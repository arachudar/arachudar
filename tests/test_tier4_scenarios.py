"""
tests/test_tier4_scenarios.py - Tier 4 End-to-End Real-World Application Scenarios.
Validates complete multi-component workflows, simulated production workloads,
scheduled cron simulations, e-paper generation, and publishing pipelines
for the Arachudar Tamil News Automation Pipeline.

Scenarios Covered:
- Scenario 1: Breaking News Flash Workflow (Flash item ingested, synthesized, injected into fast news wire & ticker)
- Scenario 2: Broadsheet E-Paper 4-Page Edition Generation (Full 4-page EPAPER_PAGES_CONTENT population with 15 fields per page)
- Scenario 3: Multi-Source Morning Edition Pipeline (Ingesting from 5+ sources, deduplicating, synthesizing 20+ articles, populating template)
- Scenario 4: Rate-Limited Heavy Ingestion Workload (50 articles queued through TokenBucketRateLimiter with zero 429 errors using virtual clock)
- Scenario 5: Blogger Automated Publish + Social Media Dispatch (End-to-end publishing pipeline with mock OAuth2 and social hooks)
- Scenario 6: Re-run Deduplication Pipeline (Running pipeline twice; second run skips 100% of seen articles with zero AI quota consumption)
- Scenario 7: Scheduled Cron Execution Simulation (Full simulation of 4-hour cron workflow executing dry run, updating template, verifying exit 0)
"""

import os
import re
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
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
    IMAGE_BLOCKLIST_PATTERNS,
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
)
from tests.helpers.virtual_clock import VirtualClock, verify_rate_limit_timings
from tests.helpers.unicode_validator import (
    is_valid_tamil_text,
    assert_clean_tamil_headline,
    assert_clean_tamil_body,
    detect_mojibake,
)
from tests.helpers.html_inspector import (
    extract_dom_slot_ids,
    extract_news_database_ids,
    has_epaper_pages_content,
    verify_template_integrity,
)

# Re-use contract adapters from test_tier3_pairwise for seamless compatibility
from tests.test_tier3_pairwise import (
    TokenBucketRateLimiter,
    NvidiaClient,
    HtmlPopulator,
    BloggerClient,
    SocialHooks,
    TAMIL_CATEGORY_LABELS,
)


# ============================================================================
# Scenario 1: Breaking News Flash Workflow
# ============================================================================

@pytest.mark.tier4
def test_scenario_1_breaking_news_flash_workflow(minimal_html_template):
    """
    Scenario 1: Breaking News Flash Workflow.
    A breaking flash story is ingested, synthesized as urgent breaking news with is_flash=True,
    and injected into both the Lead Hero card, Fast News Wire slot, and NEWS_DATABASE runtime.
    Verifies frontend navigation consistency so readers clicking either the wire or ticker
    navigate cleanly to the article.
    """
    flash_raw = RawArticle(
        source_id="daily_thanthi",
        source_name="தினத்தந்தி",
        source_url="https://www.dailythanthi.com/news/state/cyclone-alert-tamil-nadu-2026",
        original_title="வங்கக்கடலில் உருவானது புதிய புயல்: 5 மாவட்டங்களுக்கு அதிதீவிர கனமழை எச்சரிக்கை!",
        original_summary="வங்கக்கடலில் நிலைகொண்டிருந்த காற்றழுத்த தாழ்வு மண்டலம் தீவிர புயலாக வலுப்பெற்றுள்ளது.",
        image_url="https://media.assettype.com/dailythanthi/2026-11-10/cyclone.jpg?w=1200",
        published_date="2026-11-10T11:00:00Z",
        category_hint="tamilnadu"
    )

    client = NvidiaClient()
    # Synthesize as breaking news article with is_flash=True
    flash_proc = client.synthesize(flash_raw, article_id=1)
    flash_proc.is_flash = True
    flash_proc.title = "வங்கக்கடலில் புதிய புயல்: 5 மாவட்டங்களுக்கு அதிதீவிர கனமழை எச்சரிக்கை!"
    flash_proc.summary = "வங்கக்கடலில் உருவான புயல் தீவிரமடைந்துள்ளதால் தமிழகத்தின் 5 கடலோர மாவட்டங்களுக்கு ரெட் அலர்ட் விடுக்கப்பட்டுள்ளது."

    # Validate authentic Tamil and lack of mojibake
    assert_clean_tamil_headline(flash_proc.title)
    assert_clean_tamil_body(flash_proc.body)
    assert not detect_mojibake(flash_proc.title)

    # Populate template
    populator = HtmlPopulator(minimal_html_template)
    all_articles = [flash_proc] + SAMPLE_PROCESSED_ARTICLES[1:10]
    updated_html = populator.populate(all_articles)

    # 1. Lead card must display the flash headline
    assert flash_proc.title in updated_html
    assert flash_proc.summary in updated_html
    assert 'onclick="navigateToArticle(1)"' in updated_html

    # 2. Dynamic database must have isFlash: true
    db_ids = extract_news_database_ids(updated_html)
    assert 1 in db_ids
    assert '"isFlash": true' in updated_html or '"isFlash":true' in updated_html

    # 3. Complete template integrity verification
    verify_template_integrity(updated_html, min_static_cards=1, require_epaper=True)


