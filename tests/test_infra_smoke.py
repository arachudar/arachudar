"""
tests/test_infra_smoke.py - Test Infrastructure & Fixture Framework Smoke Verification.
Validates that conftest fixtures, hermetic interceptors, template immutability guards,
Tamil Unicode validators, HTML inspectors, and sample payloads operate genuinely and cleanly.
"""

import xml.etree.ElementTree as ET
import pytest
import requests

from tests.conftest import (
    CANONICAL_HTML,
    CANONICAL_THEME_XML,
    MINIMAL_HTML_TEMPLATE_CONTENT
)
from tests.helpers.network_guard import HermeticNetworkViolation
from tests.helpers.virtual_clock import VirtualClock, verify_rate_limit_timings
from tests.helpers.unicode_validator import (
    is_valid_tamil_text,
    assert_clean_tamil_headline,
    assert_clean_tamil_body,
    detect_mojibake,
    TAMIL_CODEPOINT_PATTERN
)
from tests.helpers.html_inspector import (
    extract_dom_slot_ids,
    extract_news_database_ids,
    has_epaper_pages_content,
    verify_template_integrity
)
from tests.fixtures.sample_images import (
    DUMMY_JPEG_BYTES,
    VALID_EDITORIAL_IMAGE_URLS,
    VALID_IMAGE_URLS,
    NEGATIVE_IMAGE_URLS
)
from tests.fixtures.sample_feeds import (
    SAMPLE_FEEDS,
    DAILY_THANTHI_RSS,
    DINAMALAR_SITEMAP,
    ZEE_TAMIL_YOUTUBE_ATOM,
    MALFORMED_UNCLOSED_XML,
    MALFORMED_NO_ITEMS
)
from tests.fixtures.sample_nim_json import (
    SAMPLE_TAMIL_AI_CONTENT,
    MOCK_NIM_SUCCESS_RESPONSE,
    MOCK_NIM_MARKDOWN_WRAPPED_RESPONSE,
    MOCK_NIM_TRUNCATED_RESPONSE,
    MOCK_NIM_REASONING_LEAK_RESPONSE,
    MOCK_NIM_429_PAYLOAD,
    MOCK_NIM_503_PAYLOAD
)
from tests.fixtures.sample_blogger_json import (
    MOCK_BLOGGER_OAUTH_SUCCESS,
    MOCK_BLOGGER_OAUTH_INVALID_GRANT,
    MOCK_BLOGGER_POST_SUCCESS,
    MOCK_BLOGGER_POST_FORBIDDEN,
    MOCK_BLOGGER_POST_NOT_FOUND,
    build_blogger_post_payload
)
from tests.fixtures.sample_articles import (
    RawArticle,
    ProcessedArticle,
    SAMPLE_RAW_ARTICLES,
    SAMPLE_PROCESSED_ARTICLES,
    SAMPLE_EPAPER_PAGES_CONTENT
)


# ============================================================================
# 1. Canonical Template & Configuration Verification
# ============================================================================

@pytest.mark.tier1
def test_canonical_template_exists_and_is_unmodified():
    """Verifies that the master production HTML template exists and has authentic size."""
    assert CANONICAL_HTML.exists(), f"Production template not found at {CANONICAL_HTML}"
    assert CANONICAL_HTML.stat().st_size > 500_000, "Production template appears incomplete"


@pytest.mark.tier1
def test_clean_html_template_fixture(clean_html_template):
    """Verifies that clean_html_template provides an isolated mutable copy in tmp_path."""
    assert clean_html_template.exists()
    assert clean_html_template != CANONICAL_HTML
    # Mutate the copy and verify canonical is not affected
    original_size = CANONICAL_HTML.stat().st_size
    clean_html_template.write_text("<!-- mutated test copy -->", encoding="utf-8")
    assert clean_html_template.read_text(encoding="utf-8") == "<!-- mutated test copy -->"
    assert CANONICAL_HTML.stat().st_size == original_size


@pytest.mark.tier1
def test_minimal_html_template_fixture(minimal_html_template):
    """Verifies that minimal_html_template provides a rapid, structurally complete template."""
    assert minimal_html_template.exists()
    content = minimal_html_template.read_text(encoding="utf-8")
    verify_template_integrity(content, min_static_cards=1, require_epaper=True)


# ============================================================================
# 2. Hermetic Network Guard Interception Verification
# ============================================================================

@pytest.mark.hermetic
def test_hermetic_guard_blocks_unmocked_domain():
    """Guarantees that unmocked external network calls raise HermeticNetworkViolation."""
    with pytest.raises(HermeticNetworkViolation) as exc_info:
        requests.get("https://unmocked-external-unknown-service.com/api/data")
    assert "Hermetic Network Guard Blocked Unmocked Network Call" in str(exc_info.value)


@pytest.mark.hermetic
def test_hermetic_guard_intercepts_image_request():
    """Verifies that requests for valid editorial CDN images return 200 OK and JPEG bytes."""
    url = "https://media.assettype.com/dailythanthi/2026-11-10/news_photo.jpg?w=1200"
    resp = requests.get(url)
    assert resp.status_code == 200
    assert resp.content == DUMMY_JPEG_BYTES
    assert resp.headers.get("Content-Type") == "image/jpeg"


