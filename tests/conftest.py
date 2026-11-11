"""
tests/conftest.py - Master Fixture Framework for Arachudar Tamil News Test Suite.
Provides 100% hermetic network isolation, production template protection,
deterministic virtual clock rate limiting, and authentic Tamil news data fixtures.
"""

import os
import re
import json
import time
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
import unittest.mock as mock
import pytest
import requests

from tests.helpers.network_guard import (
    HermeticNetworkViolation,
    MockResponse,
    MockUrllibResponse
)
from tests.helpers.virtual_clock import VirtualClock
from tests.fixtures.sample_images import DUMMY_JPEG_BYTES
from tests.fixtures.sample_nim_json import MOCK_NIM_SUCCESS_RESPONSE
from tests.fixtures.sample_blogger_json import (
    MOCK_BLOGGER_OAUTH_SUCCESS,
    MOCK_BLOGGER_POST_SUCCESS
)
from tests.fixtures.sample_feeds import (
    SAMPLE_FEEDS,
    DAILY_THANTHI_RSS,
    DINAMALAR_SITEMAP,
    ZEE_TAMIL_YOUTUBE_ATOM
)
from tests.fixtures.sample_articles import (
    RawArticle,
    ProcessedArticle,
    SAMPLE_RAW_ARTICLES,
    SAMPLE_PROCESSED_ARTICLES,
    SAMPLE_EPAPER_PAGES_CONTENT
)

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_HTML = PROJECT_ROOT / "tamil-news-blogger.html"
CANONICAL_THEME_XML = PROJECT_ROOT / "blogger-theme.xml"

