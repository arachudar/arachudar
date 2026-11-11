# -*- coding: utf-8 -*-
"""
Arachudar AI News Auto-Publisher
Publishes articles, categories, and breaking flash news to Blogger.
Connected directly to: https://arachudar.blogspot.com/ (ID: 563563588050874327)
"""

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BLOG_ID = "563563588050874327"

def get_blogger_service():
    if not os.path.exists("blogger_token.json"):
        raise FileNotFoundError("Blogger credentials not found in blogger_token.json.")

    with open("blogger_token.json", "r", encoding="utf-8") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes')
    )

    return build('blogger', 'v3', credentials=creds)

def publish_news_article(title, content_html, categories, is_flash=False, is_draft=False):
    """
    Publishes an AI generated news post directly to Blogger (arachudar.blogspot.com).
    
    :param title: News headline in Tamil
    :param content_html: Full news content formatted in HTML with paragraphs & images
    :param categories: List of labels/categories (e.g. ['தமிழ்நாடு', 'தொழில்நுட்பம்'])
    :param is_flash: If True, adds the 'மின்னல்' label for the Flash News Ticker
    :param is_draft: If True, saves as draft instead of publishing live
    :return: dict with post details from Blogger API
    """
    service = get_blogger_service()
    
    labels = list(categories) if categories else ['தமிழ்நாடு']
    if is_flash and 'மின்னல்' not in labels:
        labels.append('மின்னல்')

    body = {
        'kind': 'blogger#post',
        'title': title,
        'content': content_html,
        'labels': labels
    }

    result = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=is_draft).execute()
    
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
