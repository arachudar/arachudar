"""
src/publisher/blogger_client.py - Google Blogger API v3 client.
Manages OAuth2 token refresh, payload formatting, dry-run mode, and publishing
Tamil news articles to Blogger (https://arachudar.blogspot.com/).
"""

import json
import os
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
        """
        body_text = getattr(article, "body", "")
        paragraphs = "".join(f"<p>{p.strip()}</p>" for p in body_text.split("\n\n") if p.strip())
        return (
            f'<div class="arachudar-post" style="font-family: \'Mukta Malar\', sans-serif;">\n'
            f'<div class="post-media"><img src="{article.image}" alt="{article.title}" style="max-width:100%; height:auto; border-radius:8px;" /></div>\n'
            f'<p class="post-lead"><strong>{article.summary}</strong></p>\n'
            f'<div class="post-body">{paragraphs}</div>\n'
            f'<div class="post-meta"><span>ஆசிரியர்: {article.author}</span> • <span>வழங்குபவர்: {article.source_name}</span></div>\n'
            f'</div>'
        )

    def publish_article(self, article: ProcessedArticle, dry_run: bool = False) -> Dict[str, Any]:
        """
        Publishes article to Blogger, returning API response dict or dry-run report.
        """
        label = TAMIL_CATEGORY_LABELS.get(article.category, article.category)
        tags = [t for t in getattr(article, "tags", []) if t != label]
        labels = [label] + tags
        if getattr(article, "is_flash", False) and "மின்னல்" not in labels:
            labels.append("மின்னல்")

        payload = {
            "kind": "blogger#post",
            "title": article.title,
            "content": self.format_post_html(article),
            "labels": labels
        }

        if dry_run:
            return {
                "status": "DRY_RUN",
                "published": False,
                "title": article.title,
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

