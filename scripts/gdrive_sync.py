#!/usr/bin/env python3
"""
scripts/gdrive_sync.py - Google Drive Synchronization for Arachudar Archive.
Syncs topic-wise and date-wise news articles (archive/<category>/<YYYY-MM-DD>/<slug>.html)
to designated Google Drive folder (1DZQonk5qEEXQke0ZmLLLa311r_XQ5yUv).
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gdrive_sync")

ROOT_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT_DIR / "archive"
GDRIVE_TOKEN_FILE = ROOT_DIR / "gdrive_token.json"
CLIENT_SECRETS_FILE = ROOT_DIR / "client_secrets.json"

DEFAULT_GDRIVE_FOLDER_ID = "1DZQonk5qEEXQke0ZmLLLa311r_XQ5yUv"

TOPIC_FOLDER_NAMES = {
    "history": "01_தமிழ்_வரலாறு_History",
    "tamilnadu": "02_தமிழகம்_TamilNadu",
    "national": "03_இந்தியா_National",
    "world": "04_உலகம்_World",
    "politics": "05_அரசியல்_Politics",
    "business": "06_வணிகம்_Business",
    "tech": "07_தொழில்நுட்பம்_Tech",
    "sports": "08_விளையாட்டு_Sports",
    "cinema": "09_சினிமா_Cinema",
    "spiritual": "10_ஆன்மிகம்_Spiritual",
    "astrology": "11_ராசிபலன்_Astrology",
}

def get_oauth_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Resolves client ID and client secret safely from environment or local gitignored secrets."""
    cid = os.environ.get("GOOGLE_CLIENT_ID") or os.environ.get("BLOGGER_CLIENT_ID")
    sec = os.environ.get("GOOGLE_CLIENT_SECRET") or os.environ.get("BLOGGER_CLIENT_SECRET")
    if (not cid or not sec) and CLIENT_SECRETS_FILE.exists():
        try:
            data = json.loads(CLIENT_SECRETS_FILE.read_text(encoding="utf-8"))
            installed = data.get("installed") or data.get("web") or {}
            cid = cid or installed.get("client_id")
            sec = sec or installed.get("client_secret")
        except Exception:
            pass
    return cid, sec

def get_auth_url() -> str:
    """Generates the Google OAuth authorization URL for Google Drive access."""
    client_id, _ = get_oauth_credentials()
    redirect_uri = "https://developers.google.com/oauthplayground"
    scope = "https://www.googleapis.com/auth/drive.file"
    return (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )

def exchange_auth_code(code: str) -> Optional[Dict[str, str]]:
    """Exchanges authorization code for Google Drive refresh token."""
    client_id, client_secret = get_oauth_credentials()
    redirect_uri = "https://developers.google.com/oauthplayground"

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code.strip(),
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        GDRIVE_TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Google Drive token successfully saved to {GDRIVE_TOKEN_FILE.name}")
        return data
    else:
        logger.error(f"Failed to exchange code: {resp.text}")
        return None

def sync_to_gdrive(folder_id: Optional[str] = None):
    """
    Scans local archive/<category>/<date>/ files and syncs to Google Drive.
    """
    target_folder = folder_id or os.environ.get("GDRIVE_FOLDER_ID", DEFAULT_GDRIVE_FOLDER_ID)
    logger.info("=======================================================")
    logger.info(f"   அறச்சுடர் Google Drive Archive Synchronization")
    logger.info(f"   Target Folder ID: {target_folder}")
    logger.info("=======================================================")

    if not ARCHIVE_DIR.exists():
        logger.info(f"Archive directory {ARCHIVE_DIR} is currently empty. Run pipeline first.")
        return

    article_files = sorted(list(ARCHIVE_DIR.glob("**/*.html")))
    logger.info(f"Discovered {len(article_files)} topic-wise/date-wise articles in local archive:")
    for f in article_files:
        rel_path = f.relative_to(ARCHIVE_DIR)
        logger.info(f"  • archive/{rel_path} ({f.stat().st_size} bytes)")

    # Check if gdrive_token.json exists
    if not GDRIVE_TOKEN_FILE.exists():
        logger.info("-------------------------------------------------------")
        logger.info("Google Drive API authentication required.")
        logger.info("To authorize Google Drive upload, visit this link in browser:")
        logger.info(get_auth_url())
        logger.info("Then run: python3 scripts/gdrive_sync.py --code <AUTHORIZATION_CODE>")
        logger.info("-------------------------------------------------------")
        return

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        client_id, client_secret = get_oauth_credentials()
        token_data = json.loads(GDRIVE_TOKEN_FILE.read_text(encoding="utf-8"))
        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        service = build("drive", "v3", credentials=creds)

        # Upload files
        for f in article_files:
            rel = f.relative_to(ARCHIVE_DIR)
            parts = rel.parts
            topic = parts[0] if len(parts) > 1 else "general"
            topic_label = TOPIC_FOLDER_NAMES.get(topic, topic)

            file_metadata = {
                "name": f.name,
                "parents": [target_folder],
                "description": f"அறச்சுடர் நாளிதழ் - {topic_label}",
            }
            media = MediaFileUpload(str(f), mimetype="text/html")
            up = service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink").execute()
            logger.info(f"Uploaded to Drive: {up.get('name')} -> {up.get('webViewLink')}")

    except Exception as e:
        logger.warning(f"Google Drive sync note: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--code":
        exchange_auth_code(sys.argv[2])
    else:
        sync_to_gdrive()
