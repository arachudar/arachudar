"""
src/ai/test_ai.py - Comprehensive Unit Test Suite for Arachudar AI Subsystem.
Tests TokenBucketRateLimiter, NvidiaClient, TamilSynthesizer, and ProcessedArticle contracts.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time
from typing import Dict, Any, List
import unittest.mock as mock

import pytest
import requests

from src.aggregator.feed_fetcher import RawArticle
from src.ai import (
    TokenBucketRateLimiter,
    NvidiaClient,
    NvidiaClientError,
    NvidiaRateLimitExceeded,
    NvidiaModelUnavailableError,
    NvidiaAPIError,
    TamilSynthesizer,
    ProcessedArticle,
    SynthesisError,
    is_valid_tamil_text,
    detect_mojibake,
    format_tamil_date,
    format_time_ago,
    calculate_read_time,
)
from tests.fixtures.sample_articles import SAMPLE_RAW_ARTICLES
from tests.fixtures.sample_nim_json import (
    SAMPLE_TAMIL_AI_CONTENT,
    MOCK_NIM_SUCCESS_RESPONSE,
    MOCK_NIM_MARKDOWN_WRAPPED_RESPONSE,
    MOCK_NIM_TRUNCATED_RESPONSE,
    MOCK_NIM_REASONING_LEAK_RESPONSE,
    MOCK_NIM_APOLOGY_RESPONSE,
    MOCK_NIM_429_PAYLOAD,
    MOCK_NIM_503_PAYLOAD,
    build_nvidia_chat_response,
)
from tests.helpers.virtual_clock import VirtualClock, verify_rate_limit_timings
from tests.helpers.unicode_validator import (
    assert_clean_tamil_headline,
    assert_clean_tamil_body,
    TAMIL_CODEPOINT_PATTERN,
)


@pytest.fixture
def virtual_clock():
    """Provides a controllable VirtualClock patching time.monotonic and time.sleep."""
    clock = VirtualClock(start_time=1000.0)
    with mock.patch("time.monotonic", side_effect=clock.monotonic), \
         mock.patch("time.sleep", side_effect=clock.sleep):
        yield clock


@pytest.fixture(autouse=True)
def default_nvidia_network_mock():
    """Default hermetic mock for NVIDIA chat completions, overridable by test-specific mocks."""
    def mock_post(url, *args, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.text = json.dumps(MOCK_NIM_SUCCESS_RESPONSE, ensure_ascii=False)
        resp.json.return_value = MOCK_NIM_SUCCESS_RESPONSE
        resp.headers = {"Content-Type": "application/json"}
        return resp

    with mock.patch("requests.post", side_effect=mock_post):
        yield


# ============================================================================
# 1. TokenBucketRateLimiter Unit Tests
# ============================================================================

class TestTokenBucketRateLimiter:
    """Verifies token bucket rate limiter initialization, burst, refill, pacing, and thread safety."""

    def test_rate_limiter_defaults_and_validation(self):
        """Rate limiter initializes with valid defaults and rejects non-positive parameters."""
        limiter = TokenBucketRateLimiter()
        assert limiter.rate == 0.5  # 30 RPM / 60 = 0.5 tokens/sec
        assert limiter.capacity == 4.0
        assert limiter.tokens == 4.0

        with pytest.raises(ValueError):
            TokenBucketRateLimiter(rate=0)
        with pytest.raises(ValueError):
            TokenBucketRateLimiter(rate=-0.5)
        with pytest.raises(ValueError):
            TokenBucketRateLimiter(capacity=0)
        with pytest.raises(ValueError):
            TokenBucketRateLimiter(capacity=-4.0)

    def test_rate_limiter_negative_token_request(self):
        """Requesting negative tokens raises ValueError."""
        limiter = TokenBucketRateLimiter()
        with pytest.raises(ValueError):
            limiter.acquire(-1.0)
        with pytest.raises(ValueError):
            limiter.try_acquire(-1.0)

    def test_burst_capacity_immediate_acquisition(self, virtual_clock):
        """Burst capacity of 4 allows 4 immediate requests with 0 delay."""
        limiter = TokenBucketRateLimiter(
            rate_rpm=30.0,
            capacity=4.0,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        for _ in range(4):
            delay = limiter.acquire(1.0)
            assert delay == 0.0
        assert virtual_clock.total_slept == 0.0
        assert limiter.tokens == 0.0

    def test_refill_rate_deterministic(self, virtual_clock):
        """Tokens refill at 0.5 tokens/sec (2.0s = 1.0 token)."""
        limiter = TokenBucketRateLimiter(
            rate_per_sec=0.5,
            capacity=4.0,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        # Drain all 4 tokens
        for _ in range(4):
            limiter.acquire(1.0)
        assert limiter.tokens == 0.0

        # Advance 2 seconds -> exactly 1 token should be available
        virtual_clock.advance(2.0)
        assert limiter.tokens == pytest.approx(1.0, rel=1e-2)
        assert limiter.try_acquire(1.0) is True
        assert limiter.tokens == 0.0

    def test_pacing_post_burst_exhaustion(self, virtual_clock):
        """When burst is exhausted, acquire() sleeps 2.0s per token."""
        limiter = TokenBucketRateLimiter(
            rate_rpm=30.0,
            capacity=4.0,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        for _ in range(4):
            limiter.acquire(1.0)

        # 5th and 6th calls must sleep 2.0s each
        delay5 = limiter.acquire(1.0)
        delay6 = limiter.acquire(1.0)

        assert delay5 == pytest.approx(2.0, rel=1e-2)
        assert delay6 == pytest.approx(2.0, rel=1e-2)
        assert len(virtual_clock.sleep_history) == 2
        assert virtual_clock.total_slept == pytest.approx(4.0, rel=1e-2)

    def test_rapid_10_sequential_requests(self, virtual_clock):
        """10 rapid sequential requests require (10 - 4) * 2.0s = 12.0s total sleep."""
        limiter = TokenBucketRateLimiter(
            rate_per_sec=0.5,
            capacity=4.0,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        for _ in range(10):
            limiter.acquire(1.0)

        assert len(virtual_clock.sleep_history) == 6
        assert virtual_clock.total_slept == pytest.approx(12.0, rel=1e-2)
        verify_rate_limit_timings(virtual_clock.sleep_history, expected_delay=2.0, tolerance=0.1)

    def test_try_acquire_non_blocking(self, virtual_clock):
        """try_acquire returns True when available and False without sleeping when depleted."""
        limiter = TokenBucketRateLimiter(
            rate_rpm=30.0,
            capacity=2.0,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        assert limiter.try_acquire(1.0) is True
        assert limiter.try_acquire(1.0) is True
        assert limiter.try_acquire(1.0) is False
        assert virtual_clock.total_slept == 0.0

    def test_clock_skew_recovery(self, virtual_clock):
        """Backward time jump does not corrupt token count or crash limiter."""
        limiter = TokenBucketRateLimiter(
            capacity=4.0,
            rate=0.5,
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep,
        )
        limiter.last_update = virtual_clock.monotonic() + 5000.0  # simulate future clock jump
        delay = limiter.acquire(1.0)
        assert limiter.tokens >= 0.0

    def test_multithreaded_concurrency(self):
        """Concurrent threads acquire tokens without data races or corruption."""
        limiter = TokenBucketRateLimiter(rate_rpm=120.0, capacity=10.0)
        acquired_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal acquired_count
            if limiter.try_acquire(1.0):
                with lock:
                    acquired_count += 1

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(20)]
            for f in futures:
                f.result()

        # At most capacity (10) tokens could be acquired instantly
        assert acquired_count <= 10


# ============================================================================
# 2. NvidiaClient Unit Tests
# ============================================================================

class TestNvidiaClient:
    """Verifies NvidiaClient request structure, auth, backoff, 429, 503, and fallback logic."""

    def test_client_initialization_defaults(self):
        """Client initializes with preset defaults and custom configuration."""
        client = NvidiaClient()
        assert client.model == "nvidia/nemotron-3.5-bolt-e4b"
        assert client.fallback_model == "nvidia/nemotron-3.5-super-vl-120b-a12b"
        assert "nvapi-" in client.api_key
        assert client.rate_limiter is not None

    def test_create_chat_completion_success_200(self):
        """Successful 200 OK completion returns expected dictionary."""
        client = NvidiaClient()
        messages = [
            {"role": "system", "content": "நீங்கள் Arachudar செய்தி ஆசிரியர்."},
            {"role": "user", "content": "சென்னை மெட்ரோ பணிகள் குறித்து செய்தி எழுதுக."}
        ]
        resp = client.create_chat_completion(messages=messages)
        assert "choices" in resp
        content = resp["choices"][0]["message"]["content"]
        assert len(content) > 0
        parsed = json.loads(content)
        assert parsed["category"] == "tamilnadu"

    def test_http_429_backoff_and_retry_after(self, virtual_clock):
        """HTTP 429 respects Retry-After header and applies backoff."""
        limiter = TokenBucketRateLimiter(
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep
        )
        client = NvidiaClient(rate_limiter=limiter)

        class Mock429Response:
            status_code = 429
            headers = {"Retry-After": "5"}
            text = "Too Many Requests"

        class Mock200Response:
            status_code = 200
            headers = {}
            text = json.dumps(MOCK_NIM_SUCCESS_RESPONSE)
            def json(self):
                return MOCK_NIM_SUCCESS_RESPONSE

        responses = [Mock429Response(), Mock200Response()]

        with mock.patch("requests.post", side_effect=responses):
            result = client.create_chat_completion(messages=[{"role": "user", "content": "test"}])
            assert result == MOCK_NIM_SUCCESS_RESPONSE
            assert 5.0 in virtual_clock.sleep_history

    def test_http_429_max_retries_exceeded_raises(self, virtual_clock):
        """HTTP 429 exceeding max_retries raises NvidiaRateLimitExceeded."""
        limiter = TokenBucketRateLimiter(
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep
        )
        client = NvidiaClient(rate_limiter=limiter)

        class Mock429Response:
            status_code = 429
            headers = {"Retry-After": "1"}
            text = "Too Many Requests"

        with mock.patch("requests.post", return_value=Mock429Response()):
            with pytest.raises(NvidiaRateLimitExceeded):
                client.create_chat_completion(
                    messages=[{"role": "user", "content": "test"}],
                    max_retries=2
                )

    def test_http_404_model_not_found_failover(self):
        """HTTP 404 triggers immediate fallback to secondary model."""
        client = NvidiaClient()

        called_models = []

        def mock_post(url, headers, json, timeout):
            called_models.append(json["model"])
            if json["model"] == "nvidia/nemotron-3.5-bolt-e4b":
                resp = mock.MagicMock()
                resp.status_code = 404
                resp.text = "Model not found"
                return resp
            # Fallback model succeeds
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.json.return_value = MOCK_NIM_SUCCESS_RESPONSE
            return resp

        with mock.patch("requests.post", side_effect=mock_post):
            result = client.create_chat_completion(messages=[{"role": "user", "content": "test"}])
            assert result == MOCK_NIM_SUCCESS_RESPONSE
            assert called_models[0] == "nvidia/nemotron-3.5-bolt-e4b"
            assert called_models[1] == "nvidia/nemotron-3.5-super-vl-120b-a12b"

    def test_http_503_service_unavailable_failover(self, virtual_clock):
        """HTTP 503 retries then falls back to secondary model."""
        limiter = TokenBucketRateLimiter(
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep
        )
        client = NvidiaClient(rate_limiter=limiter)

        called_models = []

        def mock_post(url, headers, json, timeout):
            called_models.append(json["model"])
            if json["model"] == "nvidia/nemotron-3.5-bolt-e4b":
                resp = mock.MagicMock()
                resp.status_code = 503
                resp.headers = {"Retry-After": "1"}
                resp.text = "Backend unavailable"
                return resp
            resp = mock.MagicMock()
            resp.status_code = 200
            resp.headers = {}
            resp.json.return_value = MOCK_NIM_SUCCESS_RESPONSE
            return resp

        with mock.patch("requests.post", side_effect=mock_post):
            result = client.create_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_retries=2
            )
            assert result == MOCK_NIM_SUCCESS_RESPONSE
            assert "nvidia/nemotron-3.5-super-vl-120b-a12b" in called_models

    def test_all_models_unavailable_raises_model_unavailable_error(self):
        """When primary and fallback models both fail, NvidiaModelUnavailableError is raised."""
        client = NvidiaClient()

        resp_404 = mock.MagicMock()
        resp_404.status_code = 404
        resp_404.text = "Not found"

        with mock.patch("requests.post", return_value=resp_404):
            with pytest.raises(NvidiaModelUnavailableError):
                client.create_chat_completion(messages=[{"role": "user", "content": "test"}])

    def test_network_error_retries_and_raises(self, virtual_clock):
        """Network connection exceptions are retried before raising NvidiaClientError."""
        limiter = TokenBucketRateLimiter(
            time_func=virtual_clock.monotonic,
            sleep_func=virtual_clock.sleep
        )
        client = NvidiaClient(rate_limiter=limiter)

        with mock.patch("requests.post", side_effect=requests.ConnectionError("Network down")):
            with pytest.raises(NvidiaClientError) as exc_info:
                client.create_chat_completion(
                    messages=[{"role": "user", "content": "test"}],
                    max_retries=2
                )
            assert "Network error" in str(exc_info.value)


# ============================================================================
# 3. TamilSynthesizer & ProcessedArticle Unit Tests
# ============================================================================

class TestTamilSynthesizer:
    """Verifies prompt generation, fence unwrapping, reasoning token purge, and ProcessedArticle schema."""

    def test_build_prompt_editorial_guidelines(self):
        """Prompt construction includes Arachudar chief editor persona and authentic Tamil instructions."""
        synthesizer = TamilSynthesizer()
        raw_article = SAMPLE_RAW_ARTICLES[0]
        messages = synthesizer.build_prompt(raw_article)

        assert len(messages) == 2
        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]

        assert "Arachudar" in system_msg
        assert "தலைமை செய்தி ஆசிரியர்" in system_msg
        assert is_valid_tamil_text(system_msg)
        assert raw_article.original_title in user_msg
        assert is_valid_tamil_text(user_msg)

    def test_parse_completion_clean_json(self):
        """Parses clean JSON successfully into dictionary."""
        synthesizer = TamilSynthesizer()
        raw = json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False)
        parsed = synthesizer.parse_completion(raw)
        assert parsed["category"] == "tamilnadu"
        assert parsed["subCategory"] == "chennai"
        assert is_valid_tamil_text(parsed["title"])

    def test_parse_completion_markdown_fence_unwrapping(self):
        """Unwraps ```json ... ``` and ``` ... ``` code fences."""
        synthesizer = TamilSynthesizer()
        raw = f"```json\n{json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False)}\n```"
        parsed = synthesizer.parse_completion(raw)
        assert parsed["category"] == "tamilnadu"
        assert parsed["isFlash"] is True

    def test_parse_completion_think_tag_purging(self):
        """Purges <think>...</think> reasoning blocks cleanly."""
        synthesizer = TamilSynthesizer()
        raw = (
            "<think>\n"
            "Generating Chennai metro news article.\n"
            "Editorial tone: objective, high standard Tamil.\n"
            "</think>\n"
            f"{json.dumps(SAMPLE_TAMIL_AI_CONTENT, ensure_ascii=False)}"
        )
        parsed = synthesizer.parse_completion(raw)
        assert parsed["category"] == "tamilnadu"
        assert "<think>" not in parsed["title"]
        assert "<think>" not in parsed["body"]

    def test_parse_completion_truncated_json_raises_decode_error(self):
        """Truncated JSON raises json.JSONDecodeError."""
        synthesizer = TamilSynthesizer()
        truncated = '{"category": "tamilnadu", "title": "மெட்ரோ ரயில் வேக'
        with pytest.raises(json.JSONDecodeError):
            synthesizer.parse_completion(truncated)

    def test_parse_completion_missing_required_keys_raises_value_error(self):
        """Missing required fields (e.g. body) raises ValueError."""
        synthesizer = TamilSynthesizer()
        incomplete = json.dumps({
            "category": "tamilnadu",
            "title": "சென்னையில் மெட்ரோ ரயில் பணிகள் தீவிரம்"
        })
        with pytest.raises(ValueError) as exc_info:
            synthesizer.parse_completion(incomplete)
        assert "Missing required schema field" in str(exc_info.value)

    def test_parse_completion_mojibake_rejection(self):
        """Synthesized content containing mojibake raises ValueError."""
        synthesizer = TamilSynthesizer()
        mojibake_content = dict(SAMPLE_TAMIL_AI_CONTENT)
        mojibake_content["title"] = "à®šà¯†à®©à¯\x8dà®©à¯ˆà®¯à®¿à®²à¯\x8d à®®à¯†à®fà¯\x8dà®°à¯‹"
        with pytest.raises(ValueError) as exc_info:
            synthesizer.parse_completion(json.dumps(mojibake_content, ensure_ascii=False))
        assert "Mojibake detected" in str(exc_info.value)

    def test_parse_completion_english_apology_rejection(self):
        """Non-Tamil English apology prose is rejected by authentic Tamil validator."""
        synthesizer = TamilSynthesizer()
        apology_json = json.dumps({
            "category": "tamilnadu",
            "title": "I apologize, but I am unable to generate the news article",
            "summary": "English apology summary text.",
            "body": "English apology body text."
        })
        with pytest.raises(ValueError) as exc_info:
            synthesizer.parse_completion(apology_json)
        assert "not authentic Tamil text" in str(exc_info.value)

    def test_parse_completion_mojibake_in_summary_triggers_rejection(self):
        """Mojibake in summary triggers ValueError in parse_completion and fallback in synthesize."""
        synthesizer = TamilSynthesizer()
        payload = dict(SAMPLE_TAMIL_AI_CONTENT)
        payload["summary"] = "à®¤à®®à®¿à®´à¯ நாட்டின் செய்தி சுருக்கம்"
        with pytest.raises(ValueError) as exc_info:
            synthesizer.parse_completion(json.dumps(payload, ensure_ascii=False))
        assert "Mojibake detected" in str(exc_info.value)

        # In synthesize, rejection triggers fallback safely
        mock_client = mock.MagicMock(spec=NvidiaClient)
        mock_client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]
        }
        synth = TamilSynthesizer(nvidia_client=mock_client)
        raw_article = SAMPLE_RAW_ARTICLES[0]
        article = synth.synthesize(raw_article, article_id=101)
        assert article.title == raw_article.original_title
        assert article.summary == raw_article.original_summary

    def test_parse_completion_english_summary_triggers_rejection(self):
        """English-only summary triggers ValueError in parse_completion and fallback in synthesize."""
        synthesizer = TamilSynthesizer()
        payload = dict(SAMPLE_TAMIL_AI_CONTENT)
        payload["summary"] = "This is an entirely English summary without any Tamil characters."
        with pytest.raises(ValueError) as exc_info:
            synthesizer.parse_completion(json.dumps(payload, ensure_ascii=False))
        assert "Summary is not authentic Tamil text" in str(exc_info.value)

        # In synthesize, non-Tamil summary triggers fallback safely
        mock_client = mock.MagicMock(spec=NvidiaClient)
        mock_client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]
        }
        synth = TamilSynthesizer(nvidia_client=mock_client)
        raw_article = SAMPLE_RAW_ARTICLES[0]
        article = synth.synthesize(raw_article, article_id=102)
        assert article.title == raw_article.original_title
        assert article.summary == raw_article.original_summary

    def test_detect_mojibake_boundary_patterns(self):
        """Mojibake at string boundaries and preceding spaces is detected."""
        assert detect_mojibake("செய்தி à®") is True
        assert detect_mojibake("செய்தி à¯") is True
        assert detect_mojibake("செய்தி à® ") is True
        assert detect_mojibake("செய்தி à¯ ") is True
        assert detect_mojibake("à®") is True
        assert detect_mojibake("à¯") is True
        assert detect_mojibake("முழுமையான தமிழ் உரை") is False

    def test_synthesize_is_flash_boolean_coercion(self):
        """isFlash safely coerces string booleans ('false' -> False, 'true' -> True)."""
        raw_article = SAMPLE_RAW_ARTICLES[0]

        # Case 1: isFlash is string 'false'
        payload_false = dict(SAMPLE_TAMIL_AI_CONTENT)
        payload_false["isFlash"] = "false"
        mock_client = mock.MagicMock(spec=NvidiaClient)
        mock_client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": json.dumps(payload_false, ensure_ascii=False)}}]
        }
        synth = TamilSynthesizer(nvidia_client=mock_client)
        article_false = synth.synthesize(raw_article, article_id=103)
        assert article_false.is_flash is False

        # Case 2: isFlash is string 'true'
        payload_true = dict(SAMPLE_TAMIL_AI_CONTENT)
        payload_true["isFlash"] = "true"
        mock_client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": json.dumps(payload_true, ensure_ascii=False)}}]
        }
        article_true = synth.synthesize(raw_article, article_id=104)
        assert article_true.is_flash is True

        # Case 3: isFlash is native False
        payload_native_false = dict(SAMPLE_TAMIL_AI_CONTENT)
        payload_native_false["isFlash"] = False
        mock_client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": json.dumps(payload_native_false, ensure_ascii=False)}}]
        }
        article_native_false = synth.synthesize(raw_article, article_id=105)
        assert article_native_false.is_flash is False

    def test_synthesize_end_to_end(self):
        """Synthesizes RawArticle into ProcessedArticle with real Tamil headline and body."""
        client = NvidiaClient()
        synthesizer = TamilSynthesizer(nvidia_client=client)
        raw_article = SAMPLE_RAW_ARTICLES[0]

        article = synthesizer.synthesize(raw_article, article_id=42)
        assert isinstance(article, ProcessedArticle)
        assert article.id == 42
        assert article.category == "tamilnadu"
        assert_clean_tamil_headline(article.title)
        assert_clean_tamil_body(article.body)
        assert article.image == raw_article.image_url
        assert article.source_url == raw_article.source_url
        assert article.source_name == raw_article.source_name
        assert 5000 <= article.views <= 15000
        assert "நிமிடம்" in article.read_time
        assert "முன்" in article.time_ago

    def test_synthesize_graceful_fallback_on_corrupted_response(self):
        """Synthesizer recovers safely using raw article metadata if LLM response is corrupt."""
        client = mock.MagicMock(spec=NvidiaClient)
        # LLM returns malformed content
        client.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "INVALID_CORRUPTED_RESPONSE_NON_JSON"}}]
        }
        synthesizer = TamilSynthesizer(nvidia_client=client)
        raw_article = SAMPLE_RAW_ARTICLES[0]

        article = synthesizer.synthesize(raw_article, article_id=99)
        assert isinstance(article, ProcessedArticle)
        assert article.id == 99
        assert article.title == raw_article.original_title
        assert is_valid_tamil_text(article.title)
        assert is_valid_tamil_text(article.body)

    def test_processed_article_to_template_dict(self):
        """to_template_dict produces camelCase dictionary matching NEWS_DATABASE schema."""
        article = ProcessedArticle(
            id=1,
            category="tamilnadu",
            sub_category="chennai",
            title="சென்னையில் புதிய மெட்ரோ திட்டம்",
            summary="மெட்ரோ பணிகள் துரிதப்படுத்தப்பட்டுள்ளன.",
            body="முழுமையான செய்தி விவரங்கள்.",
            image="https://example.com/metro.jpg",
            author="அறச்சுடர் சிறப்பு நிருபர்",
            date="10 நவம்பர் 2026",
            time_ago="15 நிமிடங்கள் முன்",
            read_time="3 நிமிடம்",
            views=12500,
            is_flash=True,
            tags=["சென்னை", "மெட்ரோ"],
            source_url="https://dailythanthi.com/metro",
            source_name="தினத்தந்தி"
        )
        data = article.to_template_dict()
        assert data["id"] == 1
        assert data["category"] == "tamilnadu"
        assert data["subCategory"] == "chennai"
        assert data["timeAgo"] == "15 நிமிடங்கள் முன்"
        assert data["readTime"] == "3 நிமிடம்"
        assert data["sourceUrl"] == "https://dailythanthi.com/metro"
        assert data["sourceName"] == "தினத்தந்தி"
        assert data["isFlash"] is True

    def test_tamil_formatting_helpers(self):
        """Tests format_tamil_date, format_time_ago, and calculate_read_time."""
        tamil_date = format_tamil_date("2026-11-10T08:30:00Z")
        assert "நவம்பர்" in tamil_date
        assert "2026" in tamil_date

        tamil_time = format_time_ago("2026-11-10T08:30:00Z")
        assert ("முன்" in tamil_time) or ("சற்று" in tamil_time)

        read_time = calculate_read_time("சொல் " * 300)
        assert "2 நிமிடம்" in read_time
