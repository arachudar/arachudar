"""
src/ai - Arachudar AI Synthesis & Rate Control Subsystem.
Provides token-bucket rate limiting, resilient NVIDIA NIM chat client,
authentic Tamil journalistic synthesis, and ProcessedArticle contracts.
"""

from src.ai.rate_limiter import TokenBucketRateLimiter
from src.ai.nvidia_client import (
    NvidiaClient,
    NvidiaClientError,
    NvidiaRateLimitExceeded,
    NvidiaModelUnavailableError,
    NvidiaAPIError,
)
from src.ai.tamil_synthesizer import (
    TamilSynthesizer,
    ProcessedArticle,
    SynthesisError,
    detect_mojibake,
    is_valid_tamil_text,
    format_tamil_date,
    format_time_ago,
    calculate_read_time,
)

__all__ = [
    "TokenBucketRateLimiter",
    "NvidiaClient",
    "NvidiaClientError",
    "NvidiaRateLimitExceeded",
    "NvidiaModelUnavailableError",
    "NvidiaAPIError",
    "TamilSynthesizer",
    "ProcessedArticle",
    "SynthesisError",
    "detect_mojibake",
    "is_valid_tamil_text",
    "format_tamil_date",
    "format_time_ago",
    "calculate_read_time",
]
