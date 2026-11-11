"""
src/aggregator/test_aggregator.py - Comprehensive unit and integration test suite
for Milestone 1: News Aggregator, Real Image Extractor, and Deduplicator.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

from config.sources import (
    TAMIL_NEWS_SOURCES,
    VALID_CATEGORIES,
    VALID_SUBCATEGORIES,
    SourceConfig,
    get_source_config,
    map_category,
    map_subcategory,
    DEFAULT_USER_AGENT,
    DEFAULT_TIMEOUT,
)
from src.aggregator.image_extractor import (
    ImageExtractor,
    validate_and_enhance_image_url,
    extract_image_from_feed_entry,
    extract_image_from_html,
    scrape_article_image,
    IMAGE_BLOCKLIST_PATTERNS,
    BLOCKED_FILE_EXTENSIONS,
)
from src.aggregator.feed_fetcher import (
    RawArticle,
    FeedFetcher,
    _sanitize_xml,
    _clean_html_snippet,
    _normalize_date,
    fetch_articles_from_source,
    fetch_all_sources,
)
from src.aggregator.deduplicator import (
    Deduplicator,
    normalize_url,
    normalize_title,
    compute_article_hash,
)


class TestConfigSources(unittest.TestCase):
    """Tests for 15 source configurations, URLs, feed types, and category mapping."""

    def test_all_15_sources_present(self):
        expected_sources = [
            "daily_thanthi",
            "dinamalar",
            "hindu_tamil",
            "dinamani",
            "maalai_malar",
            "thinaboomi",
            "vikatan",
            "samayam_tamil",
            "oneindia_tamil",
            "bbc_tamil",
            "news18_tamil",
            "zee_news_tamil",
            "asianet_tamil",
            "google_news_tamil",
            "w3newspapers_directory",
        ]
        self.assertEqual(len(TAMIL_NEWS_SOURCES), 15)
        for src in expected_sources:
            self.assertIn(src, TAMIL_NEWS_SOURCES, f"Source {src} missing from TAMIL_NEWS_SOURCES")

    def test_source_configs_structure(self):
        for src_id, cfg in TAMIL_NEWS_SOURCES.items():
            self.assertIn("name", cfg)
            self.assertIn("tamil_name", cfg)
            self.assertIn("type", cfg)
            typed_cfg = get_source_config(src_id)
            self.assertIsNotNone(typed_cfg)
            self.assertEqual(typed_cfg.id, src_id)
            self.assertEqual(typed_cfg.name, cfg["name"])
            self.assertEqual(typed_cfg.type, cfg["type"])

    def test_category_mapping(self):
        self.assertEqual(map_category("சென்னை"), "tamilnadu")
        self.assertEqual(map_category("tamilnadu"), "tamilnadu")
        self.assertEqual(map_category("இந்தியா"), "national")
        self.assertEqual(map_category("உலகம்"), "world")
        self.assertEqual(map_category("அரசியல்"), "politics")
        self.assertEqual(map_category("வணிகம்"), "business")
        self.assertEqual(map_category("சினிமா"), "cinema")
        self.assertEqual(map_category("விளையாட்டு"), "sports")
        self.assertEqual(map_category("தொழில்நுட்பம்"), "tech")
        self.assertEqual(map_category("ஆன்மிகம்"), "spiritual")
        self.assertEqual(map_category("unknown_xyz"), "tamilnadu")  # default fallback

    def test_category_stem_mappings(self):
        # Morphological stem forms for business, spiritual, and world
        self.assertEqual(map_category("தங்க விலை நிலவரம்"), "business")
        self.assertEqual(map_category("தங்க நகை விலை உயர்வு"), "business")
        self.assertEqual(map_category("திருக்கோயில் திருவிழா கொடியேற்றம்"), "spiritual")
        self.assertEqual(map_category("கோயில் திருவிழா"), "spiritual")
        self.assertEqual(map_category("திருக்கோவில் கும்பாபிஷேகம்"), "spiritual")
        self.assertEqual(map_category("அமெரிக்க அதிபர் தேர்தல்"), "world")

    def test_category_precedence_specific_domain_over_district(self):
        # Specific domain categories must be prioritized before broad district keywords
        self.assertEqual(map_category("சென்னையில் ஐபிஎல் கிரிக்கெட் போட்டி"), "sports")
        self.assertEqual(map_category("சென்னையில் புதிய திரைப்பட டிரெய்லர் வெளியீடு"), "cinema")
        self.assertEqual(map_category("சென்னையில் தங்கம் விலை திடீர் சரிவு"), "business")
        self.assertEqual(map_category("சென்னையில் போக்குவரத்து நெரிசல்"), "tamilnadu")
        self.assertEqual(map_category("மதுரையில் கோவில் திருவிழா"), "spiritual")
        self.assertEqual(map_category("கோவையில் புதிய ஸ்மார்ட்போன் ஆப் அறிமுகம்"), "tech")
        self.assertEqual(map_category("திருச்சியில் தேர்தல் பிரச்சார பொதுக்கூட்டம்"), "politics")

    def test_subcategory_mapping(self):
        self.assertEqual(map_subcategory("tamilnadu", "சென்னை பெருநகரம்"), "chennai")
        self.assertEqual(map_subcategory("tamilnadu", "மதுரை மாவட்டம்"), "madurai")
        self.assertEqual(map_subcategory("cinema", "புதிய திரைவிமர்சனம்"), "reviews")
        self.assertEqual(map_subcategory("cinema", "ஓடிடி ரிலீஸ்"), "ott")
        self.assertEqual(map_subcategory("sports", "கிரிக்கெட் போட்டி"), "cricket")
        self.assertIsNone(map_subcategory("sports", "unknown_sub"))


class TestImageExtractor(unittest.TestCase):
    """Tests for image extraction, negative blocklist, LangImg exemption, and CDN upgrades."""

    def setUp(self):
        self.extractor = ImageExtractor()

    def test_image_url_boundaries(self):
        self.assertIsNone(self.extractor.validate_and_enhance(None))
        self.assertIsNone(self.extractor.validate_and_enhance(""))
        self.assertIsNone(self.extractor.validate_and_enhance("   "))
        self.assertIsNone(self.extractor.validate_and_enhance(123))
        self.assertIsNone(self.extractor.validate_and_enhance("data:image/png;base64,iVBORw0KGgo"))
        self.assertIsNone(self.extractor.validate_and_enhance("ftp://example.com/pic.jpg"))
        # Protocol-relative URL should normalize to https
        self.assertEqual(
            self.extractor.validate_and_enhance("//example.com/editorial/pic.jpg"),
            "https://example.com/editorial/pic.jpg",
        )

    def test_blocked_extensions(self):
        # .svg, .ico, .gif must be rejected
        self.assertIsNone(self.extractor.validate_and_enhance("https://example.com/logo.svg"))
        self.assertIsNone(self.extractor.validate_and_enhance("https://example.com/favicon.ico"))
        self.assertIsNone(self.extractor.validate_and_enhance("https://example.com/loading.gif"))

    def test_negative_patterns_blocked(self):
        blocked_samples = [
            "https://example.com/images/site-logo.jpg",
            "https://example.com/assets/favicon-32x32.png",
            "https://example.com/static/user-avatar.png",
            "https://example.com/img/placeholder.jpg",
            "https://example.com/media/no_image.png",
            "https://example.com/dummy-thumb.jpg",
            "https://example.com/blank-space.jpg",
            "https://example.com/tracking-pixel.png",
            "https://example.com/advertisement_banner.jpg",
            "https://example.com/app-download-badge.png",
            "https://example.com/play_store_button.jpg",
            "https://example.com/share-default-news.jpg",
            "https://example.com/header-bg.png",
            "https://example.com/subscribe-banner.jpg",
            "https://example.com/newsletter-box.jpg",
        ]
        for url in blocked_samples:
            self.assertIsNone(
                self.extractor.validate_and_enhance(url),
                f"URL '{url}' should have been blocked by negative filter",
            )

    def test_rejection_of_all_negative_fixture_images(self):
        # Cross-checks with tests/fixtures/sample_images.py::NEGATIVE_IMAGE_URLS
        from tests.fixtures.sample_images import NEGATIVE_IMAGE_URLS
        self.assertEqual(len(NEGATIVE_IMAGE_URLS), 14)
        for url in NEGATIVE_IMAGE_URLS:
            self.assertIsNone(
                self.extractor.validate_and_enhance(url),
                f"Fixture NEGATIVE_IMAGE_URL '{url}' should be rejected as None",
            )

    def test_ad_directories_dimensions_and_servers_blocked(self):
        ad_urls = [
            "https://asianetnews.com/images/ad_300x250.jpg",
            "https://example.com/ads/promo.jpg",
            "https://example.com/ad/promo.jpg",
            "https://example.com/doubleclick/ad.jpg",
            "https://example.com/adserver/image.jpg",
            "https://example.com/media/ad_728x90.png",
        ]
        for url in ad_urls:
            self.assertIsNone(
                self.extractor.validate_and_enhance(url),
                f"Ad URL '{url}' should be rejected by negative filter",
            )

    def test_langimg_exemption(self):
        # Samayam LangImg CDN uses msid- with publication slug like tamil-samayam.jpg
        samayam_real_photo = (
            "https://static.langimg.com/photo/imgsize-352245,msid-135713596/tamil-samayam.jpg"
        )
        validated = self.extractor.validate_and_enhance(samayam_real_photo)
        self.assertIsNotNone(validated, "LangImg real editorial photo should be exempt and accepted")
        self.assertEqual(validated, samayam_real_photo)

    def test_bbc_cdn_resolution_upgrade(self):
        bbc_thumb = (
            "https://ichef.bbci.co.uk/ace/ws/240/cpsprodpb/3a8b/live/da8fa680-dcfd-11f1-93e1-3b657b665bcf.jpg"
        )
        upgraded = self.extractor.validate_and_enhance(bbc_thumb)
        self.assertIn("/1024/", upgraded)
        self.assertNotIn("/240/", upgraded)

    def test_assettype_cdn_resolution_upgrade(self):
        asset_url = "https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg"
        upgraded = self.extractor.validate_and_enhance(asset_url)
        self.assertIn("w=1200", upgraded)
        self.assertIn("fit=max", upgraded)

        # Ensure existing params are modified/supplemented
        asset_with_params = "https://cf-images.assettype.com/dinamani/2026/img.jpg?w=400&fit=crop"
        upgraded_params = self.extractor.validate_and_enhance(asset_with_params)
        self.assertIn("w=1200", upgraded_params)
        self.assertIn("fit=max", upgraded_params)

    def test_vikatan_gumlet_cdn_resolution_upgrade(self):
        gumlet_url = "https://gumlet.vikatan.com/vikatan/2026-11-10/1xu4rr9j/whatsapp.jpeg"
        upgraded = self.extractor.validate_and_enhance(gumlet_url)
        self.assertIn("w=1200", upgraded)
        self.assertIn("h=675", upgraded)
        self.assertIn("fit=max", upgraded)

    def test_google_news_cdn_resolution_upgrade(self):
        google_cdn = (
            "https://lh3.googleusercontent.com/J6_coFbogxhRI9iM864NL_liGXvsQp2AupsKei7z0cNNfDvGUm=s100"
        )
        upgraded = self.extractor.validate_and_enhance(google_cdn)
        self.assertIn("=s0-w1200", upgraded)

    def test_youtube_thumbnail_upgrade(self):
        yt_thumb = "https://i.ytimg.com/vi/b_H_L23uG-M/hqdefault.jpg"
        upgraded = self.extractor.validate_and_enhance(yt_thumb)
        self.assertIn("maxresdefault.jpg", upgraded)

    def test_youtube_subdomains_and_thumbnail_upgrade(self):
        # Subdomains i1..i4.ytimg.com and img.youtube.com must be exempted from default pattern
        # and enhanced from hqdefault/mqdefault to maxresdefault
        subdomains = [
            "i.ytimg.com",
            "i1.ytimg.com",
            "i2.ytimg.com",
            "i3.ytimg.com",
            "i4.ytimg.com",
            "img.youtube.com",
        ]
        for sub in subdomains:
            hq_url = f"https://{sub}/vi/Ftnp_4OY2ac/hqdefault.jpg"
            enhanced_hq = self.extractor.validate_and_enhance(hq_url)
            self.assertIsNotNone(enhanced_hq, f"Subdomain {sub} hqdefault should not be None")
            self.assertEqual(enhanced_hq, f"https://{sub}/vi/Ftnp_4OY2ac/maxresdefault.jpg")

            mq_url = f"https://{sub}/vi/Ftnp_4OY2ac/mqdefault.jpg"
            enhanced_mq = self.extractor.validate_and_enhance(mq_url)
            self.assertIsNotNone(enhanced_mq, f"Subdomain {sub} mqdefault should not be None")
            self.assertEqual(enhanced_mq, f"https://{sub}/vi/Ftnp_4OY2ac/maxresdefault.jpg")

    def test_ad_networks_and_iab_display_units_blocked(self):
        # Ad networks (Google Syndication, Taboola, Outbrain, etc.) and IAB formats must be blocked
        ad_urls = [
            "https://pagead2.googlesyndication.com/pagead/imgad?id=12345",
            "https://tpc.googlesyndication.com/simgad/123456789",
            "https://images.taboola.com/taboola/image/fetch/f_jpg/thumbnail.jpg",
            "https://images.outbrain.com/fit-in/200x200/widget.jpg",
            "https://example.com/advert/promo.jpg",
            "https://example.com/adverts/banner.png",
            "https://example.com/leaderboard_728x90.jpg",
            "https://example.com/skyscraper_160x600.jpg",
            "https://example.com/interstitial_ad.jpg",
            "https://googleadservices.com/pagead/imgad?id=789",
        ]
        for ad_url in ad_urls:
            self.assertIsNone(
                self.extractor.validate_and_enhance(ad_url),
                f"Ad URL should be blocked: {ad_url}",
            )

    def test_extract_image_from_html_opengraph(self):
        html = """
        <html>
        <head>
            <meta property="og:image" content="https://example.com/editorial/news_photo_123.jpg" />
        </head>
        <body><article><p>News body</p></article></body>
        </html>
        """
        extracted = extract_image_from_html(html)
        self.assertEqual(extracted, "https://example.com/editorial/news_photo_123.jpg")

    def test_extract_image_from_html_json_ld(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Sample Tamil News",
                "image": [
                    "https://example.com/uploads/photo_large.jpg"
                ]
            }
            </script>
        </head>
        <body><p>Article</p></body>
        </html>
        """
        extracted = extract_image_from_html(html)
        self.assertEqual(extracted, "https://example.com/uploads/photo_large.jpg")

    def test_extract_image_from_html_rejects_negative_og_image(self):
        html = """
        <html>
        <head>
            <meta property="og:image" content="https://example.com/assets/default-logo.png" />
        </head>
        <body><img src="https://example.com/news/real-event-coverage.jpg" /></body>
        </html>
        """
        extracted = extract_image_from_html(html)
        self.assertEqual(extracted, "https://example.com/news/real-event-coverage.jpg")


