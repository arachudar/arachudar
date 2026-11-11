"""
src/publisher/blogger_client.py - Google Blogger API v3 client.
Manages OAuth2 token refresh, payload formatting, dry-run mode, and publishing
Tamil news articles to Blogger (https://arachudar.blogspot.com/).
"""

import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from src.ai.tamil_synthesizer import ProcessedArticle

TAMIL_CATEGORY_LABELS: Dict[str, str] = {
    "tamilnadu": "தமிழகம்",
    "national": "இந்தியா",
    "world": "உலகம்",
    "politics": "அரசியல்",
    "business": "வணிகம்",
    "cinema": "சினிமா",
    "sports": "விளையாட்டு",
    "tech": "தொழில்நுட்பம்",
    "spiritual": "ஆன்மீகம்",
    "chennai": "சென்னை",
    "epaper": "இ-பேப்பர்"
}


def clean_tamil_text(text: str) -> str:
    """Removes Latin/English characters and normalizes whitespace."""
    if not text:
        return ""
    # Strip any Latin letters [a-zA-Z]
    cleaned = re.sub(r"[a-zA-Z]+", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class BloggerClient:
    """
    Google Blogger API v3 client managing OAuth2 token exchange,
    token caching, dry-run mode, and publishing formatted Tamil news articles.
    """

    def __init__(
        self,
        blog_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        time_func=time.time
    ):
        self.time_func = time_func
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        # 1. Resolve Blog ID
        self.blog_id = blog_id or os.environ.get("BLOGGER_BLOG_ID")
        if not self.blog_id:
            config_file = Path("blogger_config.json")
            if config_file.exists():
                try:
                    data = json.loads(config_file.read_text(encoding="utf-8"))
                    self.blog_id = data.get("blog_id")
                except Exception:
                    pass
        if not self.blog_id:
            self.blog_id = "test-mock-blog-id-12345"

        # 2. Resolve Client ID & Client Secret
        self.client_id = client_id or os.environ.get("BLOGGER_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("BLOGGER_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            secrets_file = Path("client_secrets.json")
            if secrets_file.exists():
                try:
                    data = json.loads(secrets_file.read_text(encoding="utf-8"))
                    installed = data.get("installed", {})
                    self.client_id = self.client_id or installed.get("client_id")
                    self.client_secret = self.client_secret or installed.get("client_secret")
                except Exception:
                    pass
        if not self.client_id:
            self.client_id = "test-mock-client-id.apps.googleusercontent.com"
        if not self.client_secret:
            self.client_secret = "test-mock-client-secret"

        # 3. Resolve Refresh Token
        self.refresh_token = refresh_token or os.environ.get("BLOGGER_REFRESH_TOKEN")
        if not self.refresh_token:
            token_file = Path("blogger_token.json")
            if token_file.exists():
                try:
                    data = json.loads(token_file.read_text(encoding="utf-8"))
                    self.refresh_token = data.get("refresh_token")
                except Exception:
                    pass
        if not self.refresh_token:
            self.refresh_token = "test-mock-refresh-token"

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves a valid OAuth2 access token, exchanging refresh token if needed.
        """
        now = self.time_func()
        if not force_refresh and self._cached_token and now < (self._token_expires_at - 60):
            return self._cached_token

        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        self._cached_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = now + float(expires_in)
        return self._cached_token

    def format_post_html(self, article: ProcessedArticle) -> str:
        """
        Formats article into publication-ready Tamil Blogger HTML post.
        Strictly pure Tamil text, spacious line-height, elegant mood indent (&emsp;&emsp;),
        and zero byline/source attribution footers.
        """
        body_text = getattr(article, "body", "")
        clean_summary = clean_tamil_text(getattr(article, "summary", ""))
        clean_title = clean_tamil_text(getattr(article, "title", ""))

        indent = "&emsp;&emsp;"
        paragraphs = "".join(f"<p>{indent}{clean_tamil_text(p)}</p>\n" for p in body_text.split("\n\n") if clean_tamil_text(p))
        return (
            f'<div class="arachudar-post" style="font-family: \'Mukta Malar\', sans-serif; max-width: 800px; margin: 0 auto; padding: 10px 0;">\n'
            f'<style>\n'
            f'  .arachudar-post {{ font-family: \'Mukta Malar\', sans-serif; max-width: 800px; margin: 0 auto; }}\n'
            f'  .arachudar-post .post-body p {{ font-size: 1.05rem; line-height: 2.0; color: #222; margin-bottom: 20px; text-align: justify; text-indent: 1.5rem; }}\n'
            f'  .arachudar-post .post-lead {{ font-size: 1.15rem; line-height: 1.9; color: #1a1a1a; margin-top: 16px; margin-bottom: 24px; padding: 14px 20px; background-color: #faf8f8; border-left: 4px solid #b71c1c; border-radius: 4px; font-weight: 600; text-indent: 1.5rem; }}\n'
            f'</style>\n'
            f'<div class="post-media" style="margin-top: 10px; margin-bottom: 24px; text-align: center;">\n'
            f'  <img src="{article.image}" alt="{clean_title}" style="max-width:100%; height:auto; border-radius:8px; box-shadow: 0 4px 14px rgba(0,0,0,0.08);" />\n'
            f'</div>\n'
            f'<p class="post-lead">\n'
            f'  <strong>{indent}{clean_summary}</strong>\n'
            f'</p>\n'
            f'<div class="post-body">\n{paragraphs}</div>\n'
            f'</div>'
        )

    def publish_article(self, article: ProcessedArticle, dry_run: bool = False) -> Dict[str, Any]:
        """
        Publishes article to Blogger, returning API response dict or dry-run report.
        Strictly enforces pure Tamil tags and labels.
        """
        clean_title = clean_tamil_text(article.title)
        label = TAMIL_CATEGORY_LABELS.get(article.category, article.category)
        raw_tags = [t for t in getattr(article, "tags", []) if t != label]
        cleaned_tags = [clean_tamil_text(t) for t in raw_tags if clean_tamil_text(t)]
        labels = [label] + [t for t in cleaned_tags if t != label]
        if getattr(article, "is_flash", False) and "மின்னல்" not in labels:
            labels.append("மின்னல்")

        payload = {
            "kind": "blogger#post",
            "title": clean_title,
            "content": self.format_post_html(article),
            "labels": labels
        }

        if dry_run:
            return {
                "status": "DRY_RUN",
                "published": False,
                "title": clean_title,
                "payload": payload
            }

        token = self.get_access_token()
        resp = requests.post(
            f"https://www.googleapis.com/blogger/v3/blogs/{self.blog_id}/posts",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()

