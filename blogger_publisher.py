# -*- coding: utf-8 -*-
"""
Arachudar AI News Auto-Publisher
Publishes articles, categories, and breaking flash news to Blogger.
Connected directly to: https://arachudar.blogspot.com/ (ID: 563563588050874327)
Unified with src.publisher.blogger_client architecture.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.publisher.blogger_client import BloggerClient
from src.ai.tamil_synthesizer import ProcessedArticle

BLOG_ID = "563563588050874327"


def get_blogger_service():
    """Returns official Google Blogger API service client."""
    client = BloggerClient(blog_id=BLOG_ID)
    return client.get_blogger_service()


def publish_news_article(title: str, content_html: str, categories: Optional[List[str]] = None, is_flash: bool = False, is_draft: bool = False):
    """
    Publishes an AI generated news post directly to Blogger (arachudar.blogspot.com).

    :param title: News headline in Tamil
    :param content_html: Full news content formatted in HTML with paragraphs & images
    :param categories: List of labels/categories (e.g. ['தமிழ்நாடு', 'தொழில்நுட்பம்'])
    :param is_flash: If True, adds the 'மின்னல்' label for the Flash News Ticker
    :param is_draft: If True, saves as draft instead of publishing live
    :return: dict with post details from Blogger API
    """
    client = BloggerClient(blog_id=BLOG_ID)
    service = client.get_blogger_service()

    labels = list(categories) if categories else ['தமிழ்நாடு']
    if is_flash and 'மின்னல்' not in labels:
        labels.append('மின்னல்')

    body = {
        'kind': 'blogger#post',
        'title': title,
        'content': content_html,
        'labels': labels
    }

    if service:
        result = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=is_draft).execute()
    else:
        # Fallback to direct REST API
        import requests
        token = client.get_access_token()
        query = "?isDraft=true" if is_draft else ""
        resp = requests.post(
            f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts{query}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15
        )
        resp.raise_for_status()
        result = resp.json()

    print("\n=======================================================")
    print("   செய்தி வெற்றிகரமாக பதிவிடப்பட்டது (Published!)")
    print("=======================================================")
    print(f"Title:    {result.get('title')}")
    print(f"Post URL: {result.get('url')}")
    print(f"Labels:   {', '.join(result.get('labels', []))}")
    print("=======================================================\n")

    return result


if __name__ == '__main__':
    print("Arachudar Blogger Publisher is connected and ready.")
