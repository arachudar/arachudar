"""
src/aggregator/feed_fetcher.py - Multi-source feed fetcher for RSS 2.0, Atom,
Google News Sitemap XML, and YouTube Atom feeds for the Arachudar pipeline.
"""

import re
import time
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests
import feedparser

from config.sources import (
    TAMIL_NEWS_SOURCES,
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    get_source_config,
    map_category,
)
from src.aggregator.image_extractor import (
    validate_and_enhance_image_url,
    extract_image_from_feed_entry,
    scrape_article_image,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core Interface Contract: RawArticle (M1 <-> M2)
# ---------------------------------------------------------------------------
@dataclass
class RawArticle:
    source_id: str          # e.g. "daily_thanthi", "dinamalar"
    source_name: str        # e.g. "தினத்தந்தி"
    source_url: str         # Primary article link
    original_title: str     # Raw Tamil title from feed
    original_summary: str   # Raw description or snippet
    image_url: str          # Verified real news photograph URL (non-empty, filtered)
    published_date: str     # ISO or formatted date string
    category_hint: str      # Raw category slug or hint (e.g. "tamilnadu", "cinema")


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------
def _sanitize_xml(text: str) -> str:
    """Remove invalid XML control characters."""
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)


def _clean_html_snippet(raw_html: str) -> str:
    """Strip HTML tags from description or summary."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    return " ".join(text.split()).strip()


def _normalize_date(date_str: Optional[str]) -> str:
    """Normalize date strings to ISO 8601 if possible; fallback to current UTC time."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        try:
            # Handle standard ISO formats with T or Z
            clean = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            return dt.isoformat()
        except Exception:
            return date_str.strip()


