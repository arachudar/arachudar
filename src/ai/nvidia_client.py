"""
src/ai/nvidia_client.py - NVIDIA NIM API Client with Rate Limiting and Resilience.
Provides OpenAI-compatible chat completion access to nvidia/nemotron-3.5-bolt-e4b
with automatic model failover, exponential backoff, and TokenBucketRateLimiter pacing.
"""

import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from src.ai.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# Load local .env if present
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

# Default API configuration
DEFAULT_NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "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")
DEFAULT_NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_PRIMARY_MODEL = "nvidia/nemotron-3.5-bolt-e4b"
DEFAULT_FALLBACK_MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"


class NvidiaClientError(Exception):
    """Base exception for all NVIDIA client errors."""
    pass


class NvidiaRateLimitExceeded(NvidiaClientError):
    """Raised when rate limit (HTTP 429) retries are exhausted."""
    pass


class NvidiaModelUnavailableError(NvidiaClientError):
    """Raised when primary and fallback models are unavailable (HTTP 404, 410, 503)."""
    pass


class NvidiaAPIError(NvidiaClientError):
    """Raised on general API errors (HTTP 4xx/5xx)."""
    pass


class NvidiaClient:
    """
    Client for interacting with NVIDIA NIM API Chat Completions.
    Integrates rate limiting, exponential backoff with jitter, and model failover.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_PRIMARY_MODEL,
        fallback_model: str = DEFAULT_FALLBACK_MODEL,
        endpoint: str = DEFAULT_NVIDIA_ENDPOINT,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the NVIDIA client.

        Args:
            api_key: NVIDIA API Key (defaults to NVIDIA_API_KEY env or preset key).
            model: Primary completion model.
            fallback_model: Secondary model to use if primary fails.
            endpoint: Completions API URL.
            rate_limiter: TokenBucketRateLimiter instance for pacing calls.
            timeout: Default request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY") or DEFAULT_NVIDIA_API_KEY
        self.model = model
        self.fallback_model = fallback_model
        self.endpoint = endpoint
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(rate_rpm=30.0, capacity=4.0)
        self.timeout = timeout

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        max_retries: int = 3,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a chat completion with rate limiting and automated retry/fallback.

        Args:
            messages: List of chat message dictionaries ({role, content}).
            model: Specific model to use, or default to self.model.
            temperature: Sampling temperature (default 0.2 for editorial precision).
            max_tokens: Maximum tokens in completion.
            max_retries: Number of retry attempts on transient errors.
            timeout: Request timeout in seconds.
            **kwargs: Extra parameters passed to completion payload.

        Returns:
            Decoded JSON dictionary from the NVIDIA completion response.

        Raises:
            NvidiaRateLimitExceeded: When HTTP 429 persists beyond max_retries.
            NvidiaModelUnavailableError: When models return 404/410/503 and cannot recover.
            NvidiaAPIError: On unexpected 4xx/5xx API responses.
            NvidiaClientError: On network failures after retries.
        """
        # 1. Enforce client-side rate limiting
        self.rate_limiter.acquire(1.0)

        current_model = model or self.model
        req_timeout = timeout or self.timeout

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        attempt = 0
        while attempt <= max_retries:
            payload = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }

            try:
                resp = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=req_timeout,
                )
            except requests.RequestException as e:
                if attempt < max_retries:
                    attempt += 1
                    backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                    logger.warning(
                        f"NVIDIA request error: {e}. Retrying in {backoff:.2f}s (attempt {attempt}/{max_retries})..."
                    )
                    self.rate_limiter.sleep_func(backoff)
                    continue
                raise NvidiaClientError(f"Network error communicating with NVIDIA API: {e}") from e

            # 200 OK
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as e:
                    raise NvidiaAPIError(f"Invalid JSON response from NVIDIA API: {resp.text}") from e

            # HTTP 429 Too Many Requests
            if resp.status_code == 429:
                if attempt >= max_retries:
                    raise NvidiaRateLimitExceeded(
                        f"NVIDIA API rate limit exceeded (HTTP 429) after {max_retries} retries: {resp.text}"
                    )
                attempt += 1
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        backoff = float(retry_after)
                    except (ValueError, TypeError):
                        backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                else:
                    backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                logger.warning(
                    f"HTTP 429 Rate limited. Backing off for {backoff:.2f}s (attempt {attempt}/{max_retries})..."
                )
                self.rate_limiter.sleep_func(backoff)
                continue

            # HTTP 404 / 410 Model Not Found or Gone -> immediate fallback
            if resp.status_code in (404, 410):
                if current_model != self.fallback_model:
                    logger.warning(
                        f"Model '{current_model}' returned HTTP {resp.status_code}. "
                        f"Failing over to fallback model '{self.fallback_model}'..."
                    )
                    current_model = self.fallback_model
                    attempt = 0
                    continue
                raise NvidiaModelUnavailableError(
                    f"Model '{current_model}' is unavailable (HTTP {resp.status_code}): {resp.text}"
                )

            # HTTP 503 Service Unavailable
            if resp.status_code == 503:
                if attempt < max_retries:
                    attempt += 1
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            backoff = float(retry_after)
                        except (ValueError, TypeError):
                            backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                    else:
                        backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                    logger.warning(
                        f"HTTP 503 Service Unavailable. Backing off for {backoff:.2f}s "
                        f"(attempt {attempt}/{max_retries})..."
                    )
                    self.rate_limiter.sleep_func(backoff)
                    continue

                # Primary model exhausted 503 retries -> failover
                if current_model != self.fallback_model:
                    logger.warning(
                        f"Model '{current_model}' exhausted 503 retries. "
                        f"Failing over to fallback model '{self.fallback_model}'..."
                    )
                    current_model = self.fallback_model
                    attempt = 0
                    continue

                raise NvidiaModelUnavailableError(
                    f"NVIDIA API service unavailable (HTTP 503) for all models: {resp.text}"
                )

            # Client errors (4xx)
            if 400 <= resp.status_code < 500:
                raise NvidiaAPIError(
                    f"NVIDIA API client error HTTP {resp.status_code}: {resp.text}"
                )

            # Server errors (5xx)
            if resp.status_code >= 500:
                if attempt < max_retries:
                    attempt += 1
                    backoff = min(60.0, (2 ** attempt) + random.uniform(0.1, 0.5))
                    logger.warning(
                        f"HTTP {resp.status_code} server error. Backing off for {backoff:.2f}s..."
                    )
                    self.rate_limiter.sleep_func(backoff)
                    continue
                raise NvidiaAPIError(
                    f"NVIDIA API server error HTTP {resp.status_code} after retries: {resp.text}"
                )

        raise NvidiaClientError(f"Unexpected completion loop termination for {current_model}")

    def synthesize(self, raw_article: Any, article_id: int = 1) -> Any:
        """
        Convenience method to synthesize a RawArticle into a ProcessedArticle.
        Delegates to TamilSynthesizer.
        """
        from src.ai.tamil_synthesizer import TamilSynthesizer
        synthesizer = TamilSynthesizer(nvidia_client=self)
        return synthesizer.synthesize(raw_article, article_id=article_id)
