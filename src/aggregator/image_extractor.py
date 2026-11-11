"""
src/aggregator/image_extractor.py - Real news image extraction, strict negative filtering,
CDN high-resolution enhancements, and fallback scraping for the Arachudar pipeline.
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup

from config.sources import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Negative Image Blocklist Patterns & Extensions
# ---------------------------------------------------------------------------
IMAGE_BLOCKLIST_PATTERNS = [
    r"logo",
    r"icon",
    r"favicon",
    r"avatar",
    r"placeholder",
    r"fallback",
    r"no[-_]?image",
    r"noimage",
    r"dummy",
    r"blank",
    r"spacer",
    r"pixel",
    r"tracking",
    r"advertisement",
    r"sponsored",
    r"banner",
    r"sprite",
    r"watermark",
    r"badge",
    r"app[-_]?download",
    r"play[-_]?store",
    r"app[-_]?store",
    r"social[-_]?share",
    r"share[-_]?default",
    r"default[-_]?(news|image|thumb|pic)?",
    r"header[-_]?bg",
    r"subscribe[-_]?banner",
    r"newsletter[-_]?box",
    r"screenshot|screen[-_]?shot|screengrab",
    r"epaper|e[-_]?paper",
    r"thinaboomi\.com/uploads",
    # Ad servers, dimensions, and directories
    r"doubleclick",
    r"adserver",
    r"googlesyndication",
    r"googleadservices",
    r"taboola",
    r"outbrain",
    r"[/._-]ads?[/._-]",
    r"[/._-]adverts?[/._-]",
    r"leaderboard|skyscraper|interstitial",
    r"[-_]ad[-_]?\d+x\d+|\bad[-_]?\d+x\d+",
    r"[-_]ad(?:vertisement)?[-_.]",
]

BLOCKED_FILE_EXTENSIONS = (".svg", ".ico", ".gif")


# ---------------------------------------------------------------------------
# Validation & Resolution Enhancement Logic
# ---------------------------------------------------------------------------
def validate_and_enhance_image_url(
    image_url: Optional[str],
    source_domain: str = "",
) -> Optional[str]:
    """
    Validates that the given image URL is an authentic editorial news photo.
    Filters out logos, ads, banners, placeholders, and tracking pixels.
    Applies CDN high-resolution parameters where appropriate.
    Returns normalized high-res URL or None if invalid.
    """
    if not image_url or not isinstance(image_url, str):
        return None

    url = image_url.strip()
    if not url:
        return None

    # Protocol validation
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("//")):
        return None

    if url.startswith("//"):
        url = "https:" + url

    url_lower = url.lower()
    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    # 1. Reject non-photo file extensions (.svg, .ico, .gif)
    if any(path_lower.endswith(ext) for ext in BLOCKED_FILE_EXTENSIONS):
        return None

    # 2. Check blacklist regex patterns (with CMS-specific exemptions)
    for pat in IMAGE_BLOCKLIST_PATTERNS:
        # Exemption: Samayam LangImg CDN uses 'msid-' with a publication slug like 'tamil-samayam.jpg'
        if "static.langimg.com" in url_lower and "msid-" in url_lower:
            continue

        # Exemption: YouTube CDN video thumbnails use hqdefault.jpg / maxresdefault.jpg
        if ("ytimg.com" in url_lower or "youtube.com" in url_lower) and "default" in pat:
            continue

        if re.search(pat, url_lower):
            return None

    # 3. CDN High-Resolution Enhancement
    enhanced_url = _apply_cdn_enhancement(url, url_lower, parsed)
    return enhanced_url


def _apply_cdn_enhancement(url: str, url_lower: str, parsed) -> str:
    """Applies platform-specific high-resolution parameters to image URLs."""
    # BBC News thumbnail upgrade: /240/ -> /1024/ or /\d+/cpsprodpb/ -> /1024/cpsprodpb/
    if "ichef.bbci.co.uk" in url_lower:
        if "/240/" in url:
            return url.replace("/240/", "/1024/")
        return re.sub(r"/\d+/cpsprodpb/", "/1024/cpsprodpb/", url)

    # AssetType CDN (Daily Thanthi, Dinamani, Hindu Tamil, Maalai Malar)
    if any(cdn in url_lower for cdn in ["media.assettype.com", "cf-images.assettype.com"]):
        query_dict = parse_qs(parsed.query)
        query_dict["w"] = ["1200"]
        query_dict["auto"] = ["format,compress"]
        query_dict["fit"] = ["max"]
        new_query = urlencode(query_dict, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    # Vikatan Gumlet CDN
    if "gumlet.vikatan.com" in url_lower:
        query_dict = parse_qs(parsed.query)
        query_dict["w"] = ["1200"]
        query_dict["h"] = ["675"]
        query_dict["auto"] = ["format,compress"]
        query_dict["fit"] = ["max"]
        new_query = urlencode(query_dict, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    # Google News CDN
    if "googleusercontent.com" in url_lower:
        if "=s" in url or "=w" in url:
            return re.sub(r"=(s\d+|w\d+|s0-w\d+).*", "=s0-w1200", url)
        elif not parsed.query and "=" not in url:
            return url + "=s0-w1200"

    # YouTube Thumbnail upgrade: hqdefault.jpg / mqdefault.jpg -> maxresdefault.jpg
    if "ytimg.com" in url_lower or "youtube.com" in url_lower:
        if "hqdefault.jpg" in url:
            return url.replace("hqdefault.jpg", "maxresdefault.jpg")
        elif "mqdefault.jpg" in url:
            return url.replace("mqdefault.jpg", "maxresdefault.jpg")

    return url


# ---------------------------------------------------------------------------
# Feed Entry Image Extractor
# ---------------------------------------------------------------------------
def extract_image_from_feed_entry(entry: Any, source_id: str = "") -> Optional[str]:
    """
    Extracts candidate image URL from a parsed feed entry (dict, feedparser entry,
    or XML Element) and validates/enhances it.
    """
    candidates: List[str] = []

    # Case 1: Entry is a dictionary or FeedParserDict
    if isinstance(entry, dict) or hasattr(entry, "get"):
        # 1. media:content
        media_content = entry.get("media_content") or entry.get("media:content")
        if media_content:
            if isinstance(media_content, list):
                for item in media_content:
                    if isinstance(item, dict):
                        # Filter out video types
                        medium = item.get("medium", "")
                        content_type = item.get("type", "")
                        if medium == "video" or "video" in content_type:
                            continue
                        url = item.get("url")
                        if url:
                            candidates.append(url)
                    elif isinstance(item, str):
                        candidates.append(item)
            elif isinstance(media_content, dict):
                url = media_content.get("url")
                if url:
                    candidates.append(url)

        # 2. media:thumbnail
        media_thumbnail = entry.get("media_thumbnail") or entry.get("media:thumbnail")
        if media_thumbnail:
            if isinstance(media_thumbnail, list):
                for item in media_thumbnail:
                    if isinstance(item, dict) and item.get("url"):
                        candidates.append(item["url"])
                    elif isinstance(item, str):
                        candidates.append(item)
            elif isinstance(media_thumbnail, dict):
                if media_thumbnail.get("url"):
                    candidates.append(media_thumbnail["url"])

        # 3. enclosures
        enclosures = entry.get("enclosures")
        if enclosures and isinstance(enclosures, list):
            for enc in enclosures:
                if isinstance(enc, dict):
                    enc_type = enc.get("type", "")
                    url = enc.get("url") or enc.get("href")
                    # If type starts with image/ or no type but valid image extension
                    if url and (not enc_type or enc_type.startswith("image/")):
                        candidates.append(url)

        # 4. image dict or image_loc (sitemap)
        if entry.get("image"):
            img = entry.get("image")
            if isinstance(img, dict) and img.get("href"):
                candidates.append(img["href"])
            elif isinstance(img, str):
                candidates.append(img)
        if entry.get("image_loc"):
            candidates.append(entry.get("image_loc"))

        # 5. links array
        links = entry.get("links")
        if links and isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("type", "").startswith("image/"):
                    if link.get("href"):
                        candidates.append(link["href"])

        # 6. check HTML in summary / description
        summary = entry.get("summary") or entry.get("description") or ""
        if isinstance(summary, str) and "<img" in summary:
            extracted = extract_image_from_html(summary)
            if extracted:
                candidates.append(extracted)

    # Case 2: XML ElementTree Element
    elif hasattr(entry, "tag"):
        # Check media:content
        for elem in entry.findall(".//{http://search.yahoo.com/mrss/}content"):
            url = elem.attrib.get("url")
            medium = elem.attrib.get("medium")
            elem_type = elem.attrib.get("type", "")
            if medium == "video" or "video" in elem_type:
                continue
            if url:
                candidates.append(url)

        # Check media:thumbnail
        for elem in entry.findall(".//{http://search.yahoo.com/mrss/}thumbnail"):
            url = elem.attrib.get("url")
            if url:
                candidates.append(url)

        # Check enclosure
        for elem in entry.findall(".//enclosure"):
            url = elem.attrib.get("url")
            enc_type = elem.attrib.get("type", "")
            if url and (not enc_type or enc_type.startswith("image/")):
                candidates.append(url)

        # Check image:loc (Google News Sitemap)
        for elem in entry.findall(".//{http://www.google.com/schemas/sitemap-image/1.1}loc"):
            if elem.text:
                candidates.append(elem.text.strip())

    # Validate candidates in order
    for candidate in candidates:
        validated = validate_and_enhance_image_url(candidate, source_domain=source_id)
        if validated:
            return validated

    return None


# ---------------------------------------------------------------------------
# HTML Web Scraper Fallback (OpenGraph, Twitter Card, JSON-LD)
# ---------------------------------------------------------------------------
def extract_image_from_html(html_text: str, base_url: str = "") -> Optional[str]:
    """
    Parses HTML to extract real article images using OpenGraph, Twitter Card,
    JSON-LD ImageObject schema, or content img tags.
    """
    if not html_text:
        return None

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse HTML for image extraction: %s", e)
        return None

    candidates: List[str] = []

    # 1. OpenGraph meta tag: <meta property="og:image" content="...">
    og_img = soup.find("meta", attrs={"property": "og:image"}) or soup.find(
        "meta", attrs={"name": "og:image"}
    )
    if og_img and og_img.get("content"):
        candidates.append(og_img["content"].strip())

    # 2. Twitter Card meta tag: <meta name="twitter:image" content="...">
    tw_img = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find(
        "meta", attrs={"property": "twitter:image"}
    )
    if tw_img and tw_img.get("content"):
        candidates.append(tw_img["content"].strip())

    # 3. JSON-LD Schema: <script type="application/ld+json">
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            data = json.loads(script.string.strip())
            _extract_json_ld_images(data, candidates)
        except Exception:
            continue

    # 4. First valid <img> inside <article> or body
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if src:
            candidates.append(src.strip())

    # Resolve relative URLs and validate
    for cand in candidates:
        if base_url and not cand.startswith(("http://", "https://", "//")):
            cand = urljoin(base_url, cand)
        validated = validate_and_enhance_image_url(cand)
        if validated:
            return validated

    return None


def _extract_json_ld_images(data: Any, candidates: List[str]):
    """Recursively extracts image URLs from parsed JSON-LD structures."""
    if isinstance(data, dict):
        # Direct 'image' field
        img = data.get("image")
        if isinstance(img, str):
            candidates.append(img)
        elif isinstance(img, list):
            for item in img:
                if isinstance(item, str):
                    candidates.append(item)
                elif isinstance(item, dict) and item.get("url"):
                    candidates.append(item["url"])
        elif isinstance(img, dict) and img.get("url"):
            candidates.append(img["url"])

        # Check @graph arrays
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                _extract_json_ld_images(item, candidates)

    elif isinstance(data, list):
        for item in data:
            _extract_json_ld_images(item, candidates)


def scrape_article_image(
    article_url: str,
    timeout: int = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Fetches the article webpage and extracts the primary real news image.
    Uses robust HTTP headers and strict negative validation.
    """
    if not article_url:
        return None

    req_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        req_headers.update(headers)

    try:
        resp = requests.get(article_url, headers=req_headers, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            return extract_image_from_html(resp.text, base_url=article_url)
    except Exception as e:
        logger.warning("Failed to scrape article image from %s: %s", article_url, e)

    return None


# ---------------------------------------------------------------------------
# Class Interface: ImageExtractor
# ---------------------------------------------------------------------------
class ImageExtractor:
    """High-level Image Extractor managing validation, enhancement, and fallback scraping."""

    def __init__(self, default_timeout: int = DEFAULT_TIMEOUT):
        self.timeout = default_timeout

    def validate_and_enhance(self, image_url: Optional[str], source_domain: str = "") -> Optional[str]:
        return validate_and_enhance_image_url(image_url, source_domain=source_domain)

    def is_valid_image(self, image_url: Optional[str], source_domain: str = "") -> bool:
        return validate_and_enhance_image_url(image_url, source_domain=source_domain) is not None

    def extract_from_feed_entry(self, entry: Any, source_id: str = "") -> Optional[str]:
        return extract_image_from_feed_entry(entry, source_id=source_id)

    def extract_from_html(self, html_text: str, base_url: str = "") -> Optional[str]:
        return extract_image_from_html(html_text, base_url=base_url)

    def scrape_fallback(self, article_url: str) -> Optional[str]:
        return scrape_article_image(article_url, timeout=self.timeout)
