"""
tests/helpers/blogger_contract.py
Contract reference implementation for Google Blogger API v3 client (Feature 10)
and dry-run verification (Feature 13).
"""

from typing import List, Dict, Any, Optional
import os
import time
import requests

from tests.fixtures.sample_articles import ProcessedArticle

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
        blog_id: str = "test-mock-blog-id-12345",
        client_id: str = "test-mock-client-id.apps.googleusercontent.com",
        client_secret: str = "test-mock-client-secret",
        refresh_token: str = "test-mock-refresh-token",
        time_func=time.time
    ):
        self.blog_id = blog_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.time_func = time_func
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_access_token(self, force_refresh: bool = False) -> str:
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
            }
        )
        resp.raise_for_status()
        data = resp.json()
        self._cached_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = now + float(expires_in)
        return self._cached_token

    def format_post_html(self, article: ProcessedArticle) -> str:
        paragraphs = "".join(f"<p>{p.strip()}</p>" for p in article.body.split("\n\n") if p.strip())
        return (
            f'<div class="arachudar-post" style="font-family: \'Mukta Malar\', sans-serif;">\n'
            f'<div class="post-media"><img src="{article.image}" alt="{article.title}" style="max-width:100%; height:auto; border-radius:8px;" /></div>\n'
            f'<p class="post-lead"><strong>{article.summary}</strong></p>\n'
            f'<div class="post-body">{paragraphs}</div>\n'
            f'<div class="post-meta"><span>ஆசிரியர்: {article.author}</span> • <span>வழங்குபவர்: {article.source_name}</span></div>\n'
            f'</div>'
        )

    def publish_article(self, article: ProcessedArticle, dry_run: bool = False) -> Dict[str, Any]:
        label = TAMIL_CATEGORY_LABELS.get(article.category, article.category)
        payload = {
            "kind": "blogger#post",
            "title": article.title,
            "content": self.format_post_html(article),
            "labels": [label] + [t for t in article.tags if t != label]
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
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload
        )
        resp.raise_for_status()
        return resp.json()
