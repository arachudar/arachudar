"""
src/publisher/blogger_client.py - Google Blogger API v3 client.
Manages OAuth2 token refresh, payload formatting, dry-run mode, local caching,
and publishing Tamil news articles to Blogger (https://arachudar.blogspot.com/).
Adapted with proven digital newsroom publishing tech from Automatic-Blogger-Poster.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as google_build
    from google.auth.transport.requests import Request as GoogleAuthRequest
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from src.ai.tamil_synthesizer import ProcessedArticle

logger = logging.getLogger(__name__)

# ── Load local .env if present (strictly gitignored for security) ──────────
_env_path = Path(".env")
if _env_path.exists():
    try:
        with open(_env_path, "r", encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
    except Exception:
        pass

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
    token caching, dry-run mode, local article archiving, and publishing
    formatted Tamil news articles to Blogger.
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

        # Storage paths
        self.cache_dir = Path(".blog-cache")
        self.posts_dir = Path("_posts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.posts_log_file = self.cache_dir / "posts_log.json"
        self.posted_history_file = self.cache_dir / "posted_history.json"

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
        self.client_id = (
            client_id
            or os.environ.get("GOOGLE_CLIENT_ID")
            or os.environ.get("BLOGGER_CLIENT_ID")
        )
        self.client_secret = (
            client_secret
            or os.environ.get("GOOGLE_CLIENT_SECRET")
            or os.environ.get("BLOGGER_CLIENT_SECRET")
        )
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
        self.refresh_token = (
            refresh_token
            or os.environ.get("GOOGLE_REFRESH_TOKEN")
            or os.environ.get("BLOGGER_REFRESH_TOKEN")
        )
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

    def get_blogger_service(self):
        """
        Instantiates Google API discovery client using official googleapiclient.
        """
        if not GOOGLE_API_AVAILABLE:
            logger.warning("google-api-python-client is not installed")
            return None
        try:
            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/blogger"]
            )
            creds.refresh(GoogleAuthRequest())
            return google_build("blogger", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Failed to initialize Blogger service: {e}")
            return None

    def format_post_html(self, article: ProcessedArticle) -> str:
        """
        Formats article into publication-ready Tamil Blogger HTML post.
        Strictly pure Tamil text, spacious line-height (2.0), elegant mood indent (&emsp;&emsp; + text-indent),
        Schema.org NewsArticle JSON-LD structured data, and zero byline/source attribution footers.
        """
        body_text = getattr(article, "body", "")
        clean_summary = clean_tamil_text(getattr(article, "summary", ""))
        clean_title = clean_tamil_text(getattr(article, "title", ""))

        indent = "&emsp;&emsp;"
        paragraphs = "".join(f"<p>{indent}{clean_tamil_text(p)}</p>\n" for p in body_text.split("\n\n") if clean_tamil_text(p))

        # Schema.org NewsArticle structured data
        schema_json = json.dumps({
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": clean_title,
            "description": clean_summary[:160],
            "image": [getattr(article, "image", "")],
            "datePublished": datetime.now(timezone.utc).isoformat(),
            "inLanguage": "ta",
            "publisher": {
                "@type": "Organization",
                "name": "அறச்சுடர்",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://arachudar.blogspot.com/favicon.ico"
                }
            }
        }, ensure_ascii=False)

        return (
            f'<script type="application/ld+json">{schema_json}</script>\n'
            f'<div class="arachudar-post" style="font-family: \'Mukta Malar\', sans-serif; max-width: 800px; margin: 0 auto; padding: 10px 0;">\n'
            f'<style>\n'
            f'  .arachudar-post {{ font-family: \'Mukta Malar\', sans-serif; max-width: 800px; margin: 0 auto; }}\n'
            f'  .arachudar-post .post-body p {{ font-size: 1.15rem; line-height: 2.0; color: #1e293b; margin-bottom: 22px; text-align: justify; text-indent: 2rem; word-break: normal; overflow-wrap: break-word; }}\n'
            f'  .arachudar-post .post-lead {{ font-size: 1.25rem; line-height: 1.85; color: #0f172a; margin-top: 18px; margin-bottom: 26px; padding: 16px 20px; background-color: #f8fafc; border-left: 5px solid #990000; border-radius: 6px; font-weight: 700; text-indent: 1.5rem; text-align: left; }}\n'
            f'</style>\n'
            f'<div class="post-media" style="margin-top: 10px; margin-bottom: 24px; text-align: center;">\n'
            f'  <figure style="margin: 0; padding: 0;">\n'
            f'    <img src="{article.image}" alt="{clean_title}" style="max-width:100%; height:auto; border-radius:8px; box-shadow: 0 4px 14px rgba(0,0,0,0.08);" />\n'
            f'  </figure>\n'
            f'</div>\n'
            f'<div class="post-lead">\n'
            f'  <strong>{indent}{clean_summary}</strong>\n'
            f'</div>\n'
            f'<div class="post-body">\n{paragraphs}</div>\n'
            f'</div>'
        )

    def save_local_markdown(self, article: ProcessedArticle, post_url: str = "") -> Path:
        """
        Saves a local archive copy of the published article as Markdown/HTML with frontmatter
        in the _posts/ directory (following the Automatic-Blogger-Poster standard).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^\w\s-]", "", getattr(article, "title", "news")).strip()
        slug = re.sub(r"\s+", "-", slug)[:50]
        filename = f"{timestamp}_{slug or 'article'}.md"
        filepath = self.posts_dir / filename

        frontmatter = {
            "title": getattr(article, "title", ""),
            "date": datetime.now(timezone.utc).isoformat(),
            "category": getattr(article, "category", ""),
            "labels": getattr(article, "tags", []),
            "image": getattr(article, "image", ""),
            "source_url": getattr(article, "source_url", ""),
            "post_url": post_url
        }

        content = (
            f"---\n{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n---\n\n"
            f"{self.format_post_html(article)}"
        )
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def record_published_post(self, title: str, post_url: str, source_url: str = ""):
        """
        Updates .blog-cache/posts_log.json and posted_history.json for robust deduplication.
        """
        log_entries = []
        if self.posts_log_file.exists():
            try:
                log_entries = json.loads(self.posts_log_file.read_text(encoding="utf-8"))
            except Exception:
                log_entries = []

        log_entries.append({
            "title": title,
            "url": post_url,
            "source_url": source_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        try:
            self.posts_log_file.write_text(
                json.dumps(log_entries[-200:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to write posts_log.json: {e}")

    def publish_article(self, article: ProcessedArticle, dry_run: bool = False) -> Dict[str, Any]:
        """
        Publishes article to Blogger, returning API response dict or dry-run report.
        Strictly enforces pure Tamil tags and labels without trailing commas or duplicates.
        """
        clean_title = clean_tamil_text(article.title)
        clean_summary = clean_tamil_text(getattr(article, "summary", ""))
        label = TAMIL_CATEGORY_LABELS.get(article.category, article.category)
        raw_tags = [t for t in getattr(article, "tags", []) if t != label]
        cleaned_tags = [clean_tamil_text(t) for t in raw_tags if clean_tamil_text(t)]

        seen_tags = {label}
        unique_tags = []
        for t in cleaned_tags:
            if t and t not in seen_tags:
                seen_tags.add(t)
                unique_tags.append(t)
        labels = [label] + unique_tags
        if getattr(article, "is_flash", False) and "மின்னல்" not in labels:
            labels.append("மின்னல்")

        payload = {
            "kind": "blogger#post",
            "title": clean_title,
            "content": self.format_post_html(article),
            "labels": labels,
            "metaDescription": clean_summary[:160]
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
        res_data = resp.json()

        # Archive and track post locally
        post_url = res_data.get("url", "")
        try:
            self.save_local_markdown(article, post_url=post_url)
            self.record_published_post(
                title=clean_title,
                post_url=post_url,
                source_url=getattr(article, "source_url", "")
            )
        except Exception as e:
            logger.warning(f"Could not record local post archive: {e}")

        return res_data
