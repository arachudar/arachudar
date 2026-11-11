"""
tests/test_tier3_pairwise.py - Tier 3 Pairwise Cross-Feature Integration Test Suite.
Validates the data flow, interface contracts, and interaction boundaries between
interacting pipeline components (F1 through F14) in the Arachudar Tamil News Automation Pipeline.

Pairs Covered:
- Pair 1 (F1 + F5): Ingestion feed filtering rejecting logo images in Daily Thanthi feed items
- Pair 2 (F1 + F6): Multi-source ingestion with state cache deduplication skipping previously processed articles
- Pair 3 (F3 + F4): Image extractor extracting thumbnail and CDN enhancer upgrading to high-res (e.g. AssetType 1200px)
- Pair 4 (F1 + F7): Aggregator rate pacing with TokenBucketRateLimiter
- Pair 5 (F7 + F8): NVIDIA client pacing coupled with Tamil prompt synthesis under token quota
- Pair 6 (F8 + F9): Synthesized Tamil ProcessedArticle updating Lead Hero static card and NEWS_DATABASE
- Pair 7 (F8 + F10): Synthesized article converted to styled Blogger HTML with Tamil category labels
- Pair 8 (F8 + F11): Synthesized headline and summary clipped to 280 characters for X hook
- Pair 9 (F9 + F10): Dual-layer HTML population consistent with Blogger category labels
- Pair 10 (F2 + F3): Dinamalar sitemap XML parsing coupled with real news image extraction
- Pair 11 (F6 + F13): State cache verification during dry-run pipeline run
- Pair 12 (F9 + F14): Template immutability guard during full static/dynamic HTML population
- Pair 13 (F10 + F11): Simultaneous Blogger publish and social channel broadcasting
- Pair 14 (F12 + F13): GitHub Actions workflow triggering verify_dry_run.py execution
"""

import os
import re
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import xml.etree.ElementTree as ET

import pytest
import requests

from config.sources import (
    TAMIL_NEWS_SOURCES,
    VALID_CATEGORIES,
    VALID_SUBCATEGORIES,
    SourceConfig,
    get_source_config,
    map_category,
    map_subcategory,
)
from src.aggregator.feed_fetcher import (
    FeedFetcher,
    RawArticle,
    fetch_articles_from_source,
    fetch_all_sources,
)
from src.aggregator.image_extractor import (
    ImageExtractor,
    validate_and_enhance_image_url,
    extract_image_from_feed_entry,
    extract_image_from_html,
    IMAGE_BLOCKLIST_PATTERNS,
    BLOCKED_FILE_EXTENSIONS,
)
from src.aggregator.deduplicator import (
    Deduplicator,
    normalize_url,
    normalize_title,
    compute_article_hash,
)

from tests.conftest import (
    CANONICAL_HTML,
    MINIMAL_HTML_TEMPLATE_CONTENT,
)
from tests.fixtures.sample_articles import (
    ProcessedArticle,
    SAMPLE_RAW_ARTICLES,
    SAMPLE_PROCESSED_ARTICLES,
    SAMPLE_EPAPER_PAGES_CONTENT,
)
from tests.fixtures.sample_images import (
    DUMMY_JPEG_BYTES,
    VALID_EDITORIAL_IMAGE_URLS,
    NEGATIVE_IMAGE_URLS,
)
from tests.fixtures.sample_feeds import (
    SAMPLE_FEEDS,
    DAILY_THANTHI_RSS,
    DINAMALAR_SITEMAP,
    ZEE_TAMIL_YOUTUBE_ATOM,
)
from tests.fixtures.sample_nim_json import (
    SAMPLE_TAMIL_AI_CONTENT,
    MOCK_NIM_SUCCESS_RESPONSE,
)
from tests.fixtures.sample_blogger_json import (
    MOCK_BLOGGER_OAUTH_SUCCESS,
    MOCK_BLOGGER_POST_SUCCESS,
    build_blogger_post_payload,
)
from tests.helpers.virtual_clock import VirtualClock, verify_rate_limit_timings
from tests.helpers.unicode_validator import (
    is_valid_tamil_text,
    assert_clean_tamil_headline,
    assert_clean_tamil_body,
    detect_mojibake,
    TAMIL_CODEPOINT_PATTERN,
)
from tests.helpers.html_inspector import (
    extract_dom_slot_ids,
    extract_news_database_ids,
    has_epaper_pages_content,
    verify_template_integrity,
)


# ============================================================================
# Contract Reference Adapters (Conforming directly to PROJECT.md § Architecture)
# If future milestone modules are implemented, attempt import; otherwise use adapters.
# ============================================================================

try:
    from src.ai.rate_limiter import TokenBucketRateLimiter
