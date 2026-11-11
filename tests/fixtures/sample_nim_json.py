"""
tests/fixtures/sample_nim_json.py - NVIDIA NIM API Chat Completion Fixtures.
Provides realistic OpenAI/NIM-compatible responses for nvidia/nemotron-3.5-bolt-e4b,
covering authentic Tamil content, NVCF HTTP 429 quota errors, HTTP 503 overload,
markdown backtick wrapping, truncated JSON, and <think> token leakage.
"""

from typing import Dict, Any, Optional
import json

# Authentic Tamil journalistic article conforming directly to Arachudar schema
SAMPLE_TAMIL_AI_CONTENT: Dict[str, Any] = {
    "category": "tamilnadu",
    "subCategory": "chennai",
    "title": "மெட்ரோ ரயில் வேகமெடுக்கிறது: பயண நேரம் 3 நிமிடங்களாக குறைப்பு",
    "summary": "அண்ணா சாலையில் போக்குவரத்து மாற்றம்; கோயம்பேடு-பரங்கிமலை வழித்தடத்தில் புதிய சிக்னல் முறை அறிமுகம்.",
    "body": "சென்னை அண்ணா சாலையில் நடைபெற்று வரும் மெட்ரோ ரயில் பணிகளால் தற்காலிக போக்குவரத்து மாற்றங்கள் அறிவிக்கப்பட்டுள்ளன. கோயம்பேடு முதல் பரங்கிமலை வரையிலான மெட்ரோ வழித்தடத்தில் புதிய தானியங்கி சிக்னல் முறை வெற்றிகரமாக நிறுவப்பட்டுள்ளது.\n\nஇதன் மூலம் ரயில்களின் இயக்கம் துரிதப்படுத்தப்பட்டு, பயண நேரம் 3 நிமிடங்களாக குறைக்கப்படும் என மெட்ரோ நிர்வாகம் தெரிவித்துள்ளது. பொதுமக்கள் புதிய அட்டவணையை பயன்படுத்தி பயணங்களை திட்டமிடுமாறு கேட்டுக்கொள்ளப்படுகிறார்கள்.",
    "author": "அறச்சுடர் சிறப்பு நிருபர்",
    "tags": ["மெட்ரோரயில்", "சென்னைபோக்குவரத்து", "புதியதொழில்நுட்பம்", "நகர்ப்புறமேம்பாடு"],
    "isFlash": True
}


def build_nvidia_chat_response(
    content: str,
    model: str = "nvidia/nemotron-3.5-bolt-e4b",
    finish_reason: str = "stop",
    reasoning_content: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to construct an OpenAI/NIM compliant chat completion response dictionary."""
    return {
        "id": "chatcmpl-992e0959-919e-437a-bf23-086b0a6da317",
        "object": "chat.completion",
        "created": 1794325166,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "reasoning_content": reasoning_content
                },
                "finish_reason": finish_reason,
                "logprobs": None
            }
        ],
        "usage": {
            "prompt_tokens": 280,
            "completion_tokens": 195,
            "total_tokens": 475
        }
    }


# 1. 200 OK Standard JSON Completion
MOCK_NIM_SUCCESS_RESPONSE: Dict[str, Any] = build_nvidia_chat_response(
    content=json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False)
)

# 2. Markdown-fenced JSON completion (```json\n...\n```)
MOCK_NIM_MARKDOWN_WRAPPED_RESPONSE: Dict[str, Any] = build_nvidia_chat_response(
    content=f"```json\n{json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False, indent=2)}\n```"
)

# 3. Truncated / Incomplete JSON (finish_reason = "length")
TRUNCATED_JSON_STRING = '{"category": "tamilnadu", "subCategory": "chennai", "title": "மெட்ரோ ரயில் வேகமெடு'
MOCK_NIM_TRUNCATED_RESPONSE: Dict[str, Any] = build_nvidia_chat_response(
    content=TRUNCATED_JSON_STRING,
    finish_reason="length"
)

# 4. Chain-of-thought <think> token leakage
MOCK_NIM_REASONING_LEAK_RESPONSE: Dict[str, Any] = build_nvidia_chat_response(
    content=(
        "<think>\n"
        "User requests a Tamil news article about Chennai Metro expansion.\n"
        "I will set category to tamilnadu and subCategory to chennai.\n"
        "Generating professional journalistic headline and lead summary.\n"
        "</think>\n"
        f"{json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False)}"
    )
)

# 5. Non-compliant English prose / apology response
MOCK_NIM_APOLOGY_RESPONSE: Dict[str, Any] = build_nvidia_chat_response(
    content="I apologize, but I am unable to generate the news article in the requested format at this time."
)

# 6. HTTP 429 Too Many Requests (NVCF Gateway RFC 7807 problem details)
MOCK_NIM_429_PAYLOAD: Dict[str, Any] = {
    "status_code": 429,
    "headers": {
        "Content-Type": "application/problem+json",
        "Nvcf-Error-Source": "rate_limit",
        "Retry-After": "20",
        "X-Request-Id": "8c12a789-ef34-4b56-9123-abcdef012345"
    },
    "body": {
        "type": "about:blank",
        "title": "Too Many Requests",
        "status": 429,
        "detail": "Rate limit exceeded: 40 requests per minute limit reached for model nvidia/nemotron-3.5-bolt-e4b."
    }
}

# 7. HTTP 503 Service Unavailable (NIM backend maintenance / overload)
MOCK_NIM_503_PAYLOAD: Dict[str, Any] = {
    "status_code": 503,
    "headers": {
        "Content-Type": "application/problem+json",
        "Nvcf-Status": "unavailable",
        "Retry-After": "5",
        "X-Request-Id": "9d34b890-fa45-4c67-8234-bcdef0123456"
    },
    "body": {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The backend service for nvidia/nemotron-3.5-bolt-e4b is currently overloaded. Please retry later."
    }
}
