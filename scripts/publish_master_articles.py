#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/publish_master_articles.py
Publishes the 10 master articles across all 10 topics to Google Blogger:
- 100% pure Tamil text, zero English words
- Elegant typographic indent (&emsp;&emsp; + text-indent: 1.5rem)
- Spacious line height (2.0)
- Bold lead summary box with brand red border
- Real, high-resolution editorial photos (landmarks, institutions, infrastructure, ISRO, temples)
- ZERO candid shots of random people or screenshot vibes
- ZERO publisher/author bylines
- Safe 3.5s rate pacing between posts to respect Blogger API rate limits
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ai.tamil_synthesizer import ProcessedArticle
from src.publisher.blogger_client import BloggerClient
from scripts.build_full_database import ALL_42_ARTICLES, clean_tamil_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Publisher")

# Select the primary flagship article for each of the 10 topics
SELECTED_ARTICLE_IDS = [1, 26, 3, 9, 31, 6, 7, 5, 11, 12]


def run_publish():
    logger.info("Initializing Blogger Client...")
    client = BloggerClient()
    logger.info(f"Target Blog ID: {client.blog_id} (https://arachudar.blogspot.com/)")

    target_articles = [a for a in ALL_42_ARTICLES if a["id"] in SELECTED_ARTICLE_IDS]
    logger.info(f"Publishing {len(target_articles)} flagship articles across all 10 topics...")

    published_count = 0
    for idx, raw in enumerate(target_articles, start=1):
        clean_title = clean_tamil_text(raw["title"])
        clean_summary = clean_tamil_text(raw["summary"])
        clean_body = "\n\n".join(clean_tamil_text(p) for p in raw["body"].split("\n\n") if clean_tamil_text(p))
        clean_tags = [clean_tamil_text(t) for t in raw["tags"] if clean_tamil_text(t)]

        proc = ProcessedArticle(
            id=raw["id"],
            category=raw["category"],
            sub_category=raw["subCategory"],
            title=clean_title,
            summary=clean_summary,
            body=clean_body,
            image=raw["image"],
            author=raw.get("author", "அறச்சுடர் நிருபர்"),
            date=raw.get("date", "11 நவம்பர் 2026"),
            time_ago=raw.get("timeAgo", "உடனுக்குடன்"),
            read_time="3 நிமிடம்",
            views=raw.get("views", 10000),
            is_flash=raw.get("isFlash", False),
            tags=clean_tags,
            source_url="https://arachudar.blogspot.com/",
            source_name="அறச்சுடர்"
        )

        logger.info(f"[{idx}/{len(target_articles)}] Publishing '{proc.category}': {clean_title}...")
        try:
            res = client.publish_article(proc, dry_run=False)
            post_url = res.get("url", "N/A")
            logger.info(f"  -> SUCCESS! Live Post: {post_url}")
            published_count += 1
        except Exception as exc:
            logger.error(f"  -> FAILED: {exc}")

        # Rate pacing: 3.5s sleep to prevent Blogger API 403 burst rate-limit
        if idx < len(target_articles):
            time.sleep(3.5)

    logger.info("=======================================================")
    logger.info(f"   Published {published_count}/{len(target_articles)} articles successfully!")
    logger.info("=======================================================")


if __name__ == "__main__":
    run_publish()
