"""
src/publisher/social_hooks.py - Social channel formatters and dispatch hooks.
Formatting helpers and dispatch stubs for X (280-char limit), Facebook Graph API,
Instagram Photo Container, and YouTube Community posts.
"""

import os
from typing import List, Dict, Any, Optional
from src.ai.tamil_synthesizer import ProcessedArticle


class SocialHooks:
    """
    Social channel formatters and stubs for X (280-char clipping),
    Facebook, Instagram, and YouTube.
    """
    CHANNELS = ["x", "facebook", "instagram", "youtube"]

    @staticmethod
    def format_x_post(title: str, summary: str, url: str, tags: Optional[List[str]] = None) -> str:
        """
        Formats and clips news story for X (Twitter) within strict 280-character boundary.
        """
        tag_str = " " + " ".join(f"#{t}" for t in (tags or ["அறச்சுடர்", "செய்திகள்"]))
        suffix = f"\n\nமுழு செய்தி: {url}{tag_str}"
        max_content_len = 280 - len(suffix)
        full_text = f"{title}\n{summary}"
        if len(full_text) <= max_content_len:
            return f"{full_text}{suffix}"
        clipped = full_text[:max_content_len - 3]
        last_space = clipped.rfind(" ")
        if last_space > 0:
            clipped = clipped[:last_space]
        return f"{clipped}...{suffix}"

    @staticmethod
    def format_facebook_post(title: str, summary: str = "", url: str = "") -> Dict[str, str]:
        """
        Formats story payload for Facebook Page post.
        """
        lead = summary.strip() if summary and summary.strip() else title.strip()
        return {
            "message": f"🔴 {title}\n\n{lead}\n\nமேலும் விவரங்களுக்கு: {url}" if summary else f"🔴 {title}\n\nமேலும் விவரங்களுக்கு: {url}",
            "link": url
        }

    @staticmethod
    def format_instagram_post(image_url: Optional[str], caption: str) -> Dict[str, str]:
        """
        Formats story payload for Instagram photo feed.
        """
        if not image_url or not str(image_url).strip():
            raise ValueError("Instagram requires a valid media URL")
        return {
            "image_url": str(image_url).strip(),
            "caption": f"{caption}\n\n#TamilNews #Arachudar #BreakingNews"
        }

    @staticmethod
    def format_youtube_post(title: str, body: str) -> Dict[str, str]:
        """
        Formats story for YouTube Community tab.
        """
        return {
            "title": title,
            "text": f"{body}\n\nஅறச்சுடர் செய்திகளை உடனுக்குடன் பெற சப்ஸ்கிரைப் செய்யுங்கள்."
        }

    @classmethod
    def broadcast_article(
        cls,
        article: Optional[ProcessedArticle] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Broadcasts article across configured social channels.
        By default, channels are skipped unless explicitly enabled via environment flags.
        """
        env = env if env is not None else os.environ
        statuses = {}
        for ch in cls.CHANNELS:
            is_enabled = env.get(f"ENABLE_{ch.upper()}", "false").lower() == "true"
            statuses[ch] = "published" if is_enabled else "skipped"
        return statuses