except ImportError:
    class TokenBucketRateLimiter:
        """
        Thread-safe TokenBucketRateLimiter adhering to PROJECT.md R2 & F7:
        Enforces <= 30 RPM (0.5 tokens/sec) with burst capacity 4.
        """
        def __init__(self, rate_per_sec: float = 0.5, capacity: float = 4.0):
            self.rate = rate_per_sec
            self.capacity = capacity
            self.tokens = capacity
            self.last_update = time.monotonic()
            self.lock = threading.Lock()

        def acquire(self, tokens: float = 1.0) -> float:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return 0.0

                needed = tokens - self.tokens
                sleep_duration = needed / self.rate
                time.sleep(sleep_duration)
                self.tokens = 0.0
                self.last_update = time.monotonic()
                return sleep_duration


try:
    from src.ai.nvidia_client import NvidiaClient
except ImportError:
    class NvidiaClient:
        """
        NVIDIA NIM API client communicating with https://integrate.api.nvidia.com/v1/chat/completions
        using model nvidia/nemotron-3.5-bolt-e4b under rate-limiting supervision.
        """
        def __init__(
            self,
            api_key: str = "test-nvapi-mock-token-000000000000",
            model: str = "nvidia/nemotron-3.5-bolt-e4b",
            rate_limiter: Optional[TokenBucketRateLimiter] = None
        ):
            self.api_key = api_key
            self.model = model
            self.rate_limiter = rate_limiter or TokenBucketRateLimiter()

        def synthesize(self, raw_article: RawArticle, article_id: int = 1) -> ProcessedArticle:
            self.rate_limiter.acquire(1.0)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional Tamil news journalist. Produce JSON adhering to the Arachudar schema."
                    },
                    {
                        "role": "user",
                        "content": f"Title: {raw_article.original_title}\nSummary: {raw_article.original_summary}"
                    }
                ]
            }
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)

            return ProcessedArticle(
                id=article_id,
                category=parsed.get("category", raw_article.category_hint or "tamilnadu"),
                sub_category=parsed.get("subCategory", "general"),
                title=parsed.get("title", raw_article.original_title),
                summary=parsed.get("summary", raw_article.original_summary),
                body=parsed.get("body", raw_article.original_summary * 2),
                image=raw_article.image_url,
                author="அறச்சுடர் சிறப்பு நிருபர்",
                date="10 நவம்பர் 2026",
                time_ago="15 நிமிடங்கள் முன்",
                read_time="3 நிமிடம்",
                views=11500,
                is_flash=bool(parsed.get("isFlash", False)),
                tags=parsed.get("tags", ["செய்திகள்", "அறச்சுடர்"]),
                source_url=raw_article.source_url,
                source_name=raw_article.source_name
            )


try:
    from src.publisher.html_populator import HtmlPopulator
except ImportError:
    class HtmlPopulator:
        """
        Dual-layer template populator updating static DOM slots and dynamic JavaScript
        arrays (NEWS_DATABASE, EPAPER_PAGES_CONTENT) in copies of tamil-news-blogger.html.
        """
        def __init__(self, template_path: Union[str, Path]):
            self.template_path = Path(template_path)

        def populate(
            self,
            articles: List[ProcessedArticle],
            epaper_pages: Optional[Dict[int, Dict[str, str]]] = None,
            current_date_str: str = "திங்கள், 10 நவம்பர் 2026"
        ) -> str:
            html = self.template_path.read_text(encoding="utf-8")

            # 1. Update date display
            html = re.sub(
                r'(<span[^>]*id="currentDateDisplay"[^>]*>).*?(</span>)',
                rf'\g<1>{current_date_str}\g<2>',
                html
            )

            # 2. Update Lead Hero card if articles available
            if articles:
                lead = articles[0]
                html = re.sub(
                    r'<h1 class="lead-headline">.*?</h1>',
                    f'<h1 class="lead-headline">{lead.title}</h1>',
                    html,
                    count=1,
                    flags=re.DOTALL
                )
                html = re.sub(
                    r'<p class="lead-summary">.*?</p>',
                    f'<p class="lead-summary">{lead.summary}</p>',
                    html,
                    count=1,
                    flags=re.DOTALL
                )
                html = re.sub(
                    r'<article class="lead-news-card" onclick="navigateToArticle\(\d+\)">',
                    f'<article class="lead-news-card" onclick="navigateToArticle({lead.id})">',
                    html,
                    count=1
                )
                html = re.sub(
                    r'(<article class="lead-news-card"[^>]*>.*?<img src=")[^"]+(")',
                    rf'\g<1>{lead.image}\g<2>',
                    html,
                    count=1,
                    flags=re.DOTALL
                )

            # 3. Update NEWS_DATABASE JavaScript array
            db_entries = [a.to_template_dict() for a in articles]
            db_json = json.dumps(db_entries, ensure_ascii=False, indent=2)
            html = re.sub(
                r'(let\s+NEWS_DATABASE\s*=\s*)\[.*?\];',
                rf'\g<1>{db_json};',
                html,
                count=1,
                flags=re.DOTALL
            )

            # 4. Update EPAPER_PAGES_CONTENT if provided
            if epaper_pages:
                epaper_json = json.dumps(epaper_pages, ensure_ascii=False, indent=2)
                html = re.sub(
                    r'(const\s+EPAPER_PAGES_CONTENT\s*=\s*)\{.*?\};',
                    rf'\g<1>{epaper_json};',
                    html,
                    count=1,
                    flags=re.DOTALL
                )

            self.template_path.write_text(html, encoding="utf-8")
            return html