@pytest.mark.hermetic
def test_hermetic_guard_rejects_negative_image_request():
    """Verifies that requests for blocklisted negative logos/icons return 404 Not Found."""
    url = "https://www.dailythanthi.com/assets/images/logo.png"
    resp = requests.get(url)
    assert resp.status_code == 404


@pytest.mark.hermetic
def test_hermetic_guard_intercepts_nvidia_completion():
    """Verifies that calls to NVIDIA NIM completions endpoint return valid Tamil AI payload."""
    resp = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        json={"model": "nvidia/nemotron-3.5-bolt-e4b", "messages": []}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data
    assert data["choices"][0]["message"]["role"] == "assistant"
    # Content must parse as authentic Tamil article JSON
    content_obj = json_loads_safe(data["choices"][0]["message"]["content"])
    assert content_obj["category"] == "tamilnadu"
    assert is_valid_tamil_text(content_obj["title"])


@pytest.mark.hermetic
def test_hermetic_guard_intercepts_oauth_and_blogger():
    """Verifies that Google OAuth2 and Blogger v3 endpoints are hermetically intercepted."""
    oauth_resp = requests.post("https://oauth2.googleapis.com/token", data={"grant_type": "refresh_token"})
    assert oauth_resp.status_code == 200
    assert "access_token" in oauth_resp.json()

    blogger_resp = requests.post(
        "https://www.googleapis.com/blogger/v3/blogs/12345/posts",
        json={"title": "Test Post"}
    )
    assert blogger_resp.status_code == 200
    assert blogger_resp.json()["kind"] == "blogger#post"
    assert blogger_resp.json()["status"] == "LIVE"


@pytest.mark.hermetic
def test_hermetic_guard_intercepts_tamil_feeds():
    """Verifies that Tamil publication RSS/Atom endpoints return valid parseable XML."""
    resp_dt = requests.get("https://www.dailythanthi.com/stories.rss")
    assert resp_dt.status_code == 200
    root = ET.fromstring(resp_dt.text)
    assert root.tag == "rss"

    resp_dm = requests.get("https://www.dinamalar.com/sitemap_latest.xml")
    assert resp_dm.status_code == 200
    root_dm = ET.fromstring(resp_dm.text)
    assert "urlset" in root_dm.tag


# ============================================================================
# 3. Virtual Clock & Rate Limiting Helper Verification
# ============================================================================

@pytest.mark.tier1
def test_virtual_clock_pacing_simulation(virtual_clock):
    """Verifies that VirtualClock advances time and tracks sleep durations instantly."""
    start = virtual_clock.monotonic()
    assert start == 1000.0

    # Simulate token bucket delay
    virtual_clock.sleep(2.0)
    virtual_clock.sleep(2.0)
    assert virtual_clock.monotonic() == 1004.0
    assert len(virtual_clock.sleep_history) == 2
    assert virtual_clock.total_slept == 4.0

    # Verify helper passes
    verify_rate_limit_timings(virtual_clock.sleep_history, expected_delay=2.0, tolerance=0.1)


# ============================================================================
# 4. Unicode & Content Integrity Validator Verification
# ============================================================================

@pytest.mark.tier1
def test_unicode_validator_authentic_tamil():
    """Verifies detection of authentic Tamil text."""
    tamil_headline = "சென்னையில் தொழில் முதலீடுகள் அதிகரிப்பு: 50,000 பேருக்கு வேலைவாய்ப்பு"
    assert is_valid_tamil_text(tamil_headline)
    assert_clean_tamil_headline(tamil_headline)


@pytest.mark.tier1
def test_unicode_validator_flags_non_tamil_and_leaks():
    """Verifies that non-Tamil text and reasoning token leaks are rejected."""
    english_headline = "Breaking news: Major investments in Chennai tech sector"
    assert not is_valid_tamil_text(english_headline)

    leaked_headline = "<think>Here is the headline</think> சென்னையில் மெட்ரோ பணிகள்"
    with pytest.raises(AssertionError):
        assert_clean_tamil_headline(leaked_headline)


@pytest.mark.tier1
def test_unicode_validator_detects_mojibake():
    """Verifies detection of double UTF-8 decoding / mojibake artifacts."""
    mojibake_text = "à®šà¯†à®©à¯\x8dà®©à¯ˆà®¯à®¿à®²à¯\x8d à®®à¯†à®fà¯\x8dà®°à¯‹"
    assert detect_mojibake(mojibake_text)
    clean_text = "சென்னையில் மெட்ரோ ரயில் விரிவாக்கம்"
    assert not detect_mojibake(clean_text)


# ============================================================================
# 5. HTML Inspector Helper Verification
# ============================================================================

