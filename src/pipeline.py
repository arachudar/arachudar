"""
src/pipeline.py - Master orchestration pipeline for Arachudar Tamil News.
Ingests from 15 Tamil sources, extracts real news images, deduplicates,
synthesizes easy-to-read Tamil content via NVIDIA NIM API (<= 30 RPM),
populates tamil-news-blogger.html, publishes to Blogger, and triggers social hooks.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Set root directory in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.sources import TAMIL_NEWS_SOURCES, VALID_CATEGORIES
from src.aggregator.feed_fetcher import FeedFetcher, RawArticle, fetch_all_sources
from src.aggregator.deduplicator import Deduplicator
from src.ai.rate_limiter import TokenBucketRateLimiter
from src.ai.nvidia_client import NvidiaClient
from src.ai.tamil_synthesizer import TamilSynthesizer, ProcessedArticle
from src.publisher.html_populator import HtmlPopulator
from src.publisher.blogger_client import BloggerClient
from src.publisher.social_hooks import SocialHooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("arachudar.pipeline")

# Default fallback NVIDIA API Key from user configuration
DEFAULT_NVIDIA_API_KEY = "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"

TAMIL_MONTHS = {
    1: "ஜனவரி", 2: "பிப்ரவரி", 3: "மார்ச்", 4: "ஏப்ரல்",
    5: "மே", 6: "ஜூன்", 7: "ஜூலை", 8: "ஆகஸ்ட்",
    9: "செப்டம்பர்", 10: "அக்டோபர்", 11: "நவம்பர்", 12: "டிசம்பர்"
}
TAMIL_DAYS = {
    0: "திங்கள்", 1: "செவ்வாய்", 2: "புதன்",
    3: "வியாழன்", 4: "வெள்ளி", 5: "சனி", 6: "ஞாயிறு"
}


def get_current_tamil_date() -> str:
    """Returns localized Tamil date e.g. 'புதன், 11 நவம்பர் 2026'."""
    now = datetime.now()
    day_name = TAMIL_DAYS.get(now.weekday(), "")
    month_name = TAMIL_MONTHS.get(now.month, "")
    return f"{day_name}, {now.day} {month_name} {now.year}"


def run_pipeline(
    limit: int = 5,
    dry_run: bool = False,
    category: str = "all",
    sources: Optional[List[str]] = None,
    html_path: Optional[Path] = None,
    seen_path: Optional[Path] = None
) -> int:
    """
    Executes the full automated news pipeline.
    """
    logger.info("=======================================================")
    logger.info("   அறச்சுடர் தமிழ் செய்தி தானியங்கி இயக்கம் (Pipeline Started)")
    logger.info("=======================================================")
    logger.info(f"Configuration: limit={limit}, dry_run={dry_run}, category={category}")

    html_file = html_path or (ROOT_DIR / "tamil-news-blogger.html")
    seen_file = seen_path or (ROOT_DIR / "data" / "seen_articles.json")
    seen_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Multi-source Ingestion
    logger.info(f"1. Fetching news feeds from Tamil sources...")
    source_keys = sources or list(TAMIL_NEWS_SOURCES.keys())
    if category != "all" and category in VALID_CATEGORIES:
        logger.info(f"Filtering feeds by category: {category}")

    fetcher = FeedFetcher()
    raw_articles: List[RawArticle] = []
    try:
        raw_articles = fetch_all_sources(sources=source_keys, limit_per_source=3)
    except Exception as exc:
        logger.warning(f"Live feed fetch encountered issues: {exc}. Proceeding with available articles.")

    logger.info(f"Ingested {len(raw_articles)} raw news items.")

    if not raw_articles:
        logger.warning("No articles fetched from live feeds. Checking if dry-run or sample data needed.")
        if dry_run:
            from tests.fixtures.sample_articles import SAMPLE_RAW_ARTICLES
            raw_articles = SAMPLE_RAW_ARTICLES[:limit]
            logger.info(f"Loaded {len(raw_articles)} fixture articles for dry-run verification.")
        else:
            logger.info("No new articles available to process.")
            return 0

    # 2. Deduplication
    logger.info("2. Filtering unseen articles...")
    deduplicator = Deduplicator(filepath=seen_file)
    unseen_articles = deduplicator.filter_unseen(raw_articles)
    logger.info(f"Found {len(unseen_articles)} unseen new articles.")

    if category != "all" and category in VALID_CATEGORIES:
        unseen_articles = [a for a in unseen_articles if getattr(a, "category_hint", "") == category or not getattr(a, "category_hint", "")]

    unseen_articles = unseen_articles[:limit]
    if not unseen_articles:
        logger.info("All ingested articles have already been processed and seen. Done.")
        return 0

    # 3. AI Synthesis via NVIDIA NIM (<= 30 RPM rate limiting)
    api_key = os.environ.get("NVIDIA_API_KEY", DEFAULT_NVIDIA_API_KEY)
    rate_limiter = TokenBucketRateLimiter(rate_per_sec=0.5, capacity=4.0)
    nvidia_client = NvidiaClient(api_key=api_key, rate_limiter=rate_limiter)
    synthesizer = TamilSynthesizer(nvidia_client=nvidia_client)

    logger.info(f"3. Synthesizing {len(unseen_articles)} articles with NVIDIA AI in natural Tamil...")
    processed_articles: List[ProcessedArticle] = []

    for idx, raw in enumerate(unseen_articles, start=1):
        logger.info(f"Synthesizing [{idx}/{len(unseen_articles)}]: {raw.original_title[:50]}...")
        try:
            processed = synthesizer.synthesize(raw, article_id=idx)
            processed_articles.append(processed)
        except Exception as exc:
            logger.error(f"Synthesis failed for article {idx}: {exc}")

    logger.info(f"Successfully synthesized {len(processed_articles)} articles.")

    if not processed_articles:
        logger.error("No articles were successfully synthesized. Exiting.")
        return 1

    # 4. Populate tamil-news-blogger.html template
    if not dry_run:
        logger.info(f"4. Updating HTML newspaper layout ({html_file.name})...")
        current_date = get_current_tamil_date()
        populator = HtmlPopulator(template_path=html_file)
        populator.populate(articles=processed_articles, current_date_str=current_date)
        logger.info("HTML newspaper DOM slots and NEWS_DATABASE updated.")
    else:
        logger.info(f"4. [DRY-RUN] Skipping in-place update of {html_file.name} to preserve canonical immutability.")

    # 5. Publish to Blogger
    logger.info("5. Publishing to Google Blogger (https://arachudar.blogspot.com/)...")
    blogger_client = BloggerClient()
    for proc in processed_articles:
        try:
            result = blogger_client.publish_article(proc, dry_run=dry_run)
            if dry_run:
                logger.info(f"[DRY-RUN] Would publish: {proc.title}")
            else:
                logger.info(f"Published to Blogger: {proc.title} -> {result.get('url')}")
                import time
                time.sleep(3)
        except Exception as exc:
            logger.error(f"Error publishing article '{proc.title}' to Blogger: {exc}")

    # 6. Broadcast to Social Hooks
    logger.info("6. Dispatching to social channels...")
    for proc in processed_articles:
        social_status = SocialHooks.broadcast_article(proc)
        logger.debug(f"Social hooks status for '{proc.title[:30]}': {social_status}")

    # 7. Mark articles as seen
    for raw in unseen_articles:
        deduplicator.mark_seen(raw)

    logger.info("=======================================================")
    logger.info("   அனைத்து பணிகளும் வெற்றிகரமாக முடிவடைந்தன! (Completed!)")
    logger.info("=======================================================")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Arachudar Tamil News Pipeline")
    parser.add_argument("--limit", type=int, default=5, help="Max articles to process")
    parser.add_argument("--dry-run", action="store_true", help="Execute without live network writes")
    parser.add_argument("--category", type=str, default="all", help="Category filter")
    parser.add_argument("--sources", type=str, default="", help="Comma-separated source keys")
    args = parser.parse_args()

    sources_list = [s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else None

    exit_code = run_pipeline(
        limit=args.limit,
        dry_run=args.dry_run,
        category=args.category,
        sources=sources_list
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