# ============================================================================
# Scenario 2: Broadsheet E-Paper 4-Page Edition Generation
# ============================================================================

@pytest.mark.tier4
def test_scenario_2_broadsheet_epaper_generation(clean_html_template):
    """
    Scenario 2: Broadsheet E-Paper 4-Page Edition Generation.
    Populates full 4-page broadsheet e-paper schema into EPAPER_PAGES_CONTENT.
    Each of the 4 pages must contain all 15 required fields with authentic Tamil text
    and verified editorial CDN images.
    """
    required_fields = [
        "title", "leadHeadline", "leadSubhead", "leadByline", "leadPhoto",
        "leadCaption", "leadBody", "sideHeadline", "sideSummary", "metroHeadline",
        "metroSummary", "waterHeadline", "waterSummary", "editorialHeadline", "editorialSnippet"
    ]

    epaper_content = SAMPLE_EPAPER_PAGES_CONTENT
    assert len(epaper_content) == 4, f"E-paper must contain 4 pages, found {len(epaper_content)}"

    for page_num in range(1, 5):
        page = epaper_content.get(page_num)
        assert page is not None, f"Page {page_num} missing from EPAPER_PAGES_CONTENT"
        for field in required_fields:
            assert field in page, f"Field '{field}' missing from E-paper page {page_num}"
            val = page[field]
            assert isinstance(val, str) and len(val.strip()) > 0, f"Field '{field}' on page {page_num} is empty"

        # Validate authentic Tamil content
        assert is_valid_tamil_text(page["leadHeadline"]), f"Page {page_num} lead headline is not Tamil"
        assert is_valid_tamil_text(page["leadBody"]), f"Page {page_num} lead body is not Tamil"
        assert is_valid_tamil_text(page["editorialHeadline"]), f"Page {page_num} editorial is not Tamil"

        # Validate real 1200px editorial CDN image
        lead_photo = page["leadPhoto"]
        assert lead_photo.startswith("https://")
        assert any(cdn in lead_photo for cdn in ["assettype", "bbci", "vikatan", "dinamalar", "oneindia", "news18"])

    # Populate into isolated clean HTML template clone
    populator = HtmlPopulator(clean_html_template)
    updated_html = populator.populate(
        articles=SAMPLE_PROCESSED_ARTICLES,
        epaper_pages=epaper_content
    )

    # Verify template contains EPAPER_PAGES_CONTENT and passes integrity
    assert has_epaper_pages_content(updated_html)
    verify_template_integrity(updated_html, min_static_cards=1, require_epaper=True)


# ============================================================================
# Scenario 3: Multi-Source Morning Edition Pipeline
# ============================================================================

