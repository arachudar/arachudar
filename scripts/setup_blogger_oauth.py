#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/setup_blogger_oauth.py - Guided OAuth 2.0 Setup for Google Blogger API v3.
Engineered using the proven authentication stack from Automatic-Blogger-Poster.
Verifies read and write permissions and writes configuration to .env and blogger_token.json.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as google_build
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError:
    print("❌ Error: Missing Google libraries. Please install them:")
    print("   pip install google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)


SCOPES = ["https://www.googleapis.com/auth/blogger"]
DEFAULT_BLOG_ID = "563563588050874327"


def print_banner():
    print("\n" + "=" * 65)
    print("  அறச்சுடர் (Arachudar) - Blogger OAuth 2.0 Setup Wizard")
    print("  Engineered with the Automatic-Blogger-Poster Tech Stack")
    print("=" * 65 + "\n")


def test_blogger_credentials(blog_id: str, client_id: str, client_secret: str, refresh_token: str):
    """Verifies that the credentials have both READ and WRITE permissions."""
    print("🔍 Testing connection with Google Blogger API v3...")
    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        creds.refresh(GoogleAuthRequest())
        service = google_build("blogger", "v3", credentials=creds)

        # 1. Test Read Access
        info = service.blogs().get(blogId=blog_id).execute()
        blog_name = info.get("name", "Unknown")
        blog_url = info.get("url", "Unknown")
        print(f"  ✅ READ SUCCESS! Connected to blog: '{blog_name}' ({blog_url})")

        # 2. Test Write Access (Draft post test)
        print("🔍 Verifying post write permissions...")
        test_body = {
            "kind": "blogger#post",
            "title": "[System Test] Arachudar Connectivity Check",
            "content": "<p>Automated OAuth permission verification test.</p>",
            "labels": ["System"]
        }
        draft = service.posts().insert(blogId=blog_id, body=test_body, isDraft=True).execute()
        draft_id = draft.get("id")
        print(f"  🎉 WRITE SUCCESS! Successfully created draft post ID: {draft_id}")

        # Clean up test draft
        try:
            service.posts().delete(blogId=blog_id, postId=draft_id).execute()
            print("  🧹 Cleaned up test draft post.")
        except Exception:
            pass

        return True, None
    except Exception as exc:
        err_str = str(exc)
        print(f"\n❌ Permission Verification Failed: {err_str}")
        if "403" in err_str or "PERMISSION_DENIED" in err_str or "caller does not have permission" in err_str:
            print("\n" + "⚠️ " * 20)
            print("GOOGLE CLOUD CONSOLE ACTION REQUIRED:")
            print("1. Open: https://console.cloud.google.com/apis/credentials/consent")
            print("2. Ensure 'https://www.googleapis.com/auth/blogger' is in 'Scopes'.")
            print("3. Under 'Test users', add your Google email address.")
            print("4. Follow Step 6 in the guide below using Google OAuth 2.0 Playground.")
            print("⚠️ " * 20 + "\n")
        return False, err_str


def save_credentials(blog_id: str, client_id: str, client_secret: str, refresh_token: str):
    # 1. Save to .env (strictly gitignored)
    env_file = ROOT_DIR / ".env"
    env_content = (
        f"BLOGGER_BLOG_ID={blog_id}\n"
        f"GOOGLE_CLIENT_ID={client_id}\n"
        f"GOOGLE_CLIENT_SECRET={client_secret}\n"
        f"GOOGLE_REFRESH_TOKEN={refresh_token}\n"
        f"BLOGGER_CLIENT_ID={client_id}\n"
        f"BLOGGER_CLIENT_SECRET={client_secret}\n"
        f"BLOGGER_REFRESH_TOKEN={refresh_token}\n"
    )
    env_file.write_text(env_content, encoding="utf-8")
    print(f"💾 Saved credentials to local '{env_file.name}' file.")

    # 2. Save token data
    token_file = ROOT_DIR / "blogger_token.json"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "scopes": SCOPES
    }
    token_file.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"💾 Updated '{token_file.name}'.")

    # 3. Update config
    config_file = ROOT_DIR / "blogger_config.json"
    config_data = {
        "blog_id": blog_id,
        "blog_name": "அறச்சுடர்",
        "blog_url": "https://arachudar.blogspot.com/"
    }
    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"💾 Updated '{config_file.name}'.")


def main():
    print_banner()

    # Load existing secrets if available as defaults
    existing_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    existing_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    existing_refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    client_secrets_path = ROOT_DIR / "client_secrets.json"
    if client_secrets_path.exists() and not existing_client_id:
        try:
            cs = json.loads(client_secrets_path.read_text(encoding="utf-8")).get("installed", {})
            existing_client_id = cs.get("client_id", "")
            existing_client_secret = cs.get("client_secret", "")
        except Exception:
            pass

    token_path = ROOT_DIR / "blogger_token.json"
    if token_path.exists() and not existing_refresh_token:
        try:
            td = json.loads(token_path.read_text(encoding="utf-8"))
            existing_refresh_token = td.get("refresh_token", "")
            existing_client_id = existing_client_id or td.get("client_id", "")
            existing_client_secret = existing_client_secret or td.get("client_secret", "")
        except Exception:
            pass

    print("Please provide your Blogger OAuth credentials:")
    print("(Press Enter to keep existing value if shown in brackets)\n")

    blog_id = input(f"Enter Blog ID [{DEFAULT_BLOG_ID}]: ").strip() or DEFAULT_BLOG_ID

    c_id_prompt = f"Enter GOOGLE_CLIENT_ID [{existing_client_id[:16]}...]: " if existing_client_id else "Enter GOOGLE_CLIENT_ID: "
    client_id = input(c_id_prompt).strip() or existing_client_id

    c_sec_prompt = f"Enter GOOGLE_CLIENT_SECRET [***]: " if existing_client_secret else "Enter GOOGLE_CLIENT_SECRET: "
    client_secret = input(c_sec_prompt).strip() or existing_client_secret

    r_tok_prompt = f"Enter GOOGLE_REFRESH_TOKEN [***]: " if existing_refresh_token else "Enter GOOGLE_REFRESH_TOKEN: "
    refresh_token = input(r_tok_prompt).strip() or existing_refresh_token

    if not all([blog_id, client_id, client_secret, refresh_token]):
        print("❌ All fields are required. Setup aborted.")
        sys.exit(1)

    success, error = test_blogger_credentials(blog_id, client_id, client_secret, refresh_token)
    if success:
        save_credentials(blog_id, client_id, client_secret, refresh_token)
        print("\n" + "=" * 65)
        print("  🎉 SETUP COMPLETE & VERIFIED!")
        print("  Your Blogger automation pipeline is now 100% ready to publish.")
        print("=" * 65 + "\n")
    else:
        print("\nSetup failed. Please review the instructions and try again.")


if __name__ == "__main__":
    main()