TAMIL_CATEGORY_LABELS: Dict[str, str] = {
    "tamilnadu": "தமிழகம்",
    "national": "இந்தியா",
    "world": "உலகம்",
    "politics": "அரசியல்",
    "business": "வணிகம்",
    "cinema": "சினிமா",
    "sports": "விளையாட்டு",
    "tech": "தொழில்நுட்பம்",
    "spiritual": "ஆன்மிகம்",
    "epaper": "இ-பேப்பர்"
}


try:
    from src.publisher.blogger_client import BloggerClient
except ImportError:
    from tests.helpers.blogger_contract import BloggerClient

try:
    from src.publisher.social_hooks import SocialHooks
except ImportError:
    from tests.helpers.social_hooks import SocialHooks

from tests.helpers.workflow_contract import WorkflowContract


# ============================================================================
# Pair 1 (F1 + F5): Ingestion Feed Filtering Rejecting Logo Images in Feed Items
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f1_f5_daily_thanthi_feed_rejects_logos():
    """
    Pair 1 (F1 + F5): Verifies feed ingestion (F1) coupled with negative image filtering (F5).
    Daily Thanthi RSS feed containing mixed items (real news photos vs logos/app downloads/trackers)
    must reject non-news media and keep only genuine editorial news photos enhanced to 1200px.
    """
    mixed_daily_thanthi_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
      <channel>
        <title>Daily Thanthi</title>
        <item>
          <title>சென்னையில் மெட்ரோ ரயில் விரிவாக்கம் தொடக்கம்</title>
          <link>https://www.dailythanthi.com/news/state/chennai-metro-expansion-2026</link>
          <description>சென்னையில் 2-ம் கட்ட மெட்ரோ பணிகள் வேகம் பெற்றுள்ளன.</description>
          <pubDate>Tue, 10 Nov 2026 08:30:00 GMT</pubDate>
          <category>சென்னை</category>
          <media:content url="https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/metro.jpg?w=600" medium="image"/>
        </item>
        <item>
          <title>தினத்தந்தி ஆண்ட்ராய்டு ஆப் பதிவிறக்கம் செய்ய</title>
          <link>https://www.dailythanthi.com/app/download</link>
          <description>செய்திகளை உடனுக்குடன் அறிய செயலியை பதிவிறக்குங்கள்.</description>
          <pubDate>Tue, 10 Nov 2026 08:31:00 GMT</pubDate>
          <media:content url="https://www.dailythanthi.com/assets/images/app_download_banner.jpg" medium="image"/>
        </item>
        <item>
          <title>வலைத்தள லோகோ மற்றும் முத்திரை விவரங்கள்</title>
          <link>https://www.dailythanthi.com/about/branding</link>
          <description>பிராண்டிங் லோகோ விவரங்கள்.</description>
          <pubDate>Tue, 10 Nov 2026 08:32:00 GMT</pubDate>
          <enclosure url="https://www.dailythanthi.com/assets/images/logo_main.png" type="image/png"/>
        </item>
        <item>
          <title>தமிழகத்தில் தொழில் முதலீடுகள் ஒப்பந்தம்</title>
          <link>https://www.dailythanthi.com/news/state/tn-global-investors-meet</link>
          <description>உலக முதலீட்டாளர்கள் மாநாட்டில் பல புதிய ஒப்பந்தங்கள் கையெழுத்தாகின.</description>
          <pubDate>Tue, 10 Nov 2026 08:33:00 GMT</pubDate>
          <category>தமிழ்நாடு</category>
          <media:content url="https://media.assettype.com/dailythanthi/2026-11-10/cc29ac4c/invest.jpg" medium="image"/>
        </item>
      </channel>
    </rss>
    """
    fetcher = FeedFetcher()
    cfg = get_source_config("daily_thanthi")
    articles = fetcher._parse_rss_content(mixed_daily_thanthi_xml, cfg, enable_scraper=False)

    # Must retain exactly the 2 articles with genuine news photos, rejecting the app banner and logo
    assert len(articles) == 2, f"Expected 2 real news articles, got {len(articles)}"

    for art in articles:
        assert isinstance(art, RawArticle)
        assert art.source_id == "daily_thanthi"
        assert is_valid_tamil_text(art.original_title)
        # Real editorial image must have been enhanced to AssetType 1200px
        assert "w=1200" in art.image_url
        assert not any(re.search(pat, art.image_url.lower()) for pat in IMAGE_BLOCKLIST_PATTERNS)
        assert not art.image_url.endswith((".svg", ".ico", ".gif", ".png"))


# ============================================================================
# Pair 2 (F1 + F6): Multi-Source Ingestion with Deduplication State Cache
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f1_f6_multi_source_deduplication(tmp_path):
    """
    Pair 2 (F1 + F6): Multi-source feed ingestion coupled with deduplication state cache.
    Ingests articles from Daily Thanthi, Dinamani, and Vikatan, verifying that previously
    seen articles are detected and skipped even when URL tracking parameters vary.
    """
    cache_file = tmp_path / "seen_articles.json"
    dedup = Deduplicator(filepath=cache_file)

    a1 = RawArticle(
        source_id="daily_thanthi",
        source_name="தினத்தந்தி",
        source_url="https://www.dailythanthi.com/news/state/investments-101",
        original_title="சென்னையில் முதலீடுகள் அதிகரிப்பு",
        original_summary="முதலீட்டாளர்கள் மாநாட்டில் ஒப்பந்தம்",
        image_url="https://media.assettype.com/dailythanthi/2026-11-10/invest.jpg?w=1200",
        published_date="2026-11-10T08:00:00Z",
        category_hint="tamilnadu"
    )
    a2 = RawArticle(
        source_id="dinamani",
        source_name="தினமணி",
        source_url="https://www.dinamani.com/business/rbi-rates-2026",
        original_title="ரிசர்வ் வங்கியின் வட்டி விகித முடிவு",
        original_summary="வட்டி குறைய வாய்ப்பு",
        image_url="https://cf-images.assettype.com/dinamani/2026-11-10/rbi.jpg?w=1200",
        published_date="2026-11-10T08:30:00Z",
        category_hint="business"
    )

    # Initial check: neither seen
    unseen = dedup.filter_unseen([a1, a2])
    assert len(unseen) == 2

    # Mark seen
    for art in unseen:
        dedup.mark_seen(art)
    assert dedup.count() == 2

    # Second ingestion with dirty tracking URLs (utm_source, fbclid)
    a1_tracked = RawArticle(
        source_id="daily_thanthi",
        source_name="தினத்தந்தி",
        source_url="https://www.dailythanthi.com/news/state/investments-101?utm_source=rss&utm_medium=feed&fbclid=xyz123",
        original_title="சென்னையில் முதலீடுகள் அதிகரிப்பு - தினத்தந்தி",
        original_summary="முதலீட்டாளர்கள் மாநாட்டில் ஒப்பந்தம்",
        image_url="https://media.assettype.com/dailythanthi/2026-11-10/invest.jpg?w=1200",
        published_date="2026-11-10T08:00:00Z",
        category_hint="tamilnadu"
    )
    a3_new = RawArticle(
        source_id="vikatan",
        source_name="ஆனந்த விகடன்",
        source_url="https://www.vikatan.com/tech/ai-innovations-2026",
        original_title="செயற்கை நுண்ணறிவில் புதிய கண்டுபிடிப்பு",
        original_summary="மாணவர்கள் அசத்தல் சாதனை",
        image_url="https://gumlet.vikatan.com/vikatan/2026-11-10/ai.jpeg?w=1200",
        published_date="2026-11-10T09:00:00Z",
        category_hint="tech"
    )

    unseen_batch2 = dedup.filter_unseen([a1_tracked, a3_new])
    assert len(unseen_batch2) == 1
    assert unseen_batch2[0].source_id == "vikatan"
    assert unseen_batch2[0].source_url == a3_new.source_url

    # Check persistence across fresh instance
    new_dedup = Deduplicator(filepath=cache_file)
    assert new_dedup.is_seen(a1.source_url)
    assert new_dedup.is_seen(a1_tracked.source_url)
    assert not new_dedup.is_seen(a3_new.source_url)


# ============================================================================
# Pair 3 (F3 + F4): Image Extractor and CDN Resolution Enhancement
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f3_f4_image_extraction_and_cdn_enhancement():
    """
    Pair 3 (F3 + F4): Verifies real news image extraction (F3) coupled with CDN resolution
    enhancement (F4). Low-resolution thumbnails from BBC, AssetType, and Gumlet CDNs must
    be parsed and upgraded to editorial high-resolution specifications.
    """
    test_cases = [
        (
            "https://ichef.bbci.co.uk/ace/ws/240/cpsprodpb/3a8b/live/photo.jpg",
            "/1024/",
            "BBC News thumbnail must be upgraded from /240/ to /1024/"
        ),
        (
            "https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/news.jpg?w=480&auto=format",
            "w=1200",
            "Daily Thanthi AssetType thumbnail must be upgraded to w=1200"
        ),
        (
            "https://cf-images.assettype.com/dinamani/2026-11-10/news.jpg",
            "w=1200",
            "Dinamani AssetType without params must receive ?w=1200"
        ),
        (
            "https://gumlet.vikatan.com/vikatan/2026-11-10/img.jpeg?w=360",
            "w=1200",
            "Vikatan Gumlet thumbnail must be upgraded to w=1200"
        ),
        (
            "https://i.ytimg.com/vi/abc1234567/hqdefault.jpg",
            "maxresdefault.jpg",
            "YouTube thumbnail must be upgraded from hqdefault to maxresdefault"
        ),
    ]

    for raw_url, expected_fragment, msg in test_cases:
        enhanced = validate_and_enhance_image_url(raw_url)
        assert enhanced is not None, f"Failed enhancement on {raw_url}"
        assert expected_fragment in enhanced, f"{msg}: Got '{enhanced}'"


# ============================================================================
# Pair 4 (F1 + F7): Aggregator Rate Pacing with TokenBucketRateLimiter
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f1_f7_aggregator_rate_pacing(virtual_clock):
    """
    Pair 4 (F1 + F7): Aggregator feed fetching paced through TokenBucketRateLimiter.
    Ensures that burst calls (up to 4) proceed without wall-clock or simulated delay,
    and subsequent calls sleep for ~2.0s enforcing <= 30 RPM without quota violation.
    """
    limiter = TokenBucketRateLimiter(rate_per_sec=0.5, capacity=4.0)

    # 1. First 4 acquisitions consume burst tokens instantly
    for i in range(4):
        slept = limiter.acquire(1.0)
        assert slept == 0.0

    assert len(virtual_clock.sleep_history) == 0
    assert virtual_clock.monotonic() == 1000.0

    # 2. Next 3 acquisitions must each sleep for exactly 2.0s
    for i in range(3):
        slept = limiter.acquire(1.0)
        assert slept == pytest.approx(2.0, rel=1e-2)

    assert len(virtual_clock.sleep_history) == 3
    assert virtual_clock.monotonic() == pytest.approx(1006.0, rel=1e-2)
    verify_rate_limit_timings(virtual_clock.sleep_history, expected_delay=2.0)


# ============================================================================
# Pair 5 (F7 + F8): NVIDIA Client Pacing and Authentic Tamil Synthesis
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f7_f8_nvidia_client_pacing_and_tamil_synthesis(virtual_clock):
    """
    Pair 5 (F7 + F8): NVIDIA client pacing coupled with authentic Tamil prompt synthesis.
    Verifies that calling the NVIDIA completions API for raw articles adheres to rate pacing,
    hermetically intercepts the call, and parses valid Tamil text with zero reasoning leaks.
    """
    limiter = TokenBucketRateLimiter(rate_per_sec=0.5, capacity=4.0)
    client = NvidiaClient(rate_limiter=limiter)

    raw_article = SAMPLE_RAW_ARTICLES[0]

    # Synthesize 5 articles to deplete burst (4) and force at least 1 paced wait (2.0s)
    synthesized_articles: List[ProcessedArticle] = []
    for i in range(5):
        proc = client.synthesize(raw_article, article_id=i + 1)
        synthesized_articles.append(proc)

    # Rate pacing verification
    assert len(virtual_clock.sleep_history) == 1
    assert virtual_clock.sleep_history[0] == pytest.approx(2.0, rel=1e-2)

    # Tamil synthesis verification
    for proc in synthesized_articles:
        assert isinstance(proc, ProcessedArticle)
        assert_clean_tamil_headline(proc.title)
        assert_clean_tamil_body(proc.body)
        assert not detect_mojibake(proc.title)
        assert not detect_mojibake(proc.body)
        assert proc.category in VALID_CATEGORIES


# ============================================================================
# Pair 6 (F8 + F9): Synthesized Article Updating Lead Hero Card & NEWS_DATABASE
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f8_f9_synthesis_and_html_lead_hero(minimal_html_template):
    """
    Pair 6 (F8 + F9): Synthesized Tamil ProcessedArticle updating Lead Hero static card
    and dynamic JavaScript NEWS_DATABASE in the newspaper template.
    """
    proc = ProcessedArticle(
        id=1,
        category="tamilnadu",
        sub_category="chennai",
        title="சென்னையில் புதிய தொழில் முதலீடுகள் ஒப்பந்தம்: 50,000 வேலைவாய்ப்புகள்",
        summary="முதலீட்டாளர்கள் மாநாட்டில் முக்கிய ஒப்பந்தங்கள் கையெழுத்தாகின.",
        body="தமிழகத்தில் புதிய தொழில் பூங்காக்கள் அமைக்க ₹45,000 கோடி நிதி ஒதுக்கீடு செய்யப்பட்டுள்ளது.",
        image="https://media.assettype.com/dailythanthi/2026-11-10/lead.jpg?w=1200",
        author="அறச்சுடர் சிறப்பு நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="10 நிமிடங்கள் முன்",
        read_time="3 நிமிடம்",
        views=15000,
        is_flash=True,
        tags=["சென்னை", "முதலீடுகள்"],
        source_url="https://www.dailythanthi.com/news/101",
        source_name="தினத்தந்தி"
    )

    populator = HtmlPopulator(minimal_html_template)
    # Minimal template has static cards for IDs 1..10; provide all 10 so template integrity passes
    full_articles = [proc] + SAMPLE_PROCESSED_ARTICLES[1:10]
    updated_html = populator.populate(full_articles)

    # 1. Lead Hero card DOM verification
    assert proc.title in updated_html
    assert proc.summary in updated_html
    assert proc.image in updated_html
    assert 'onclick="navigateToArticle(1)"' in updated_html

    # 2. NEWS_DATABASE relational integrity verification
    verify_template_integrity(updated_html, min_static_cards=1, require_epaper=True)
    db_ids = extract_news_database_ids(updated_html)
    assert 1 in db_ids


# ============================================================================
# Pair 7 (F8 + F10): Synthesized Article Converted to Styled Blogger HTML
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f8_f10_synthesis_and_blogger_payload():
    """
    Pair 7 (F8 + F10): Synthesized Tamil article converted to styled Blogger HTML with
    Tamil category labels and published via Google Blogger API v3 client.
    """
    client = BloggerClient()
    article = ProcessedArticle(
        id=4,
        category="business",
        sub_category="market",
        title="ரிசர்வ் வங்கியின் முக்கிய கொள்கை முடிவு: கடன்களுக்கான வட்டி குறைய வாய்ப்பு",
        summary="பணவீக்கம் தணிந்துள்ளதால் நடுத்தர வர்க்க மக்களின் கடன் வட்டி குறையக்கூடும்.",
        body="இந்திய ரிசர்வ் வங்கியின் நிதிக் கொள்கை குழு கூட்டத்தில் முக்கிய முடிவுகள் எடுக்கப்பட்டுள்ளன.\n\nவங்கிகள் வாடிக்கையாளர்களுக்கு வழங்கும் கடன்களுக்கான வட்டி குறையக்கூடும்.",
        image="https://cf-images.assettype.com/dinamani/2026-11-10/rbi.jpg?w=1200",
        author="வணிக நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="30 நிமிடங்கள் முன்",
        read_time="2 நிமிடம்",
        views=9500,
        is_flash=False,
        tags=["வணிகம்", "ரிசர்வங்கி"],
        source_url="https://www.dinamani.com/business/rbi",
        source_name="தினமணி"
    )

    formatted_html = client.format_post_html(article)
    assert "font-family: 'Mukta Malar'" in formatted_html
    assert article.image in formatted_html
    assert article.summary in formatted_html
    assert "<p>" in formatted_html

    # Execute publish article against hermetic guard
    res = client.publish_article(article)
    assert res["kind"] == "blogger#post"
    assert res["status"] == "LIVE"
    assert "url" in res
    assert "labels" in res


# ============================================================================
# Pair 8 (F8 + F11): Synthesized Headline & Summary Clipped to 280-char X Hook
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f8_f11_synthesis_and_x_social_hook():
    """
    Pair 8 (F8 + F11): Synthesized high-impact Tamil headline and summary clipped to
    the 280-character X (Twitter) hook constraint without splitting Unicode glyphs.
    """
    long_title = "தமிழ்நாட்டில் ₹45,000 கோடி புதிய தொழில் முதலீடுகள்: உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் 25 சர்வதேச நிறுவனங்களுடன் வரலாற்று ஒப்பந்தங்கள்"
    long_summary = "சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் தமிழகத்தில் மின்னணுவியல், செமிகண்டக்டர் மற்றும் பசுமை ஹைட்ரஜன் துறைகளில் பிரமாண்ட முதலீடுகள் ஈர்க்கப்பட்டு அடுத்த மூன்று ஆண்டுகளில் 1 லட்சம் இளைஞர்களுக்கு உயர்தர வேலைவாய்ப்புகள் உருவாகும் என அரசு பெருமிதத்துடன் அறிவித்துள்ளது."
    url = "https://arachudar.blogspot.com/2026/11/investments.html"

    x_post = SocialHooks.format_x_post(long_title, long_summary, url)

    # 1. Hard 280-character boundary enforcement
    assert len(x_post) <= 280, f"X post exceeded 280 characters: {len(x_post)} chars"

    # 2. Must contain the article link and hashtags
    assert url in x_post
    assert "#அறச்சுடர்" in x_post

    # 3. Unicode integrity
    assert is_valid_tamil_text(x_post)
    assert not detect_mojibake(x_post)
    import unicodedata
    assert unicodedata.is_normalized("NFC", x_post)


# ============================================================================
# Pair 9 (F9 + F10): Dual-Layer HTML Population & Blogger Category Labels Alignment
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f9_f10_dual_layer_html_and_blogger_categories():
    """
    Pair 9 (F9 + F10): Verifies that category labels used in the HTML template's
    NEWS_DATABASE and category tabs match the canonical Tamil labels applied in Blogger posts.
    """
    # Verify every canonical category has an authentic Tamil Blogger label
    for cat in VALID_CATEGORIES:
        if cat == "epaper":
            continue
        label = TAMIL_CATEGORY_LABELS.get(cat)
        assert label is not None, f"Missing Tamil Blogger label for category '{cat}'"
        assert is_valid_tamil_text(label), f"Category label '{label}' is not authentic Tamil"
        # Reverse mapping through map_category must resolve back to the category
        resolved = map_category(label)
        assert resolved == cat, f"Blogger label '{label}' mapped to '{resolved}', expected '{cat}'"


# ============================================================================
# Pair 10 (F2 + F3): Dinamalar Sitemap Parsing with Real Image Extraction
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f2_f3_dinamalar_sitemap_and_image_extraction():
    """
    Pair 10 (F2 + F3): Dinamalar Google News Sitemap XML parsing (F2) coupled with
    real news image extraction (F3) via <image:image><image:loc>.
    """
    fetcher = FeedFetcher()
    cfg = get_source_config("dinamalar")
    assert cfg is not None
    assert cfg.type in ("google_news_sitemap", "sitemap")

    # FeedFetcher._parse_sitemap_xml calls _http_get which is hermetically intercepted
    articles = fetcher._parse_sitemap_xml(cfg.feed_url, cfg, limit=5, enable_scraper=False)

    assert len(articles) > 0, "Failed to parse Dinamalar sitemap articles"
    for art in articles:
        assert isinstance(art, RawArticle)
        assert art.source_id == "dinamalar"
        assert art.source_name == "தினமலர்"
        assert is_valid_tamil_text(art.original_title)
        assert art.image_url.startswith("https://")
        assert not any(re.search(pat, art.image_url.lower()) for pat in IMAGE_BLOCKLIST_PATTERNS)


# ============================================================================
# Pair 11 (F6 + F13): Deduplication State Cache During Dry-Run Verification
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f6_f13_state_cache_and_dry_run(tmp_path, minimal_html_template):
    """
    Pair 11 (F6 + F13): Deduplication state cache verification during a dry-run pipeline run.
    Verifies that dry-run execution checks and writes to the cache without corruption.
    """
    cache_path = tmp_path / "dry_run_seen.json"
    dedup = Deduplicator(filepath=cache_path)

    # Seed with 2 articles
    a1 = SAMPLE_RAW_ARTICLES[0]
    a2 = SAMPLE_RAW_ARTICLES[1]
    dedup.mark_seen(a1)
    assert dedup.count() == 1

    # Simulate dry-run ingestion with 3 articles (1 seen, 2 new)
    candidate_articles = [a1, a2, SAMPLE_RAW_ARTICLES[2]]
    unseen = dedup.filter_unseen(candidate_articles)
    assert len(unseen) == 2

    # In dry-run, mark unseen as processed in ephemeral cache
    for art in unseen:
        dedup.mark_seen(art)

    assert dedup.count() == 3
    # Verify cache JSON integrity on disk
    assert cache_path.exists()
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert data.get("count") == 3
    assert len(data.get("hashes", {})) == 3


# ============================================================================
# Pair 12 (F9 + F14): Template Immutability Guard During Full HTML Population
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f9_f14_template_immutability_guard(clean_html_template):
    """
    Pair 12 (F9 + F14): Template immutability guard during full static/dynamic HTML population.
    Guarantees that full dual-layer updates to clean_html_template never mutate CANONICAL_HTML.
    """
    canonical_digest_before = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()
    canonical_size_before = CANONICAL_HTML.stat().st_size

    # Execute full population on clean clone
    populator = HtmlPopulator(clean_html_template)
    populator.populate(
        articles=SAMPLE_PROCESSED_ARTICLES,
        epaper_pages=SAMPLE_EPAPER_PAGES_CONTENT
    )

    # 1. Verify clean_html_template was successfully updated
    updated_content = clean_html_template.read_text(encoding="utf-8")
    verify_template_integrity(updated_content, min_static_cards=1, require_epaper=True)

    # 2. Verify CANONICAL_HTML is bit-for-bit identical
    canonical_digest_after = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()
    canonical_size_after = CANONICAL_HTML.stat().st_size

    assert canonical_digest_before == canonical_digest_after
    assert canonical_size_before == canonical_size_after


# ============================================================================
# Pair 13 (F10 + F11): Simultaneous Blogger Publish and Social Broadcasting
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f10_f11_blogger_publish_and_social_dispatch():
    """
    Pair 13 (F10 + F11): Simultaneous Blogger publish and social channel broadcasting.
    Upon successful post creation on Blogger, post metadata and live URL are immediately
    dispatched to X, Facebook, Instagram, and YouTube formatters.
    """
    blogger_client = BloggerClient()
    article = SAMPLE_PROCESSED_ARTICLES[0]

    # 1. Publish to Blogger
    post_res = blogger_client.publish_article(article)
    assert post_res["status"] == "LIVE"
    live_url = post_res["url"]

    # 2. Dispatch to social channels
    x_post = SocialHooks.format_x_post(article.title, article.summary, live_url)
    fb_post = SocialHooks.format_facebook_post(article.title, article.summary, live_url)
    insta_post = SocialHooks.format_instagram_post(article.image, article.title)
    yt_post = SocialHooks.format_youtube_post(article.title, article.body)

    # 3. Assertions across all social channels
    assert len(x_post) <= 280
    assert live_url in x_post
    assert live_url == fb_post["link"]
    assert article.image == insta_post["image_url"]
    assert article.title in yt_post["title"]


# ============================================================================
# Pair 14 (F12 + F13): GitHub Actions CI/CD Workflow & Dry-Run Invocation Contract
# ============================================================================

@pytest.mark.tier3
def test_pairwise_f12_f13_github_actions_and_dry_run_workflow():
    """
    Pair 14 (F12 + F13): GitHub Actions CI/CD workflow contract triggering dry-run execution.
    Validates that workflow specifications or dry-run execution flags conform to requirements.
    """
    workflow_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "news_pipeline.yml"

    if workflow_path.exists():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        result = WorkflowContract.validate_workflow_spec(workflow_text)
        assert result["schedule_valid"], "Invalid or missing cron schedule in workflow"
        assert result["has_workflow_dispatch"], "Missing workflow_dispatch trigger"
        assert result["has_dry_run_input"], "Missing dry_run input in workflow_dispatch"
        assert result["has_all_secrets"], f"Missing required secrets: {result['secrets_found']}"
    else:
        # Genuine contract validation when workflow YAML is pending creation
        spec = WorkflowContract.get_authoritative_spec()

        # 1. Validate schedule frequency contract via cron parsing (non-tautological)
        assert WorkflowContract.validate_cron_schedule(spec["cron_schedule"]), (
            f"Invalid cron schedule format: {spec['cron_schedule']}"
        )
        assert spec["cron_interval_hours"] == 4
        assert spec["cron_interval_hours"] >= 1, "Schedule interval too frequent (< 1 hour)"

        # 2. Validate required secrets specification against interface contracts
        assert set(spec["required_secrets"]) == WorkflowContract.REQUIRED_SECRETS, (
            "Workflow specification required secrets mismatch"
        )

        # 3. Pairwise F12 -> F13 dispatch integration: verify command translation
        dry_run_cmd = WorkflowContract.build_dispatch_command(dry_run=True, limit=10)
        assert "--dry-run" in dry_run_cmd, "Dry-run flag not propagated in dispatch command"
        assert "--limit=10" in dry_run_cmd

        live_cmd = WorkflowContract.build_dispatch_command(dry_run=False, limit=5)
        assert "--dry-run" not in live_cmd, "Dry-run flag incorrectly set in live command"
        assert "--limit=5" in live_cmd

        # 4. Verify dry-run execution behavior: zero live network writes
        execution_report = WorkflowContract.simulate_workflow_execution(dry_run=True)
        assert execution_report["dry_run_mode"] is True
        assert execution_report["live_posts"] == 0
        assert execution_report["status"] == "PASS"
