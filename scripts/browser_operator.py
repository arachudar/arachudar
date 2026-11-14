#!/usr/bin/env python3
"""
scripts/browser_operator.py
Autonomous Browser Operator using Playwright Chromium to assist the user:
1. Opens visible Chromium for Google login & captures Google Drive OAuth code automatically.
2. Exchanges token and syncs archive to Google Drive folder (1DZQonk5qEEXQke0ZmLLLa311r_XQ5yUv).
3. Navigates to Blogger Dashboard (https://www.blogger.com/blog/themes/563563588050874327)
   to restore the latest broadsheet blogger-theme.xml with zero modals.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("browser_operator")

ROOT_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT_DIR / "archive"
THEME_XML_PATH = ROOT_DIR / "blogger-theme.xml"
GDRIVE_TOKEN_FILE = ROOT_DIR / "gdrive_token.json"
CLIENT_SECRETS_FILE = ROOT_DIR / "client_secrets.json"
USER_DATA_DIR = Path.home() / ".chromium_arachudar_session"

BLOG_ID = "563563588050874327"
GDRIVE_FOLDER_ID = "1DZQonk5qEEXQke0ZmLLLa311r_XQ5yUv"

def get_oauth_credentials():
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

def exchange_code_for_drive_token(code: str) -> bool:
    client_id, client_secret = get_oauth_credentials()
    redirect_uri = "https://developers.google.com/oauthplayground"

    logger.info(f"Exchanging authorization code for Google Drive refresh token...")
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
        return True
    else:
        logger.error(f"Failed to exchange code: {resp.text}")
        return False

def run_operator():
    client_id, client_secret = get_oauth_credentials()
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=https://developers.google.com/oauthplayground&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/drive.file&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=======================================================")
    logger.info("   அறச்சுடர் Autonomous Browser Operator Launched")
    logger.info("   Opening visible Chromium browser on your screen...")
    logger.info("=======================================================")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            channel="chromium",
            args=["--start-maximized"]
        )

        page = context.pages[0] if context.pages else context.new_page()

        # Step 1: Drive OAuth Authorization
        if not GDRIVE_TOKEN_FILE.exists():
            logger.info("Navigating to Google Drive Authorization page...")
            page.goto(auth_url)
            logger.info("-------------------------------------------------------")
            logger.info("👉 ACTION FOR YOU: On the browser window that just opened,")
            logger.info("   simply sign in to your Google Account and click 'Allow'.")
            logger.info("   Our operator will automatically capture the code from the URL!")
            logger.info("-------------------------------------------------------")

            captured_code = None
            for _ in range(120):  # wait up to 4 minutes for user signin
                current_url = page.url
                if "oauthplayground" in current_url and "code=" in current_url:
                    parsed = urlparse(current_url)
                    params = parse_qs(parsed.query)
                    if "code" in params:
                        captured_code = params["code"][0]
                        logger.info(f"Captured OAuth authorization code from browser URL!")
                        break
                time.sleep(2)

            if captured_code:
                success = exchange_code_for_drive_token(captured_code)
                if success:
                    # Run sync immediately
                    try:
                        import subprocess
                        subprocess.run([sys.executable, "scripts/gdrive_sync.py"])
                    except Exception as ex:
                        logger.warning(f"Sync trigger note: {ex}")
        else:
            logger.info(f"Google Drive token already exists at {GDRIVE_TOKEN_FILE.name}")

        # Step 2: Open Blogger Theme page
        theme_url = f"https://www.blogger.com/blog/themes/{BLOG_ID}"
        logger.info(f"Navigating to Blogger Theme Manager: {theme_url}")
        page.goto(theme_url)
        logger.info("-------------------------------------------------------")
        logger.info("👉 Blogger Theme Dashboard is open on your screen.")
        logger.info(f"   Theme file ready on your disk: {THEME_XML_PATH.resolve()}")
        logger.info("   Click: Customize dropdown (▾) -> Restore -> Upload 'blogger-theme.xml'")
        logger.info("-------------------------------------------------------")

        # Let user complete or let operator wait
        time.sleep(30)

        # Step 3: Open live site to verify
        live_page = context.new_page()
        live_page.goto("https://arachudar.blogspot.com/")
        logger.info("Live blog https://arachudar.blogspot.com/ opened for inspection.")

        # Keep browser open for a minute or until closed
        time.sleep(30)
        context.close()
        logger.info("Browser session completed.")

if __name__ == "__main__":
    run_operator()