@pytest.mark.tier1
def test_html_inspector_validates_minimal_template():
    """Verifies that html_inspector correctly inspects static cards and NEWS_DATABASE."""
    verify_template_integrity(MINIMAL_HTML_TEMPLATE_CONTENT, min_static_cards=1, require_epaper=True)

    card_ids = extract_dom_slot_ids(MINIMAL_HTML_TEMPLATE_CONTENT)
    assert len(card_ids) >= 10
    assert 1 in card_ids
    assert 4 in card_ids
    assert 7 in card_ids

    db_ids = extract_news_database_ids(MINIMAL_HTML_TEMPLATE_CONTENT)
    assert len(db_ids) == 10
    assert set(card_ids).issubset(set(db_ids))
    assert has_epaper_pages_content(MINIMAL_HTML_TEMPLATE_CONTENT)


@pytest.mark.tier1
def test_html_inspector_detects_broken_card_references():
    """Verifies that html_inspector detects when a static card references a missing DB ID."""
    corrupted_html = MINIMAL_HTML_TEMPLATE_CONTENT.replace(
        'let NEWS_DATABASE = [',
        'let NEWS_DATABASE = [\n      // missing all items\n    ]; let DUMMY = ['
    )
    with pytest.raises(AssertionError) as exc_info:
        verify_template_integrity(corrupted_html)
    assert "NEWS_DATABASE" in str(exc_info.value)


# ============================================================================
# 6. Sample Datasets & Payloads Verification
# ============================================================================

@pytest.mark.tier1
def test_sample_feeds_are_valid_xml():
    """Verifies that all sample feeds in sample_feeds.py parse cleanly as XML/Atom."""
    assert len(SAMPLE_FEEDS) >= 10
    for source_key, xml_content in SAMPLE_FEEDS.items():
        root = ET.fromstring(xml_content)
        assert root is not None, f"Failed parsing XML for {source_key}"


@pytest.mark.tier1
def test_sample_images_fixtures():
    """Verifies that valid editorial image list and negative image list are non-empty and distinct."""
    assert len(VALID_IMAGE_URLS) >= 10
    assert len(NEGATIVE_IMAGE_URLS) >= 10
    # Valid URLs and negative URLs must have zero overlap
    overlap = set(VALID_IMAGE_URLS) & set(NEGATIVE_IMAGE_URLS)
    assert not overlap, f"Image test sets have unexpected overlap: {overlap}"


@pytest.mark.tier1
def test_sample_nim_json_payloads():
    """Verifies all NVIDIA NIM completion fixtures."""
    # 1. 200 OK
    assert MOCK_NIM_SUCCESS_RESPONSE["choices"][0]["finish_reason"] == "stop"
    # 2. Markdown fenced
    assert "```json" in MOCK_NIM_MARKDOWN_WRAPPED_RESPONSE["choices"][0]["message"]["content"]
    # 3. Truncated
    assert MOCK_NIM_TRUNCATED_RESPONSE["choices"][0]["finish_reason"] == "length"
    # 4. Reasoning leak
    assert "<think>" in MOCK_NIM_REASONING_LEAK_RESPONSE["choices"][0]["message"]["content"]
    # 5. 429 & 503
    assert MOCK_NIM_429_PAYLOAD["status_code"] == 429
    assert MOCK_NIM_503_PAYLOAD["status_code"] == 503


@pytest.mark.tier1
def test_sample_blogger_json_payloads():
    """Verifies Blogger OAuth2 and Post creation payloads."""
    assert MOCK_BLOGGER_OAUTH_SUCCESS["status_code"] == 200
    assert MOCK_BLOGGER_OAUTH_INVALID_GRANT["status_code"] == 400
    assert MOCK_BLOGGER_POST_SUCCESS["status_code"] == 200
    assert MOCK_BLOGGER_POST_FORBIDDEN["status_code"] == 403
    assert MOCK_BLOGGER_POST_NOT_FOUND["status_code"] == 404

    payload = build_blogger_post_payload("Title", "<p>Content</p>", ["தமிழகம்"])
    assert payload["title"] == "Title"
    assert payload["labels"] == ["தமிழகம்"]


@pytest.mark.tier1
def test_sample_articles_contracts(sample_raw_articles, sample_processed_articles):
    """Verifies that RawArticle and ProcessedArticle instances adhere to project contracts."""
    assert len(sample_raw_articles) >= 5
    for raw in sample_raw_articles:
        assert isinstance(raw, RawArticle)
        assert raw.source_id
        assert raw.source_url.startswith("https://")
        assert raw.image_url.startswith("https://")
        assert is_valid_tamil_text(raw.original_title)

    assert len(sample_processed_articles) >= 5
    for proc in sample_processed_articles:
        assert isinstance(proc, ProcessedArticle)
        assert proc.id > 0
        assert proc.category in [
            'tamilnadu', 'national', 'world', 'politics',
            'business', 'cinema', 'sports', 'tech', 'spiritual'
        ]
        assert is_valid_tamil_text(proc.title)
        assert is_valid_tamil_text(proc.summary)
        # Verify dictionary conversion
        t_dict = proc.to_template_dict()
        assert t_dict["id"] == proc.id
        assert t_dict["title"] == proc.title
        assert t_dict["image"] == proc.image


# Helper
def json_loads_safe(text: str):
    import json
    return json.loads(text)
