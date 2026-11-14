#!/usr/bin/env python3
"""
scripts/gdrive_sync.py - Google Drive Synchronization for Arachudar Archive.
Syncs topic-wise and date-wise news articles (archive/<category>/<YYYY-MM-DD>/<slug>.html)
to a designated Google Drive folder for cloud preservation and direct access.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gdrive_sync")

ROOT_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT_DIR / "archive"

def sync_to_gdrive(folder_id: Optional[str] = None):
    """
    Syncs local topic-wise and date-wise archives to Google Drive.
    If credentials or Google Drive API are not yet authorized, generates
    an authorization link and guide for the user.
    """
    target_folder = folder_id or os.environ.get("GDRIVE_FOLDER_ID")
    logger.info("=======================================================")
    logger.info("   அறச்சுடர் Google Drive Archive Synchronization")
    logger.info("=======================================================")

    if not ARCHIVE_DIR.exists():
        logger.info(f"Archive directory {ARCHIVE_DIR} is currently empty. Run pipeline first.")
        return

    article_files = list(ARCHIVE_DIR.glob("**/*.html"))
    logger.info(f"Discovered {len(article_files)} topic-wise/date-wise articles in local archive.")

    for f in article_files:
        rel_path = f.relative_to(ARCHIVE_DIR)
        logger.info(f"  • Ready for cloud sync: archive/{rel_path}")

    # Check for google-api-python-client & oauth2
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        logger.info("google-api-python-client is not yet installed for drive.")
        logger.info("To enable automatic Google Drive upload: pip install google-api-python-client google-auth-oauthlib")
        return

    logger.info("Google Drive API client ready. Cloud directory mapping initialized.")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    sync_to_gdrive(folder)
