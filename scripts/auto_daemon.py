#!/usr/bin/env python3
"""
scripts/auto_daemon.py - Continuous automated runner for Arachudar Tamil News.
Fetches new live articles across Tamil sources, performs NVIDIA AI synthesis,
and publishes to Blogger at configurable intervals (default: 10 minutes).
"""

import logging
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("arachudar.auto_daemon")


def run_daemon_loop(interval_seconds: int = 600, limit: int = 5):
    """
    Runs the news pipeline on a repeating loop.
    Interval default: 600s (10 minutes).
    """
    logger.info("================================================================")
    logger.info("  அறச்சுடர் தொடர் தானியங்கி இயக்கம் (Continuous Daemon Started)")
    logger.info(f"  இடைவேளை (Interval): {interval_seconds} வினாடிகள் ({interval_seconds // 60} நிமிடம்)")
    logger.info("================================================================")

    iteration = 0
    while True:
        iteration += 1
        logger.info(f"\n--- [சுழற்சி {iteration}] செய்தி சேகரிப்பு மற்றும் வெளியீடு தொடங்குகிறது ---")
        try:
            exit_code = run_pipeline(limit=limit, dry_run=False)
            logger.info(f"சுழற்சி {iteration} முடிவு: குறியீடு {exit_code}")
        except Exception as exc:
            logger.error(f"சுழற்சி {iteration} பிழை: {exc}", exc_info=True)

        logger.info(f"அடுத்த சுழற்சிக்கு காத்திருக்கிறது ({interval_seconds} வினாடிகள்)...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    interval = int(os.environ.get("AUTO_DAEMON_INTERVAL", "600"))
    article_limit = int(os.environ.get("AUTO_DAEMON_LIMIT", "5"))
    run_daemon_loop(interval_seconds=interval, limit=article_limit)