class TestFeedFetcher(unittest.TestCase):
    """Tests for feed fetching across RSS 2.0, Google News Sitemap, and YouTube Atom."""

    def setUp(self):
        self.fetcher = FeedFetcher()

    def test_raw_article_dataclass_contract(self):
        article = RawArticle(
            source_id="daily_thanthi",
            source_name="தினத்தந்தி",
            source_url="https://www.dailythanthi.com/news/123",
            original_title="முக்கிய செய்தி",
            original_summary="செய்தி சுருக்கம்",
            image_url="https://media.assettype.com/dailythanthi/2026/news.jpg?w=1200&auto=format%2Ccompress&fit=max",
            published_date="2026-11-10T12:00:00+00:00",
            category_hint="tamilnadu",
        )
        self.assertEqual(article.source_id, "daily_thanthi")
        self.assertEqual(article.source_name, "தினத்தந்தி")
        self.assertTrue(article.image_url.startswith("https://"))
        self.assertEqual(article.category_hint, "tamilnadu")

    def test_parse_rss_with_media_content(self):
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <title>Daily Thanthi</title>
                <item>
                    <title>தமிழகத்தில் புதிய திட்டம் தொடக்கம்</title>
                    <link>https://www.dailythanthi.com/news/101</link>
                    <description>முதல்வர் மு.க.ஸ்டாலின் தொடங்கி வைத்தார்.</description>
                    <pubDate>Tue, 10 Nov 2026 10:30:00 GMT</pubDate>
                    <category>தமிழ்நாடு</category>
                    <media:content url="https://media.assettype.com/dailythanthi/2026-11-10/cm_event.jpg" medium="image"/>
                </item>
            </channel>
        </rss>
        """
        cfg = get_source_config("daily_thanthi")
        articles = self.fetcher._parse_rss_content(rss_xml, cfg)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].original_title, "தமிழகத்தில் புதிய திட்டம் தொடக்கம்")
        self.assertEqual(articles[0].source_id, "daily_thanthi")
        self.assertIn("w=1200", articles[0].image_url)
        self.assertEqual(articles[0].category_hint, "tamilnadu")

    def test_parse_rss_with_enclosure(self):
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Thinaboomi</title>
                <item>
                    <title>மதுரையில் பிரம்மாண்ட பொருட்காட்சி</title>
                    <link>https://thinaboomi.com/news/202</link>
                    <description>ஏராளமான மக்கள் வருகை.</description>
                    <pubDate>Tue, 10 Nov 2026 09:15:00 GMT</pubDate>
                    <enclosure url="https://thinaboomi.com/uploads/images/2026/madurai_expo.jpg" length="102400" type="image/jpeg" />
                </item>
            </channel>
        </rss>
        """
        cfg = get_source_config("thinaboomi")
        articles = self.fetcher._parse_rss_content(rss_xml, cfg)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].original_title, "மதுரையில் பிரம்மாண்ட பொருட்காட்சி")
        self.assertEqual(articles[0].image_url, "https://thinaboomi.com/uploads/images/2026/madurai_expo.jpg")

    def test_parse_rss_missing_mandatory_fields_skipped(self):
        # RSS feed items missing title, link, or image must be dropped
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <title>Test Feed</title>
                <!-- Missing title -->
                <item>
                    <title></title>
                    <link>https://example.com/news/1</link>
                    <description>விளக்கம் 1</description>
                    <media:content url="https://media.assettype.com/dailythanthi/photo1.jpg" />
                </item>
                <!-- Missing link -->
                <item>
                    <title>தலைப்பு 2</title>
                    <link></link>
                    <description>விளக்கம் 2</description>
                    <media:content url="https://media.assettype.com/dailythanthi/photo2.jpg" />
                </item>
                <!-- Missing image -->
                <item>
                    <title>தலைப்பு 3</title>
                    <link>https://example.com/news/3</link>
                    <description>விளக்கம் 3</description>
                </item>
                <!-- Valid entry with all mandatory fields -->
                <item>
                    <title>முறையான செய்தி தலைப்பு</title>
                    <link>https://example.com/news/4</link>
                    <description>முழுமையான செய்தி விளக்கம்</description>
                    <media:content url="https://media.assettype.com/dailythanthi/photo4.jpg" />
                </item>
            </channel>
        </rss>
        """
        cfg = get_source_config("daily_thanthi")
        # Disable scraper fallback so entry 3 is not scraped
        articles = self.fetcher._parse_rss_content(rss_xml, cfg, enable_scraper=False)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].original_title, "முறையான செய்தி தலைப்பு")
        self.assertEqual(articles[0].source_url, "https://example.com/news/4")
        self.assertTrue(bool(articles[0].image_url))

    def test_parse_google_news_sitemap(self):
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
                xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
            <url>
                <loc>https://www.dinamalar.com/news/tamil-nadu-news/chennai-metro-expansion/4372635</loc>
                <news:news>
                    <news:publication>
                        <news:name>Dinamalar</news:name>
                        <news:language>ta</news:language>
                    </news:publication>
                    <news:publication_date>2026-11-10T14:30:00+05:30</news:publication_date>
                    <news:title>சென்னை மெட்ரோ ரயில் புதிய வழித்தடம் திறப்பு</news:title>
                </news:news>
                <image:image>
                    <image:loc>https://images.dinamalar.com/data/large_2025/metro_rail_lrg_4372635.jpg</image:loc>
                </image:image>
            </url>
        </urlset>
        """
        cfg = get_source_config("dinamalar")
        with patch.object(self.fetcher, "_http_get") as mock_http:
            mock_resp = MagicMock()
            mock_resp.content = sitemap_xml.encode("utf-8")
            mock_http.return_value = mock_resp

            articles = self.fetcher._fetch_sitemap(cfg)
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].original_title, "சென்னை மெட்ரோ ரயில் புதிய வழித்தடம் திறப்பு")
            self.assertEqual(articles[0].image_url, "https://images.dinamalar.com/data/large_2025/metro_rail_lrg_4372635.jpg")
            self.assertEqual(articles[0].source_id, "dinamalar")

    def test_parse_google_news_sitemap_with_image_title(self):
        # Dinamalar live sitemap XML structure: missing news:news tag, title in image:title
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
            <url>
                <loc>https://www.dinamalar.com/news/latest-tamil-news/chief-minister-visit/4372635</loc>
                <lastmod>2026-11-10T20:18:00+05:30</lastmod>
                <image:image>
                    <image:loc>https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg</image:loc>
                    <image:title>நவம்பர் 20ல் திருச்சி செல்கிறார் முதல்வர் விஜய்; நலத்திட்ட உதவிகள் வழங்க திட்டம்</image:title>
                </image:image>
            </url>
        </urlset>
        """
        cfg = get_source_config("dinamalar")
        with patch.object(self.fetcher, "_http_get") as mock_http:
            mock_resp = MagicMock()
            mock_resp.content = sitemap_xml.encode("utf-8")
            mock_http.return_value = mock_resp

            articles = self.fetcher._fetch_sitemap(cfg)
            self.assertEqual(len(articles), 1)
            self.assertEqual(
                articles[0].original_title,
                "நவம்பர் 20ல் திருச்சி செல்கிறார் முதல்வர் விஜய்; நலத்திட்ட உதவிகள் வழங்க திட்டம்",
            )
            self.assertEqual(
                articles[0].image_url,
                "https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg",
            )
            self.assertEqual(articles[0].source_id, "dinamalar")
            self.assertIn("2026-11-10", articles[0].published_date)

    def test_parse_youtube_atom_feed(self):
        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:yt="http://www.youtube.com/xml/schemas/2015"
              xmlns:media="http://search.yahoo.com/mrss/">
            <entry>
                <id>yt:video:b_H_L23uG-M</id>
                <title>தங்கம் விலை அதிரடி சரிவு | Gold Rate Today</title>
                <link rel="alternate" href="https://www.youtube.com/watch?v=b_H_L23uG-M"/>
                <published>2026-11-10T11:00:00+00:00</published>
                <media:group>
                    <media:title>தங்கம் விலை அதிரடி சரிவு</media:title>
                    <media:thumbnail url="https://i.ytimg.com/vi/b_H_L23uG-M/hqdefault.jpg" width="480" height="360"/>
                    <media:description>இன்றைய தங்கம் மற்றும் வெள்ளி விலை நிலவரம்.</media:description>
                </media:group>
            </entry>
        </feed>
        """.encode("utf-8")
        cfg = get_source_config("zee_news_tamil")
        articles = self.fetcher._parse_youtube_atom(atom_xml, cfg)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].original_title, "தங்கம் விலை அதிரடி சரிவு | Gold Rate Today")
        # Ensure upgraded to maxresdefault.jpg
        self.assertEqual(articles[0].image_url, "https://i.ytimg.com/vi/b_H_L23uG-M/maxresdefault.jpg")

    def test_fetcher_retries_on_500(self):
        cfg = get_source_config("daily_thanthi")
        with patch.object(self.fetcher.session, "get") as mock_get:
            error_resp = MagicMock()
            error_resp.status_code = 500
            ok_resp = MagicMock()
            ok_resp.status_code = 200
            ok_resp.text = """<rss version="2.0"><channel></channel></rss>"""
            mock_get.side_effect = [error_resp, ok_resp]

            resp = self.fetcher._http_get("https://example.com/test")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(mock_get.call_count, 2)