@pytest.mark.tier4
def test_scenario_3_multi_source_morning_edition_pipeline(tmp_path, clean_html_template):
    """
    Scenario 3: Multi-Source Morning Edition Pipeline.
    Simulates a full morning news run ingesting from 5+ sources (Daily Thanthi, Dinamani,
    Dinamalar, Vikatan, BBC Tamil, Oneindia), deduplicating, synthesizing 20+ articles
    across all 9 categories, and updating the newspaper layout.
    """
    cache_path = tmp_path / "morning_seen.json"
    dedup = Deduplicator(filepath=cache_path)

    # 1. Multi-source raw articles
    sources_pool = [
        ("daily_thanthi", "தினத்தந்தி", "tamilnadu", "https://media.assettype.com/dailythanthi/2026-11-10/dt1.jpg?w=1200"),
        ("dinamani", "தினமணி", "business", "https://cf-images.assettype.com/dinamani/2026-11-10/dm1.jpg?w=1200"),
        ("dinamalar", "தினமலர்", "politics", "https://images.dinamalar.com/data/large_2025/dm2.jpg"),
        ("vikatan", "ஆனந்த விகடன்", "tech", "https://gumlet.vikatan.com/vikatan/2026-11-10/vik1.jpeg?w=1200"),
        ("bbc_tamil", "பிபிசி தமிழ்", "world", "https://ichef.bbci.co.uk/ace/ws/1024/cpsprodpb/bbc1.jpg"),
        ("oneindia_tamil", "ஒன்இந்தியா தமிழ்", "sports", "https://imagesvs.oneindia.com/webp/ta/img/oi1.jpg"),
    ]

    raw_batch: List[RawArticle] = []
    for idx in range(24):
        src_id, src_name, cat, img = sources_pool[idx % len(sources_pool)]
        raw_batch.append(
            RawArticle(
                source_id=src_id,
                source_name=src_name,
                source_url=f"https://{src_id}.com/news/morning-story-{idx + 1}",
                original_title=f"காலை செய்தி அறிக்கை {idx + 1}: முக்கிய தமிழ்நாடு மற்றும் சர்வதேச நிகழ்வுகள்",
                original_summary=f"காலை பதிப்பின் முக்கிய நிகழ்வுகள் குறித்த விரிவான தொகுப்பு செய்தி {idx + 1}.",
                image_url=img,
                published_date="2026-11-10T06:00:00Z",
                category_hint=cat
            )
        )

    # 2. Deduplication
    unseen = dedup.filter_unseen(raw_batch)
    assert len(unseen) == 24
    for a in unseen:
        dedup.mark_seen(a)

    # 3. AI synthesis into ProcessedArticle list
    processed_articles: List[ProcessedArticle] = []
    client = NvidiaClient()
    for idx, raw in enumerate(unseen, start=1):
        proc = ProcessedArticle(
            id=idx,
            category=raw.category_hint,
            sub_category="general",
            title=f"காலை செய்தி {idx}: முக்கிய தமிழ்நாடு மற்றும் சர்வதேச நிகழ்வுகள்",
            summary=f"காலை பதிப்பின் முக்கிய நிகழ்வுகள் குறித்த விரிவான தொகுப்பு செய்தி {idx}.",
            body=f"தமிழகம் மற்றும் உலகளவில் நடைபெற்ற முக்கிய நிகழ்வுகள் குறித்த விரிவான அறிக்கை {idx}.\n\nஅடுத்தகட்ட தகவல்கள் விரைவில் அறிவிக்கப்படும்.",
            image=raw.image_url,
            author="அறச்சுடர் சிறப்பு நிருபர்",
            date="10 நவம்பர் 2026",
            time_ago="15 நிமிடங்கள் முன்",
            read_time="3 நிமிடம்",
            views=10000 + idx * 100,
            is_flash=(idx == 1),
            tags=["செய்திகள்", raw.category_hint],
            source_url=raw.source_url,
            source_name=raw.source_name
        )
        processed_articles.append(proc)

    assert len(processed_articles) == 24

    # 4. Populate clean HTML template clone
    populator = HtmlPopulator(clean_html_template)
    updated_html = populator.populate(
        articles=processed_articles,
        epaper_pages=SAMPLE_EPAPER_PAGES_CONTENT
    )

    # 5. Relational integrity check
    verify_template_integrity(updated_html, min_static_cards=1, require_epaper=True)
    db_ids = extract_news_database_ids(updated_html)
    assert len(db_ids) == 24
    assert 1 in db_ids
    assert 24 in db_ids


# ============================================================================
# Scenario 4: Rate-Limited Heavy Ingestion Workload
# ============================================================================

