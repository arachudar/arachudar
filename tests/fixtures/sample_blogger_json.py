"""
tests/fixtures/sample_blogger_json.py - Google OAuth 2.0 & Blogger API v3 Fixtures.
Provides realistic response payloads for OAuth2 refresh token exchange and
Blogger v3 post creation (200 OK, 400 Bad Request, 403 Forbidden, 404 Not Found).
"""

from typing import Dict, Any, List

# 1. OAuth 2.0 Token Exchange Success (200 OK)
MOCK_BLOGGER_OAUTH_SUCCESS: Dict[str, Any] = {
    "status_code": 200,
    "headers": {"Content-Type": "application/json; charset=utf-8"},
    "body": {
        "access_token": "ya29.a0AfH6SMBx_mock_token_for_arachudar_testing_1234567890",
        "expires_in": 3599,
        "scope": "https://www.googleapis.com/auth/blogger",
        "token_type": "Bearer"
    }
}

# 2. OAuth 2.0 Token Exchange Failure (400 Bad Request / invalid_grant)
MOCK_BLOGGER_OAUTH_INVALID_GRANT: Dict[str, Any] = {
    "status_code": 400,
    "headers": {"Content-Type": "application/json; charset=utf-8"},
    "body": {
        "error": "invalid_grant",
        "error_description": "Token has been expired or revoked."
    }
}

# 3. Blogger API v3 Post Creation Success (200 OK / 201 Created)
MOCK_BLOGGER_POST_SUCCESS: Dict[str, Any] = {
    "status_code": 200,
    "headers": {"Content-Type": "application/json; charset=UTF-8"},
    "body": {
        "kind": "blogger#post",
        "id": "7891234567890123456",
        "blog": {"id": "1234567890123456789"},
        "published": "2026-11-10T10:30:00Z",
        "updated": "2026-11-10T10:30:00Z",
        "url": "https://arachudarnews.blogspot.com/2026/11/metro-expansion-chennai.html",
        "selfLink": "https://www.googleapis.com/blogger/v3/blogs/1234567890123456789/posts/7891234567890123456",
        "title": "மெட்ரோ ரயில் வேகமெடுக்கிறது: பயண நேரம் 3 நிமிடங்களாக குறைப்பு",
        "content": (
            "<div class=\"arachudar-post\" style=\"font-family: 'Mukta Malar', sans-serif;\">"
            "<div class=\"post-media\"><img src=\"https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200\" style=\"max-width:100%;\" /></div>"
            "<p class=\"post-lead\"><strong>அண்ணா சாலையில் போக்குவரத்து மாற்றம்...</strong></p>"
            "<p>சென்னை அண்ணா சாலையில் நடைபெற்று வரும் மெட்ரோ ரயில் பணிகளால் தற்காலிக போக்குவரத்து மாற்றங்கள் அறிவிக்கப்பட்டுள்ளன...</p>"
            "</div>"
        ),
        "author": {
            "id": "1001",
            "displayName": "அறச்சுடர் சிறப்பு நிருபர்",
            "url": "https://www.blogger.com/profile/1001"
        },
        "labels": ["தமிழகம்", "சென்னை", "அரசியல்"],
        "status": "LIVE"
    }
}

# 4. Blogger API v3 Permission Denied (403 Forbidden)
MOCK_BLOGGER_POST_FORBIDDEN: Dict[str, Any] = {
    "status_code": 403,
    "headers": {"Content-Type": "application/json; charset=UTF-8"},
    "body": {
        "error": {
            "code": 403,
            "message": "We're sorry, but you do not have permission to post to this blog.",
            "errors": [
                {
                    "message": "We're sorry, but you do not have permission to post to this blog.",
                    "domain": "global",
                    "reason": "forbidden"
                }
            ],
            "status": "PERMISSION_DENIED"
        }
    }
}

# 5. Blogger API v3 Blog Not Found (404 Not Found)
MOCK_BLOGGER_POST_NOT_FOUND: Dict[str, Any] = {
    "status_code": 404,
    "headers": {"Content-Type": "application/json; charset=UTF-8"},
    "body": {
        "error": {
            "code": 404,
            "message": "Blog has not been found.",
            "errors": [
                {
                    "message": "Blog has not been found.",
                    "domain": "global",
                    "reason": "notFound"
                }
            ],
            "status": "NOT_FOUND"
        }
    }
}


def build_blogger_post_payload(
    title: str,
    content: str,
    labels: List[str]
) -> Dict[str, Any]:
    """Builds the JSON dictionary required for POST /v3/blogs/{blogId}/posts."""
    return {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels
    }