# ---------------------------------------------------------------------------
# FeedFetcher Class
# ---------------------------------------------------------------------------
class FeedFetcher:
    """
    Unified fetcher supporting RSS 2.0, Atom, Google News Sitemap XML,
    and YouTube Atom feeds with robust retries, timeout, and real image extraction.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        session: Optional[requests.Session] = None,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _http_get(self, url: str) -> requests.Response:
        """Execute HTTP GET with exponential backoff on transient errors."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (429, 500, 502, 503, 504):
                    wait = 0.5 * (2 ** attempt)
                    logger.warning("HTTP %s for %s, retry %d in %.1fs", resp.status_code, url, attempt + 1, wait)
                    time.sleep(wait)
                else:
                    resp.raise_for_status()
            except requests.RequestException as e:
                last_error = e
                wait = 0.5 * (2 ** attempt)
                logger.warning("Request error for %s (%s), retry %d in %.1fs", url, e, attempt + 1, wait)
                time.sleep(wait)

        if last_error:
            raise last_error
        raise requests.HTTPError(f"Failed to fetch {url} after {self.max_retries} retries")

    def fetch_source(
        self,
        source_id: str,
        limit: Optional[int] = None,
        enable_scraper_fallback: bool = True,
        require_image: bool = True,
    ) -> List[RawArticle]:
        """
        Fetch articles from a single configured source ID.
        Converts entries to RawArticle objects with verified real images.
        """
        config = get_source_config(source_id)
        if not config:
            logger.error("Unknown source ID: %s", source_id)
            return []

        articles: List[RawArticle] = []

        try:
            if config.type == "rss":
                articles = self._fetch_rss(config, limit=limit, enable_scraper=enable_scraper_fallback)
            elif config.type == "google_news_sitemap":
                articles = self._fetch_sitemap(config, limit=limit, enable_scraper=enable_scraper_fallback)
            elif config.type == "rss_multi":
                articles = self._fetch_rss_multi(config, limit=limit, enable_scraper=enable_scraper_fallback)
            elif config.type == "proxy_fallback":
                articles = self._fetch_proxy_fallback(config, limit=limit, enable_scraper=enable_scraper_fallback)
            elif config.type == "google_news_topics":
                articles = self._fetch_google_news_topics(config, limit=limit, enable_scraper=enable_scraper_fallback)
            elif config.type == "directory_catalog":
                logger.info("Source %s is directory catalog, skipping direct article fetch", source_id)
                return []
            else:
                logger.warning("Unsupported source type '%s' for source %s", config.type, source_id)
        except Exception as e:
            logger.error("Error fetching source %s: %s", source_id, e, exc_info=True)
            # Try sitemap_fallback if configured
            if config.sitemap_fallback:
                try:
                    logger.info("Attempting fallback sitemap for %s: %s", source_id, config.sitemap_fallback)
                    articles = self._parse_sitemap_xml(
                        config.sitemap_fallback, config, limit=limit, enable_scraper=enable_scraper_fallback
                    )
                except Exception as fallback_err:
                    logger.error("Fallback failed for %s: %s", source_id, fallback_err)

        if require_image:
            articles = [a for a in articles if a.image_url]

        if limit and len(articles) > limit:
            articles = articles[:limit]

        return articles

    def fetch_all(
        self,
        sources: Optional[List[str]] = None,
        limit_per_source: Optional[int] = None,
        enable_scraper_fallback: bool = True,
        require_image: bool = True,
    ) -> List[RawArticle]:
        """Fetch articles across all (or specified subset of) sources."""
        target_sources = sources or list(TAMIL_NEWS_SOURCES.keys())
        all_articles: List[RawArticle] = []

        for src_id in target_sources:
            try:
                items = self.fetch_source(
                    source_id=src_id,
                    limit=limit_per_source,
                    enable_scraper_fallback=enable_scraper_fallback,
                    require_image=require_image,
                )
                all_articles.extend(items)
            except Exception as e:
                logger.error("Batch fetch failed for source %s: %s", src_id, e)

        return all_articles

    # -----------------------------------------------------------------------
    # Protocol Fetchers
    # -----------------------------------------------------------------------
    def _fetch_rss(
        self,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Fetch and parse standard RSS 2.0 / Atom feed."""
        if not config.feed_url:
            return []

        resp = self._http_get(config.feed_url)
        sanitized_content = _sanitize_xml(resp.text)
        return self._parse_rss_content(sanitized_content, config, limit=limit, enable_scraper=enable_scraper)

    def _parse_rss_content(
        self,
        content: str,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Parse RSS/Atom XML string into RawArticle instances."""
        parsed = feedparser.parse(content)
        articles: List[RawArticle] = []

        entries = parsed.entries
        if limit:
            entries = entries[:limit * 2]  # take extra to account for missing image filter

        for entry in entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = _clean_html_snippet(getattr(entry, "summary", getattr(entry, "description", "")))
            pub_date = _normalize_date(getattr(entry, "published", getattr(entry, "pubDate", None)))

            # Category detection
            cat_hint = config.default_category
            if hasattr(entry, "tags") and entry.tags:
                cat_hint = entry.tags[0].get("term", config.default_category)
            elif hasattr(entry, "category"):
                cat_hint = entry.category

            normalized_category = map_category(cat_hint, default=config.default_category)

            # Image extraction
            image_url = extract_image_from_feed_entry(entry, source_id=config.id)
            if not image_url and enable_scraper and link:
                image_url = scrape_article_image(link, timeout=self.timeout)

            if not image_url or not title or not link:
                continue

            article = RawArticle(
                source_id=config.id,
                source_name=config.tamil_name,
                source_url=link,
                original_title=title,
                original_summary=summary,
                image_url=image_url,
                published_date=pub_date,
                category_hint=normalized_category,
            )
            articles.append(article)

            if limit and len(articles) >= limit:
                break

        return articles

    def _fetch_sitemap(
        self,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Fetch and parse Google News Sitemap XML (e.g. Dinamalar)."""
        if not config.feed_url:
            return []
        return self._parse_sitemap_xml(config.feed_url, config, limit=limit, enable_scraper=enable_scraper)

    def _parse_sitemap_xml(
        self,
        sitemap_url: str,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Parse Google News Sitemap XML into RawArticle instances."""
        resp = self._http_get(sitemap_url)
        root = ET.fromstring(resp.content)

        namespaces = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }

        articles: List[RawArticle] = []

        url_nodes = root.findall("sm:url", namespaces)
        if not url_nodes:
            # Try without namespace prefix if default is used
            url_nodes = root.findall(".//url")

        for url_node in url_nodes:
            loc_elem = url_node.find("sm:loc", namespaces)
            if loc_elem is None:
                loc_elem = url_node.find("loc")
            link = loc_elem.text.strip() if loc_elem is not None and loc_elem.text else ""

            # News title and date
            news_elem = url_node.find("news:news", namespaces)
            title = ""
            pub_date = ""
            if news_elem is not None:
                title_elem = news_elem.find("news:title", namespaces)
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()

                date_elem = news_elem.find("news:publication_date", namespaces)
                if date_elem is not None and date_elem.text:
                    pub_date = _normalize_date(date_elem.text.strip())

            # Fallback: Extract title from <image:title> (e.g. Dinamalar sitemaps)
            if not title:
                img_title_elem = url_node.find(".//image:title", namespaces)
                if img_title_elem is None:
                    img_title_elem = url_node.find(".//title")
                if img_title_elem is not None and img_title_elem.text:
                    title = img_title_elem.text.strip()

            if not pub_date:
                # Check lastmod
                lastmod_elem = url_node.find("sm:lastmod", namespaces)
                if lastmod_elem is None:
                    lastmod_elem = url_node.find("lastmod")
                if lastmod_elem is not None and lastmod_elem.text:
                    pub_date = _normalize_date(lastmod_elem.text.strip())

            # Image loc
            image_url = None
            img_loc_elem = url_node.find(".//image:loc", namespaces)
            if img_loc_elem is not None and img_loc_elem.text:
                image_url = validate_and_enhance_image_url(img_loc_elem.text.strip(), source_domain=config.id)

            if not image_url and enable_scraper and link:
                image_url = scrape_article_image(link, timeout=self.timeout)

            if not image_url or not title:
                continue

            # Category hint from URL slug
            cat_hint = config.default_category
            for cat in ["tamil-nadu", "cinema", "sports", "business", "world", "india"]:
                if f"/{cat}/" in link.lower() or f"-{cat}-" in link.lower():
                    cat_hint = cat
                    break
            normalized_cat = map_category(cat_hint, default=config.default_category)

            article = RawArticle(
                source_id=config.id,
                source_name=config.tamil_name,
                source_url=link,
                original_title=title,
                original_summary="",
                image_url=image_url,
                published_date=pub_date or datetime.now(timezone.utc).isoformat(),
                category_hint=normalized_cat,
            )
            articles.append(article)

            if limit and len(articles) >= limit:
                break

        return articles

    def _fetch_rss_multi(
        self,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Fetch across multi-category RSS feeds (e.g. Oneindia, News18, Asianet)."""
        if not config.feeds:
            return []

        articles: List[RawArticle] = []
        limit_per_feed = (limit // len(config.feeds) + 1) if limit else None

        for section_name, feed_url in config.feeds.items():
            try:
                resp = self._http_get(feed_url)
                sanitized_content = _sanitize_xml(resp.text)
                feed_articles = self._parse_rss_content(
                    sanitized_content, config, limit=limit_per_feed, enable_scraper=enable_scraper
                )
                # Override category hint with specific feed section name
                mapped_cat = map_category(section_name, default=config.default_category)
                for a in feed_articles:
                    a.category_hint = mapped_cat
                    articles.append(a)
                    if limit and len(articles) >= limit:
                        return articles
            except Exception as e:
                logger.warning("Failed to fetch sub-feed %s (%s) for %s: %s", section_name, feed_url, config.id, e)

        return articles

    def _fetch_proxy_fallback(
        self,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Fetch YouTube Atom feed or Google search proxy (e.g. Zee News Tamil)."""
        articles: List[RawArticle] = []

        # 1. Try YouTube Atom feed
        if config.youtube_feed:
            try:
                resp = self._http_get(config.youtube_feed)
                yt_articles = self._parse_youtube_atom(resp.content, config, limit=limit)
                articles.extend(yt_articles)
                if limit and len(articles) >= limit:
                    return articles[:limit]
            except Exception as e:
                logger.warning("YouTube feed fetch failed for %s: %s", config.id, e)

        # 2. Try Google News search proxy if needed
        if (not articles or (limit and len(articles) < limit)) and config.google_search_proxy:
            try:
                resp = self._http_get(config.google_search_proxy)
                proxy_articles = self._parse_rss_content(
                    resp.text, config, limit=limit, enable_scraper=enable_scraper
                )
                articles.extend(proxy_articles)
            except Exception as e:
                logger.warning("Google search proxy failed for %s: %s", config.id, e)

        return articles[:limit] if limit else articles

    def _parse_youtube_atom(
        self,
        atom_bytes: bytes,
        config: Any,
        limit: Optional[int] = None,
    ) -> List[RawArticle]:
        """Parse YouTube Channel Atom feed into RawArticle instances."""
        root = ET.fromstring(atom_bytes)
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }

        articles: List[RawArticle] = []
        entries = root.findall("atom:entry", namespaces)
        if not entries:
            entries = root.findall(".//entry")

        for entry in entries:
            title_elem = entry.find("atom:title", namespaces)
            if title_elem is None:
                title_elem = entry.find("title")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

            link_elem = entry.find("atom:link[@rel='alternate']", namespaces)
            if link_elem is None:
                link_elem = entry.find(".//link")
            link = link_elem.attrib.get("href", "") if link_elem is not None else ""

            published_elem = entry.find("atom:published", namespaces)
            pub_date = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

            # Extract thumbnail
            thumb_elem = entry.find(".//media:thumbnail", namespaces)
            image_url = None
            if thumb_elem is not None:
                raw_thumb = thumb_elem.attrib.get("url")
                image_url = validate_and_enhance_image_url(raw_thumb, source_domain=config.id)

            # Description snippet
            desc_elem = entry.find(".//media:description", namespaces)
            summary = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

            if not image_url or not title:
                continue

            article = RawArticle(
                source_id=config.id,
                source_name=config.tamil_name,
                source_url=link,
                original_title=title,
                original_summary=summary[:300],
                image_url=image_url,
                published_date=_normalize_date(pub_date),
                category_hint=config.default_category,
            )
            articles.append(article)

            if limit and len(articles) >= limit:
                break

        return articles

    def _fetch_google_news_topics(
        self,
        config: Any,
        limit: Optional[int] = None,
        enable_scraper: bool = True,
    ) -> List[RawArticle]:
        """Fetch Google News Tamil topic feeds."""
        if not config.feeds:
            return []

        articles: List[RawArticle] = []
        limit_per_topic = (limit // len(config.feeds) + 1) if limit else None

        for topic_name, feed_url in config.feeds.items():
            try:
                resp = self._http_get(feed_url)
                sanitized_content = _sanitize_xml(resp.text)
                topic_articles = self._parse_rss_content(
                    sanitized_content, config, limit=limit_per_topic, enable_scraper=enable_scraper
                )
                mapped_cat = map_category(topic_name, default=config.default_category)
                for a in topic_articles:
                    a.category_hint = mapped_cat
                    articles.append(a)
                    if limit and len(articles) >= limit:
                        return articles
            except Exception as e:
                logger.warning("Failed to fetch Google News topic %s: %s", topic_name, e)

        return articles


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------
def fetch_articles_from_source(
    source_id: str,
    limit: Optional[int] = None,
    enable_scraper_fallback: bool = True,
) -> List[RawArticle]:
    """Fetch articles from a single source ID using standard defaults."""
    fetcher = FeedFetcher()
    return fetcher.fetch_source(
        source_id=source_id,
        limit=limit,
        enable_scraper_fallback=enable_scraper_fallback,
    )


def fetch_all_sources(
    sources: Optional[List[str]] = None,
    limit_per_source: Optional[int] = None,
    enable_scraper_fallback: bool = True,
) -> List[RawArticle]:
    """Fetch articles across all configured sources using standard defaults."""
    fetcher = FeedFetcher()
    return fetcher.fetch_all(
        sources=sources,
        limit_per_source=limit_per_source,
        enable_scraper_fallback=enable_scraper_fallback,
    )