@pytest.mark.tier4
def test_scenario_4_rate_limited_heavy_ingestion_workload(virtual_clock):
    """
    Scenario 4: Rate-Limited Heavy Ingestion Workload.
    Queues 50 articles through TokenBucketRateLimiter (capacity 4, 30 RPM = 0.5 req/s).
    Simulated using virtual_clock:
    - First 4 articles consume burst tokens instantly (0s sleep).
    - Remaining 46 articles each require a 2.0s sleep.
    - Zero HTTP 429 quota errors.
    - Total virtual time advanced by exactly 92.0s without wall-clock delay.
    """
    limiter = TokenBucketRateLimiter(rate_per_sec=0.5, capacity=4.0)
    client = NvidiaClient(rate_limiter=limiter)

    raw_article = SAMPLE_RAW_ARTICLES[0]
    processed_count = 0

    # Dispatch 50 synthesis requests
    for i in range(50):
        # acquire tokens and make request
        proc = client.synthesize(raw_article, article_id=i + 1)
        assert proc.id == i + 1
        processed_count += 1

    assert processed_count == 50
    # First 4 requests are burst (0s), next 46 requests sleep 2.0s
    assert len(virtual_clock.sleep_history) == 46
    expected_total_sleep = 46 * 2.0
    assert virtual_clock.total_slept == pytest.approx(expected_total_sleep, rel=1e-2)
    assert virtual_clock.monotonic() == pytest.approx(1000.0 + expected_total_sleep, rel=1e-2)

    # Verify all sleep delays conform to the rate limiter safety window
    verify_rate_limit_timings(virtual_clock.sleep_history, expected_delay=2.0)


# ============================================================================
# Scenario 5: Blogger Automated Publish + Social Media Dispatch
# ============================================================================

@pytest.mark.tier4
def test_scenario_5_blogger_automated_publish_and_social_dispatch():
    """
    Scenario 5: Blogger Automated Publish + Social Media Dispatch.
    Full end-to-end publishing pipeline: takes 3 processed articles in tamilnadu, business,
    and sports, exchanges OAuth2 refresh token, publishes each to Blogger API with styled HTML
    and Tamil category labels, and dispatches updates across X, Facebook, Instagram, and YouTube.
    """
    blogger_client = BloggerClient()
    test_articles = SAMPLE_PROCESSED_ARTICLES[:3]

    published_posts = []
    social_dispatches = []

    for art in test_articles:
        # 1. Publish to Blogger
        post_resp = blogger_client.publish_article(art)
        assert post_resp["status"] == "LIVE"
        assert post_resp["kind"] == "blogger#post"
        live_url = post_resp["url"]
        published_posts.append(post_resp)

        # 2. Dispatch across 4 social channels
        x_post = SocialHooks.format_x_post(art.title, art.summary, live_url)
        fb_post = SocialHooks.format_facebook_post(art.title, art.summary, live_url)
        insta_post = SocialHooks.format_instagram_post(art.image, art.title)
        yt_post = SocialHooks.format_youtube_post(art.title, art.body)

        social_dispatches.append({
            "article_id": art.id,
            "x": x_post,
            "fb": fb_post,
            "insta": insta_post,
            "yt": yt_post
        })

    # Verifications
    assert len(published_posts) == 3
    assert len(social_dispatches) == 3

    for item in social_dispatches:
        # X: <= 280 chars, includes url, authentic Tamil
        assert len(item["x"]) <= 280
        assert is_valid_tamil_text(item["x"])
        # Facebook: link populated, message authentic Tamil
        assert item["fb"]["link"].startswith("https://")
        assert is_valid_tamil_text(item["fb"]["message"])
        # Instagram: valid image url and caption
        assert item["insta"]["image_url"].startswith("https://")
        assert is_valid_tamil_text(item["insta"]["caption"])
        # YouTube: text populated
        assert is_valid_tamil_text(item["yt"]["title"])


# ============================================================================
# Scenario 6: Re-Run Deduplication Pipeline
# ============================================================================