MINIMAL_HTML_TEMPLATE_CONTENT = """<!DOCTYPE html>
<html lang="ta">
<head>
  <meta charset="UTF-8">
  <title>அறச்சுடர் - Arachudar Tamil News (Minimal Hermetic Fixture)</title>
</head>
<body>
  <header class="top-bar">
    <span class="top-bar-item" id="currentDateDisplay">திங்கள், 10 நவம்பர் 2026</span>
  </header>

  <section class="hero-news-showcase" id="heroNewsShowcaseSection">
    <div class="container">
      <div class="hero-layout-grid">
        <article class="lead-news-card" onclick="navigateToArticle(1)">
          <div class="lead-news-image-wrap">
            <img src="https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200" alt="முதன்மை செய்தி">
          </div>
          <div class="lead-content-overlay">
            <span class="category-tag-badge">தலைமைச் செய்தி</span>
            <h1 class="lead-headline">தமிழ்நாட்டில் புதிய தொழில் முதலீடுகள்</h1>
            <p class="lead-summary">முதலீட்டாளர்கள் மாநாட்டில் முக்கிய ஒப்பந்தங்கள் கையெழுத்தாகின.</p>
            <div class="meta-byline-strip">
              <span>அறச்சுடர் சிறப்பு நிருபர்</span> • <span>25 நிமிடங்கள் முன்</span> • <span>3 நிமிடம்</span>
            </div>
          </div>
        </article>

        <div class="hero-side-stack">
          <article class="side-card-item" onclick="navigateToArticle(4)">
            <div class="side-card-thumb"><img src="https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200" alt="வணிகம்"></div>
            <div class="side-card-body">
              <span class="category-tag-badge">வணிகம்</span>
              <h2 class="side-card-title">ரிசர்வ் வங்கியின் முக்கிய கொள்கை முடிவு</h2>
              <div class="side-card-meta">45 நிமிடங்கள் முன் • 2 நிமிடம்</div>
            </div>
          </article>
          <article class="side-card-item" onclick="navigateToArticle(7)">
            <div class="side-card-thumb"><img src="https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg" alt="விளையாட்டு"></div>
            <div class="side-card-body">
              <span class="category-tag-badge">விளையாட்டு</span>
              <h2 class="side-card-title">மெல்போர்ன் டெஸ்டில் விராட் கோலி அபார சதம்</h2>
              <div class="side-card-meta">1 மணி நேரம் முன் • 3 நிமிடம்</div>
            </div>
          </article>
          <article class="side-card-item" onclick="navigateToArticle(6)">
            <div class="side-card-thumb"><img src="https://images.news18.com/tamil/uploads/2026/11/sonia-gandhi-2026-11-bfbe3a4e73a1c1c1200255934925ba2d-1200x800.jpg" alt="சினிமா"></div>
            <div class="side-card-body">
              <span class="category-tag-badge">சினிமா</span>
              <h2 class="side-card-title">சரித்திர திரைப்படத்தின் டீசர் சாதனை</h2>
              <div class="side-card-meta">2 மணி நேரம் முன் • 2 நிமிடம்</div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>

  <section class="speed-and-hot-topics-section" id="speedHotTopicsSection">
    <div class="container">
      <div class="speed-hot-grid-3col">
        <div class="speed-col-card">
          <ul class="fast-news-stream-list">
            <li class="fast-news-item" onclick="navigateToArticle(2)"><div class="fast-news-title">விரைவு 1</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(8)"><div class="fast-news-title">விரைவு 2</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(4)"><div class="fast-news-title">விரைவு 3</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(5)"><div class="fast-news-title">விரைவு 4</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(10)"><div class="fast-news-title">விரைவு 5</div></li>
          </ul>
        </div>
        <div class="speed-col-card">
          <div class="hot-topic-feature-card" onclick="navigateToArticle(10)"><h4 class="hot-topic-title">டிரெண்டிங் 1</h4></div>
          <div class="hot-topic-feature-card" onclick="navigateToArticle(4)"><h4 class="hot-topic-title">டிரெண்டிங் 2</h4></div>
        </div>
        <div class="speed-col-card">
          <ul class="fast-news-stream-list">
            <li class="fast-news-item" onclick="navigateToArticle(7)"><div class="fast-news-title">தலைப்பு 1</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(6)"><div class="fast-news-title">தலைப்பு 2</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(3)"><div class="fast-news-title">தலைப்பு 3</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(9)"><div class="fast-news-title">தலைப்பு 4</div></li>
            <li class="fast-news-item" onclick="navigateToArticle(1)"><div class="fast-news-title">தலைப்பு 5</div></li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <main id="mainDynamicView"></main>

  <script>
    let NEWS_DATABASE = [
      { id: 1, title: 'முதன்மை செய்தி', category: 'tamilnadu', subCategory: 'chennai' },
      { id: 4, title: 'வணிக செய்தி', category: 'business', subCategory: 'market' },
      { id: 7, title: 'விளையாட்டு செய்தி', category: 'sports', subCategory: 'cricket' },
      { id: 6, title: 'சினிமா செய்தி', category: 'cinema', subCategory: 'news' },
      { id: 2, title: 'சென்னை மெட்ரோ செய்தி', category: 'tamilnadu', subCategory: 'chennai' },
      { id: 8, title: 'அரசியல் செய்தி', category: 'politics', subCategory: 'national' },
      { id: 5, title: 'தொழில்நுட்ப செய்தி', category: 'tech', subCategory: 'ai' },
      { id: 10, title: 'உலக செய்தி', category: 'world', subCategory: 'climate' },
      { id: 3, title: 'ஆன்மிக செய்தி', category: 'spiritual', subCategory: 'temple' },
      { id: 9, title: 'தேசிய செய்தி', category: 'national', subCategory: 'general' }
    ];

    const EPAPER_PAGES_CONTENT = {
      1: {
        title: 'முதன்மைப் பக்கம்',
        leadHeadline: 'தமிழ்நாட்டில் புதிய தொழில் முதலீடுகள்',
        leadSubhead: '1 லட்சம் பேருக்கு வேலைவாய்ப்பு',
        leadByline: 'நிருபர் • 10 நவம்பர் 2026',
        leadPhoto: 'https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200',
        leadCaption: 'விளக்க உரை',
        leadBody: 'விவரமான செய்தி...',
        sideHeadline: 'ரிசர்வ் வங்கி நிதிக் கொள்கை',
        sideSummary: 'வட்டி குறைய வாய்ப்பு',
        metroHeadline: 'சென்னை மெட்ரோ பணிகள்',
        metroSummary: 'சோதனை ஓட்டம் வெற்றி',
        waterHeadline: 'வானிலை தகவல்',
        waterSummary: 'கனமழை எச்சரிக்கை',
        editorialHeadline: 'தலையங்கம்',
        editorialSnippet: 'முதலீடுகள் பரவலாக்கப்பட வேண்டும்'
      }
    };

    function navigateToArticle(id) {
      return NEWS_DATABASE.find(item => item.id === id);
    }
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Pytest CLI Options & Markers
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    """Registers the --run-live CLI option for optional live network tests."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Execute tests that require real external network connectivity."
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skips tests marked with @pytest.mark.live_network unless --run-live is supplied."""
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="Pass --run-live to execute real network tests")
        for item in items:
            if "live_network" in item.keywords:
                item.add_marker(skip_live)


# ---------------------------------------------------------------------------
# Session Guards & Environment Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def guard_canonical_template():
    """
    Session Guard: Guarantees that the canonical production template
    tamil-news-blogger.html is never modified or corrupted during test execution.
    Computes SHA-256 before the test run and verifies invariance at teardown.
    """
    assert CANONICAL_HTML.exists(), f"Master canonical template not found at {CANONICAL_HTML}"
    initial_hash = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()
    yield
    final_hash = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()
    assert initial_hash == final_hash, (
        f"CRITICAL INTEGRITY FAILURE: Canonical template {CANONICAL_HTML} was mutated during tests!\n"
        f"Initial SHA-256: {initial_hash}\n"
        f"Final SHA-256:   {final_hash}\n"
        f"All tests modifying HTML must write to clean_html_template or minimal_html_template in tmp_path."
    )


@pytest.fixture(scope="session", autouse=True)
def safe_environment_defaults():
    """
    Session Fixture: Injects safe, deterministic mock environment variables.
    Prevents leaking live production credentials or initiating live API updates.
    """
    overrides = {
        "NVIDIA_API_KEY": "test-nvapi-mock-token-000000000000",
        "BLOGGER_BLOG_ID": "test-mock-blog-id-12345",
        "BLOGGER_CLIENT_ID": "test-mock-client-id.apps.googleusercontent.com",
        "BLOGGER_CLIENT_SECRET": "test-mock-client-secret",
        "BLOGGER_REFRESH_TOKEN": "test-mock-refresh-token",
        "ENABLE_X": "false",
        "ENABLE_FACEBOOK": "false",
        "ENABLE_INSTAGRAM": "false",
        "ENABLE_YOUTUBE": "false",
        "DRY_RUN": "true",
    }
    with mock.patch.dict(os.environ, overrides):
        yield


# ---------------------------------------------------------------------------
# Template Lifecycle Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def clean_html_template(tmp_path: Path) -> Path:
    """
    Creates an isolated copy of the 877 KB production tamil-news-blogger.html
    in a temporary directory. Tests can freely mutate, parse, and overwrite this clone.
    """
    target = tmp_path / "tamil-news-blogger.html"
    shutil.copy2(CANONICAL_HTML, target)
    return target


@pytest.fixture
def minimal_html_template(tmp_path: Path) -> Path:
    """
    Creates a lightweight, syntactically complete HTML template containing only
    the required structural DOM IDs, classes, and JS anchors for rapid unit testing.
    """
    target = tmp_path / "minimal-news.html"
    target.write_text(MINIMAL_HTML_TEMPLATE_CONTENT, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Hermetic Network Guard & Mock Dispatcher
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def hermetic_network_guard(request):
    """
    Autouse Fixture: Intercepts all requests.Session.request, requests.request,
    and urllib.request.urlopen calls across the test run.
    Routes known domains to authentic canned responses and raises HermeticNetworkViolation
    for unhandled outbound network traffic.
    """
    if request.config.getoption("--run-live") or "live_network" in request.keywords:
        yield
        return

    def mock_session_request(session, method, url, *args, **kwargs):
        url_str = str(url)
        url_lower = url_str.lower()
        method_upper = method.upper()

        # 1. Image URL simulation (Assets, Gumlet, CDNs, extensions)
        is_image_url = (
            any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp"])
            or "=s0-w" in url_lower
            or "?w=" in url_lower
            or "/1024/" in url_lower
            or "/hqdefault.jpg" in url_lower
        )
        if is_image_url:
            # Check negative blocklist patterns
            negative_keywords = [
                "logo", "icon", "placeholder", "default_banner",
                "tracking_pixel", "spacer.gif", "avatar", "doubleclick"
            ]
            if any(bad in url_lower for bad in negative_keywords):
                return MockResponse(404, text="Not found", url=url_str)
            return MockResponse(
                status_code=200,
                content=DUMMY_JPEG_BYTES,
                headers={"Content-Type": "image/jpeg", "Content-Length": str(len(DUMMY_JPEG_BYTES))},
                url=url_str
            )

        # 2. NVIDIA NIM API Chat Completions
        if "integrate.api.nvidia.com" in url_lower:
            return MockResponse(200, json_data=MOCK_NIM_SUCCESS_RESPONSE, url=url_str)

        # 3. Google OAuth 2.0 Token Refresh
        if "oauth2.googleapis.com" in url_lower:
            return MockResponse(200, json_data=MOCK_BLOGGER_OAUTH_SUCCESS["body"], url=url_str)

        # 4. Google Blogger API v3 Posts
        if "googleapis.com/blogger/v3" in url_lower:
            return MockResponse(200, json_data=MOCK_BLOGGER_POST_SUCCESS["body"], url=url_str)

        # 5. Tamil News XML Feeds (RSS 2.0, Atom, Google News Sitemap)
        if "dinamalar" in url_lower and "sitemap" in url_lower:
            return MockResponse(200, text=DINAMALAR_SITEMAP, headers={"Content-Type": "application/xml"}, url=url_str)
        if "youtube.com/feeds" in url_lower:
            return MockResponse(200, text=ZEE_TAMIL_YOUTUBE_ATOM, headers={"Content-Type": "application/atom+xml"}, url=url_str)

        # Check matched publication feeds
        for source_key, sample_xml in SAMPLE_FEEDS.items():
            if source_key in url_lower or source_key.replace("_", "") in url_lower:
                return MockResponse(200, text=sample_xml, headers={"Content-Type": "application/xml"}, url=url_str)

        # General Tamil publication domains
        known_news_domains = [
            "dailythanthi", "dinamani", "hindutamil", "maalaimalar",
            "thinaboomi", "vikatan", "samayam", "oneindia",
            "news18", "asianet", "google.com/rss", "bbci.co.uk", "w3newspapers"
        ]
        if any(dom in url_lower for dom in known_news_domains):
            return MockResponse(200, text=DAILY_THANTHI_RSS, headers={"Content-Type": "application/xml"}, url=url_str)

        # Fallback: Raise HermeticNetworkViolation for unmocked outbound network call
        raise HermeticNetworkViolation(
            f"Hermetic Network Guard Blocked Unmocked Network Call: {method_upper} {url_str}. "
            f"Add a mock response handler in conftest.py or run with --run-live."
        )

    def mock_urlopen_handler(req, *args, **kwargs):
        url_str = req.full_url if hasattr(req, "full_url") else str(req)
        url_lower = url_str.lower()

        if "integrate.api.nvidia.com" in url_lower:
            return MockUrllibResponse(json.dumps(MOCK_NIM_SUCCESS_RESPONSE).encode("utf-8"), status=200)
        if any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp"]) or "?w=" in url_lower:
            return MockUrllibResponse(DUMMY_JPEG_BYTES, status=200, headers={"Content-Type": "image/jpeg"})
        if any(dom in url_lower for dom in ["dailythanthi", "dinamalar", "dinamani", "hindutamil", "vikatan", "youtube", "google"]):
            return MockUrllibResponse(DAILY_THANTHI_RSS.encode("utf-8"), status=200, headers={"Content-Type": "application/xml"})

        raise HermeticNetworkViolation(
            f"Hermetic Network Guard Blocked Unmocked urllib Call: GET {url_str}."
        )

    with mock.patch.object(requests.Session, "request", side_effect=mock_session_request, autospec=True), \
         mock.patch("requests.request", side_effect=lambda method, url, **kw: mock_session_request(None, method, url, **kw)), \
         mock.patch("urllib.request.urlopen", side_effect=mock_urlopen_handler):
        yield


# ---------------------------------------------------------------------------
# Virtual Clock Fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def virtual_clock():
    """
    Provides a controllable VirtualClock patching time.monotonic and time.sleep.
    Enables deterministic rate-limiting verification without wall-clock sleep.
    """
    clock = VirtualClock(start_time=1000.0)
    with mock.patch("time.monotonic", side_effect=clock.monotonic), \
         mock.patch("time.sleep", side_effect=clock.sleep):
        yield clock


# ---------------------------------------------------------------------------
# Data Model Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def dummy_jpeg_bytes() -> bytes:
    """Returns the minimal 1x1 valid JPEG byte stream."""
    return DUMMY_JPEG_BYTES


@pytest.fixture
def sample_raw_articles() -> List[RawArticle]:
    """Collection of 5 validated RawArticle instances."""
    return SAMPLE_RAW_ARTICLES


@pytest.fixture
def sample_processed_articles() -> List[ProcessedArticle]:
    """Collection of validated ProcessedArticle instances matching homepage slot IDs."""
    return SAMPLE_PROCESSED_ARTICLES


@pytest.fixture
def sample_raw_article_dict() -> Dict[str, Any]:
    """Single RawArticle represented as a dictionary."""
    return {
        "source_id": "daily_thanthi",
        "source_name": "தினத்தந்தி",
        "source_url": "https://www.dailythanthi.com/news/state/investments-chennai-101",
        "original_title": "சென்னையில் தொழில் முதலீடுகள் அதிகரிப்பு",
        "original_summary": "உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் பல புதிய ஒப்பந்தங்கள்.",
        "image_url": "https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200",
        "published_date": "2026-11-10T08:30:00Z",
        "category_hint": "tamilnadu"
    }


@pytest.fixture
def sample_processed_article_dict() -> Dict[str, Any]:
    """Single ProcessedArticle represented as a template-conforming dictionary."""
    return SAMPLE_PROCESSED_ARTICLES[0].to_template_dict()


@pytest.fixture
def sample_epaper_pages() -> Dict[int, Dict[str, str]]:
    """Broadsheet 4-page schema for EPAPER_PAGES_CONTENT."""
    return SAMPLE_EPAPER_PAGES_CONTENT
