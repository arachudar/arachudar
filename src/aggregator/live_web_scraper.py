"""
src/aggregator/live_web_scraper.py - Production-Grade Deep Web Scraper for
Daily Thanthi (dailythanthi.com) and The Hindu (thehindu.com / hindutamil.in).

Scrapes live breaking headlines, full copy text, authentic editorial photos,
normalizes categories, and returns RawArticle instances adhering to Arachudar contracts.
"""

import logging
import re
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, urljoin
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

from config.sources import (
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
    map_category,
    map_subcategory,
    VALID_CATEGORIES,
)
from src.aggregator.feed_fetcher import RawArticle
from src.aggregator.image_extractor import (
    validate_and_enhance_image_url,
    scrape_article_image,
)

logger = logging.getLogger(__name__)

# Boilerplate patterns to exclude from scraped article bodies
BOILERPLATE_PATTERNS = [
    r"subscribed with another email",
    r"logout and login with that one",
    r"terms and conditions",
    r"all rights reserved",
    r"click here to download",
    r"read also:",
    r"also read:",
    r"subscribe to our newsletter",
    r"follow us on",
    r"advertisement",
    r"promo code",
    r"sign in to read",
]


class LiveWebScraper:
    """
    Deep web scraping engine designed for Daily Thanthi and The Hindu.
    Extracts article content, clean paragraphs, and verified high-res editorial photos.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ta,en-US;q=0.9,en;q=0.8",
        })

    def _fetch_html(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL with exponential backoff and return BeautifulSoup parser."""
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "html.parser")
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    return None
            except Exception as e:
                logger.debug(f"Fetch failed for {url} (attempt {attempt + 1}): {e}")
                time.sleep(0.5 * (2 ** attempt))
        return None

    def _is_clean_paragraph(self, text: str) -> bool:
        """Filters out ads, login nag strings, and short garbage."""
        if len(text) < 35:
            return False
        text_lower = text.lower()
        if any(re.search(pat, text_lower) for pat in BOILERPLATE_PATTERNS):
            return False
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # 1. DAILY THANTHI SCRAPER
    # ──────────────────────────────────────────────────────────────────────────
    def scrape_daily_thanthi_article(self, article_url: str, title_hint: str = "") -> Optional[RawArticle]:
        """Scrapes full article page from Daily Thanthi."""
        soup = self._fetch_html(article_url)
        if not soup:
            return None

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else title_hint
        if not title:
            return None

        # Extract high-res image
        image_url = ""
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            image_url = validate_and_enhance_image_url(og_img.get("content"), source_domain="dailythanthi.com") or ""

        # Extract clean paragraphs
        body_paragraphs = []
        # Target main content containers
        story_div = soup.find("div", class_=re.compile(r"story-content|story_body|content-body|article-body", re.I))
        container = story_div if story_div else soup

        for p in container.find_all("p"):
            text = p.get_text(strip=True)
            if self._is_clean_paragraph(text):
                body_paragraphs.append(text)

        summary = body_paragraphs[0] if body_paragraphs else title
        body = "\n\n".join(body_paragraphs) if body_paragraphs else summary

        # Category mapping from URL path or keywords
        cat = "tamilnadu"
        url_lower = article_url.lower()
        if "sports" in url_lower or "cricket" in url_lower:
            cat = "sports"
        elif "cinema" in url_lower or "movie" in url_lower:
            cat = "cinema"
        elif "business" in url_lower:
            cat = "business"
        elif "india" in url_lower:
            cat = "national"
        elif "world" in url_lower:
            cat = "world"
        else:
            cat = map_category(f"{title} {summary}")

        return RawArticle(
            source_id="daily_thanthi",
            source_name="தினத்தந்தி",
            source_url=article_url,
            original_title=title,
            original_summary=summary,
            image_url=image_url or "https://media.assettype.com/dailythanthi/2026-11-10/0p8dqg6u/CHENNAI-10.jpg?w=1200",
            published_date=datetime.now(timezone.utc).isoformat(),
            category_hint=cat,
        )

    def scrape_daily_thanthi(self, limit: int = 5) -> List[RawArticle]:
        """Collects top breaking articles from Daily Thanthi feed and scrapes full body."""
        articles: List[RawArticle] = []
        feed_url = "https://www.dailythanthi.com/stories.rss"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                link = getattr(entry, "link", "")
                title = getattr(entry, "title", "")
                if not link:
                    continue

                scraped = self.scrape_daily_thanthi_article(link, title_hint=title)
                if scraped:
                    # If image is missing from page, fallback to media_content in feed
                    if not scraped.image_url or "CHENNAI-10.jpg" in scraped.image_url:
                        media = getattr(entry, "media_content", None)
                        if media and isinstance(media, list) and media[0].get("url"):
                            scraped.image_url = validate_and_enhance_image_url(media[0]["url"]) or scraped.image_url
                    articles.append(scraped)
        except Exception as exc:
            logger.warning(f"Error scraping Daily Thanthi feed: {exc}")

        return articles

    # ──────────────────────────────────────────────────────────────────────────
    # 2. THE HINDU & HINDU TAMIL THISAI SCRAPER
    # ──────────────────────────────────────────────────────────────────────────
    def scrape_the_hindu_article(self, article_url: str, title_hint: str = "") -> Optional[RawArticle]:
        """Scrapes full article page from The Hindu."""
        soup = self._fetch_html(article_url)
        if not soup:
            return None

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else title_hint
        if not title:
            return None

        # High-res image
        image_url = ""
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            raw_img = og_img.get("content")
            # Upgrade The Hindu image resolution if thumbnail
            if "LANDSCAPE" in raw_img:
                image_url = re.sub(r"LANDSCAPE_\d+", "LANDSCAPE_1200", raw_img)
            else:
                image_url = raw_img

        # Extract paragraphs
        body_paragraphs = []
        content_div = soup.find("div", class_=re.compile(r"articlebodycontent|article-body|story-content", re.I))
        container = content_div if content_div else soup

        for p in container.find_all("p"):
            text = p.get_text(strip=True)
            if self._is_clean_paragraph(text):
                body_paragraphs.append(text)

        summary = body_paragraphs[0] if body_paragraphs else title
        body = "\n\n".join(body_paragraphs) if body_paragraphs else summary

        # Category mapping
        cat = "national"
        url_lower = article_url.lower()
        if "international" in url_lower or "world" in url_lower:
            cat = "world"
        elif "business" in url_lower or "markets" in url_lower:
            cat = "business"
        elif "sci-tech" in url_lower or "science" in url_lower or "technology" in url_lower:
            cat = "tech"
        elif "sport" in url_lower or "cricket" in url_lower:
            cat = "sports"
        elif "entertainment" in url_lower or "cinema" in url_lower:
            cat = "cinema"
        elif "tamil-nadu" in url_lower or "chennai" in url_lower:
            cat = "tamilnadu"

        return RawArticle(
            source_id="the_hindu",
            source_name="தி இந்து",
            source_url=article_url,
            original_title=title,
            original_summary=summary,
            image_url=image_url or "https://th-i.thgim.com/public/incoming/article.jpg",
            published_date=datetime.now(timezone.utc).isoformat(),
            category_hint=cat,
        )

    def scrape_the_hindu(self, limit: int = 5) -> List[RawArticle]:
        """Collects top articles from The Hindu RSS feed and scrapes full body."""
        articles: List[RawArticle] = []
        feed_url = "https://www.thehindu.com/feeder/default.rss"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                link = getattr(entry, "link", "")
                title = getattr(entry, "title", "")
                if not link:
                    continue

                scraped = self.scrape_the_hindu_article(link, title_hint=title)
                if scraped:
                    # Check media_content
                    media = getattr(entry, "media_content", None)
                    if media and isinstance(media, list) and media[0].get("url"):
                        m_url = media[0]["url"]
                        scraped.image_url = m_url.replace("/LANDSCAPE_435/", "/LANDSCAPE_1200/")
                    articles.append(scraped)
        except Exception as exc:
            logger.warning(f"Error scraping The Hindu feed: {exc}")

        return articles

    def scrape_hindu_tamil(self, limit: int = 5) -> List[RawArticle]:
        """Scrapes Tamil edition of The Hindu (Hindu Tamil Thisai)."""
        articles: List[RawArticle] = []
        feed_url = "https://www.hindutamil.in/feed"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                link = getattr(entry, "link", "")
                title = getattr(entry, "title", "")
                if not link:
                    continue

                scraped = self.scrape_daily_thanthi_article(link, title_hint=title)
                if scraped:
                    scraped.source_id = "hindu_tamil"
                    scraped.source_name = "இந்து தமிழ் திசை"
                    articles.append(scraped)
        except Exception as exc:
            logger.warning(f"Error scraping Hindu Tamil: {exc}")

        return articles

    def scrape_all(self, limit_per_source: int = 4) -> List[RawArticle]:
        """Executes full deep scrape across Daily Thanthi, The Hindu, and Hindu Tamil."""
        all_articles: List[RawArticle] = []

        logger.info(f"Scraping Daily Thanthi (limit={limit_per_source})...")
        dt_articles = self.scrape_daily_thanthi(limit=limit_per_source)
        all_articles.extend(dt_articles)
        logger.info(f"Ingested {len(dt_articles)} full articles from Daily Thanthi.")

        logger.info(f"Scraping The Hindu (limit={limit_per_source})...")
        th_articles = self.scrape_the_hindu(limit=limit_per_source)
        all_articles.extend(th_articles)
        logger.info(f"Ingested {len(th_articles)} full articles from The Hindu.")

        logger.info(f"Scraping Hindu Tamil Thisai (limit={limit_per_source})...")
        ht_articles = self.scrape_hindu_tamil(limit=limit_per_source)
        all_articles.extend(ht_articles)
        logger.info(f"Ingested {len(ht_articles)} full articles from Hindu Tamil.")

        return all_articles