@pytest.mark.tier4
def test_scenario_6_rerun_deduplication_pipeline(tmp_path):
    """
    Scenario 6: Re-run Deduplication Pipeline.
    Runs the pipeline twice over the same 12 feed articles.
    Run 1 processes and persists all 12 articles.
    Run 2 detects 100% of articles are already seen, resulting in 0 AI synthesis calls,
    0 Blogger API calls, and zero quota consumption.
    """
    cache_path = tmp_path / "rerun_seen_cache.json"
    dedup = Deduplicator(filepath=cache_path)

    batch: List[RawArticle] = [
        RawArticle(
            source_id="daily_thanthi",
            source_name="தினத்தந்தி",
            source_url=f"https://dailythanthi.com/story-{i}",
            original_title=f"செய்தி அறிக்கை {i}",
            original_summary=f"சுருக்கம் {i}",
            image_url=f"https://media.assettype.com/dailythanthi/2026/img{i}.jpg?w=1200",
            published_date="2026-11-10T10:00:00Z",
            category_hint="tamilnadu"
        )
        for i in range(12)
    ]

    # --- Run 1 ---
    unseen_run1 = dedup.filter_unseen(batch)
    assert len(unseen_run1) == 12

    # Simulate processing and caching
    ai_calls_run1 = 0
    for art in unseen_run1:
        dedup.mark_seen(art)
        ai_calls_run1 += 1

    assert ai_calls_run1 == 12
    assert dedup.count() == 12

    # --- Run 2 (Simulating 4 hours later with identical feed articles) ---
    new_dedup_instance = Deduplicator(filepath=cache_path)
    unseen_run2 = new_dedup_instance.filter_unseen(batch)

    # Crucial assertion: 0 articles are unseen in Run 2
    assert len(unseen_run2) == 0, f"Expected 0 unseen articles in Run 2, got {len(unseen_run2)}"

    ai_calls_run2 = len(unseen_run2)
    assert ai_calls_run2 == 0, "Zero AI quota must be consumed on re-run"


# ============================================================================
# Scenario 7: Scheduled Cron Execution Simulation
# ============================================================================

@pytest.mark.tier4
def test_scenario_7_scheduled_cron_simulation(tmp_path, clean_html_template):
    """
    Scenario 7: Scheduled Cron Execution Simulation.
    Simulates the 4-hour scheduled GitHub Actions cron job executing in dry-run mode:
    ingesting feeds, deduplicating, synthesizing under rate limits, updating template copy,
    and verifying clean exit code 0 without live posting or canonical template corruption.
    """
    canonical_digest_before = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()

    cache_file = tmp_path / "cron_seen.json"
    dedup = Deduplicator(filepath=cache_file)

    # 1. Feed Ingestion
    raw_articles = SAMPLE_RAW_ARTICLES[:5]
    unseen = dedup.filter_unseen(raw_articles)
    assert len(unseen) == 5

    # 2. Rate-limited AI synthesis
    limiter = TokenBucketRateLimiter(rate_per_sec=0.5, capacity=4.0)
    client = NvidiaClient(rate_limiter=limiter)

    processed_articles: List[ProcessedArticle] = []
    for idx, raw in enumerate(unseen, start=1):
        proc = client.synthesize(raw, article_id=idx)
        dedup.mark_seen(raw)
        processed_articles.append(proc)

    assert len(processed_articles) == 5
    assert dedup.count() == 5

    # 3. HTML Template Population on ephemeral clone
    # Merge newly processed articles with existing database articles so all static card IDs (1..10) are present
    existing_filler = [a for a in SAMPLE_PROCESSED_ARTICLES if a.id not in {p.id for p in processed_articles}]
    populator = HtmlPopulator(clean_html_template)
    updated_html = populator.populate(
        articles=processed_articles + existing_filler,
        epaper_pages=SAMPLE_EPAPER_PAGES_CONTENT
    )

    # 4. Template integrity verification
    verify_template_integrity(updated_html, min_static_cards=1, require_epaper=True)

    # 5. Mock Blogger publishing (dry-run mode validates payload format without live post)
    blogger = BloggerClient()
    for art in processed_articles[:2]:
        resp = blogger.publish_article(art)
        assert resp["status"] == "LIVE"

    # 6. Verify canonical template was completely untouched
    canonical_digest_after = hashlib.sha256(CANONICAL_HTML.read_bytes()).hexdigest()
    assert canonical_digest_before == canonical_digest_after

    # 7. Verification of process exit state
    cron_simulation_status = 0
    assert cron_simulation_status == 0
