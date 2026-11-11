"""
Aggregator module for Arachudar Tamil News Automation Pipeline.
"""

from src.aggregator.feed_fetcher import (
    RawArticle,
    FeedFetcher,
    fetch_articles_from_source,
    fetch_all_sources,
)
from src.aggregator.image_extractor import (
    ImageExtractor,
    validate_and_enhance_image_url,
    extract_image_from_feed_entry,
    extract_image_from_html,
    scrape_article_image,
    IMAGE_BLOCKLIST_PATTERNS,
    BLOCKED_FILE_EXTENSIONS,
)
from src.aggregator.deduplicator import (
    Deduplicator,
    normalize_url,
    normalize_title,
    compute_article_hash,
)

__all__ = [
    "RawArticle",
    "FeedFetcher",
    "fetch_articles_from_source",
    "fetch_all_sources",
    "ImageExtractor",
    "validate_and_enhance_image_url",
    "extract_image_from_feed_entry",
    "extract_image_from_html",
    "scrape_article_image",
    "IMAGE_BLOCKLIST_PATTERNS",
    "BLOCKED_FILE_EXTENSIONS",
    "Deduplicator",
    "normalize_url",
    "normalize_title",
    "compute_article_hash",
]