class TestDeduplicator(unittest.TestCase):
    """Tests for URL normalization, SHA-256 caching, persistence, and batch filtering."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "seen_articles.json")
        self.dedup = Deduplicator(filepath=self.cache_file, max_entries=10)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_url_normalization(self):
        url1 = "https://www.DailyThanthi.com/news/article-123/?utm_source=rss&utm_medium=feed&ref=home"
        url2 = "https://www.dailythanthi.com/news/article-123"
        self.assertEqual(normalize_url(url1), normalize_url(url2))

    def test_title_normalization(self):
        t1 = "முக்கிய செய்தி அறிக்கை - தினத்தந்தி"
        t2 = "முக்கிய செய்தி அறிக்கை"
        self.assertEqual(normalize_title(t1), normalize_title(t2))

    def test_is_seen_and_mark_seen(self):
        article_url = "https://example.com/news/chennai-rains-2026"
        self.assertFalse(self.dedup.is_seen(article_url))

        h = self.dedup.mark_seen(article_url)
        self.assertTrue(self.dedup.is_seen(article_url))
        self.assertTrue(self.dedup.is_seen(h))

    def test_persistence_across_instances(self):
        url = "https://example.com/news/peristed-story"
        self.dedup.mark_seen(url, metadata={"title": "Peristed Story"})

        # New deduplicator instance reading same file
        new_dedup = Deduplicator(filepath=self.cache_file)
        self.assertTrue(new_dedup.is_seen(url))
        self.assertEqual(new_dedup.count(), 1)

    def test_filter_unseen(self):
        a1 = RawArticle(
            source_id="s1",
            source_name="விகடன்",
            source_url="https://vikatan.com/story1",
            original_title="Story 1",
            original_summary="",
            image_url="https://example.com/img1.jpg",
            published_date="2026-11-10T10:00:00Z",
            category_hint="politics",
        )
        a2 = RawArticle(
            source_id="s1",
            source_name="விகடன்",
            source_url="https://vikatan.com/story2",
            original_title="Story 2",
            original_summary="",
            image_url="https://example.com/img2.jpg",
            published_date="2026-11-10T10:00:00Z",
            category_hint="politics",
        )

        self.dedup.mark_seen(a1)
        unseen = self.dedup.filter_unseen([a1, a2, a2])
        self.assertEqual(len(unseen), 1)
        self.assertEqual(unseen[0].source_url, "https://vikatan.com/story2")

    def test_corrupt_cache_file_recovery(self):
        # Write corrupted JSON to cache file
        with open(self.cache_file, "w") as f:
            f.write("{corrupt: json content[")
        reloaded = Deduplicator(filepath=self.cache_file)
        self.assertEqual(reloaded.count(), 0)
        # Should be able to mark seen and save without error
        reloaded.mark_seen("https://example.com/new-story")
        self.assertEqual(reloaded.count(), 1)

    def test_batch_internal_duplicates_filtered(self):
        a1 = RawArticle(
            source_id="s1",
            source_name="விகடன்",
            source_url="https://vikatan.com/story-same",
            original_title="Same Story",
            original_summary="",
            image_url="https://example.com/img1.jpg",
            published_date="2026-11-10T10:00:00Z",
            category_hint="politics",
        )
        unseen = self.dedup.filter_unseen([a1, a1, a1])
        self.assertEqual(len(unseen), 1)

    def test_cache_pruning(self):
        for i in range(15):
            self.dedup.mark_seen(f"https://example.com/story_{i}")
        self.assertLessEqual(self.dedup.count(), 10)

    def test_concurrent_mark_seen_thread_safety(self):
        import threading
        errors = []

        def worker(thread_idx):
            try:
                for i in range(25):
                    self.dedup.mark_seen(f"https://example.com/worker/{thread_idx}/item_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent mark_seen produced errors: {errors}")
        self.assertLessEqual(self.dedup.count(), 10)
        # Verify file is valid JSON and readable
        with open(self.cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("hashes", data)
            self.assertEqual(len(data["hashes"]), self.dedup.count())

    def test_concurrent_mark_seen_high_capacity(self):
        import threading
        cache_path = os.path.join(self.temp_dir.name, "concurrent_seen.json")
        dedup = Deduplicator(filepath=cache_path, max_entries=500)
        errors = []

        def worker(thread_idx):
            try:
                for i in range(20):
                    dedup.mark_seen(f"https://example.com/w/{thread_idx}/{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent mark_seen produced errors: {errors}")
        self.assertEqual(dedup.count(), 200)
        # Verify persistence reload
        reloaded = Deduplicator(filepath=cache_path, max_entries=500)
        self.assertEqual(reloaded.count(), 200)


class TestAggregatorEndToEnd(unittest.TestCase):
    """Integration test verifying end-to-end simulated aggregation pipeline."""

    def test_simulated_pipeline_flow(self):
        raw_feed = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <title>Hindu Tamil Thisai</title>
                <item>
                    <title>இலக்கிய திருவிழா கோலாகல தொடக்கம்</title>
                    <link>https://www.hindutamil.in/news/tamil-nadu/lit-fest-2026.html?utm_source=rss</link>
                    <description>சென்னையில் சர்வதேச இலக்கிய திருவிழா தொடங்கியது.</description>
                    <pubDate>Tue, 10 Nov 2026 12:00:00 GMT</pubDate>
                    <category>சென்னை</category>
                    <media:content url="https://cf-images.assettype.com/hindutamil-prod/2026/lit.jpg" medium="image"/>
                </item>
                <item>
                    <title>விளம்பர செய்தி (No Real Image)</title>
                    <link>https://www.hindutamil.in/sponsored/ad1</link>
                    <description>Promo</description>
                    <pubDate>Tue, 10 Nov 2026 12:05:00 GMT</pubDate>
                    <media:content url="https://example.com/ad-banner.jpg"/>
                </item>
            </channel>
        </rss>
        """
        fetcher = FeedFetcher()
        cfg = get_source_config("hindu_tamil")
        articles = fetcher._parse_rss_content(raw_feed, cfg, enable_scraper=False)

        # 1. Image negative filter should reject second item (ad-banner.jpg)
        self.assertEqual(len(articles), 1)
        art = articles[0]

        # 2. Real image should be enhanced with 1200px width
        self.assertIn("w=1200", art.image_url)
        self.assertEqual(art.source_id, "hindu_tamil")
        self.assertEqual(art.category_hint, "tamilnadu")

        # 3. Deduplication pipeline
        with tempfile.TemporaryDirectory() as tmp_dir:
            dedup = Deduplicator(filepath=os.path.join(tmp_dir, "seen.json"))
            self.assertFalse(dedup.is_seen(art))

            unseen = dedup.filter_unseen([art])
            self.assertEqual(len(unseen), 1)

            dedup.mark_seen(art)
            self.assertTrue(dedup.is_seen(art))

            unseen_again = dedup.filter_unseen([art])
            self.assertEqual(len(unseen_again), 0)


if __name__ == "__main__":
    unittest.main()
