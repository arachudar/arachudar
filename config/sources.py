"""
config/sources.py - Configuration for all 15 Tamil news sources, feed endpoints,
image extraction rules, and category taxonomies for the Arachudar pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Default HTTP Configuration
# ---------------------------------------------------------------------------
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Arachudar Category Taxonomy & Mapping
# ---------------------------------------------------------------------------
VALID_CATEGORIES = [
    "tamilnadu",
    "national",
    "world",
    "politics",
    "business",
    "cinema",
    "sports",
    "tech",
    "spiritual",
    "epaper",
]

VALID_SUBCATEGORIES = {
    "tamilnadu": ["chennai", "madurai", "coimbatore", "trichy", "south"],
    "cinema": ["news", "reviews", "ott"],
    "sports": ["cricket", "football", "tennis"],
}

CATEGORY_KEYWORDS_MAP = {
    # Tamil Nadu & Regional Districts
    "tamilnadu": [
        "தமிழ்நாடு", "தமிழகம்", "சென்னை", "மதுரை", "கோவை", "கோயம்புத்தூர்",
        "திருச்சி", "தஞ்சாவூர்", "நெல்லை", "தூத்துக்குடி", "கன்னியாகுமரி",
        "சேலம்", "ஈரோடு", "திருப்பூர்", "வேலூர்", "திண்டுக்கல்",
        "tamilnadu", "tamil-nadu", "chennai", "district", "local"
    ],
    # National
    "national": [
        "இந்தியா", "தேசியம்", "தேசிய", "தில்லி", "டெல்லி", "மத்திய",
        "national", "india", "nation", "delhi"
    ],
    # World
    "world": [
        "உலகம்", "சர்வதேசம்", "சர்வதேச", "அமெரிக்கா", "அமெரிக்க", "இலங்கை", "பிரிட்டன்",
        "world", "international", "global", "foreign"
    ],
    # Politics
    "politics": [
        "அரசியல்", "தேர்தல்", "திமுக", "அதிமுக", "பாஜக", "காங்கிரஸ்", "தவெக",
        "சட்டமன்றம்", "நாடாளுமன்றம்", "politics", "political", "election"
    ],
    # Business & Economy
    "business": [
        "வணிகம்", "பொருளாதாரம்", "பங்குச்சந்தை", "தங்கம்", "தங்க", "வெள்ளி", "பட்ஜெட்",
        "ரூபாய்", "ரிசர்வ் வங்கி", "business", "market", "gold", "economy", "finance"
    ],
    # Cinema & Entertainment
    "cinema": [
        "சினிமா", "திரைப்படம்", "விமர்சனம்", "நடிகர்", "நடிகை", "இயக்குனர்",
        "ஓடிடி", "பாடல்", "டிரெய்லர்", "cinema", "entertainment", "movie", "kollywood", "ott"
    ],
    # Sports
    "sports": [
        "விளையாட்டு", "கிரிக்கெட்", "ஐபிஎல்", "கால்பந்து", "டென்னிஸ்", "ஹாக்கி",
        "sports", "cricket", "ipl", "football", "tennis", "hockey"
    ],
    # Technology & Auto
    "tech": [
        "தொழில்நுட்பம்", "ஸ்மார்ட்போன்", "செயற்கை நுண்ணறிவு", "ஏஐ", "ஆப்",
        "tech", "technology", "mobile", "gadgets", "ai", "auto", "automobile"
    ],
    # Spiritual & Astrology
    "spiritual": [
        "ஆன்மிகம்", "கோவில்", "கோயில்", "திருக்கோயில்", "திருக்கோவில்", "ராசிபலன்", "ஜோதிடம்", "விரதம்", "பக்தி",
        "spiritual", "astrology", "horoscope", "devotional", "temple"
    ],
    # E-Paper
    "epaper": [
        "இ-பேப்பர்", "நாளிதழ் பதிப்பு", "epaper", "e-paper"
    ],
}

SUBCATEGORY_KEYWORDS_MAP = {
    # District subcategories for tamilnadu
    "chennai": ["சென்னை", "chennai", "madras"],
    "madurai": ["மதுரை", "madurai", "தேனி", "திண்டுக்கல்"],
    "coimbatore": ["கோவை", "கோயம்புத்தூர்", "coimbatore", "திருப்பூர்", "ஈரோடு"],
    "trichy": ["திருச்சி", "trichy", "தஞ்சாவூர்", "டெல்டா", "நாகப்பட்டினம்"],
    "south": ["நெல்லை", "தூத்துக்குடி", "கன்னியாகுமரி", "தென்காசி", "விருதுநகர்", "தென்"],
    # Cinema subcategories
    "reviews": ["விமர்சனம்", "review", "திரைவிமர்சனம்"],
    "ott": ["ஓடிடி", "ott", "ஸ்ட்ரீமிங்", "streaming", "netflix", "prime"],
    "news": ["செய்திகள்", "news", "படப்பிடிப்பு", "ஷூட்டிங்"],
    # Sports subcategories
    "cricket": ["கிரிக்கெட்", "cricket", "ipl", "டி20", "டெஸ்ட்"],
    "football": ["கால்பந்து", "football", "soccer", "பிஃபா", "fifa"],
    "tennis": ["டென்னிஸ்", "tennis", "விம்பிள்டன்"],
}


# ---------------------------------------------------------------------------
# Source Configuration Data Model
# ---------------------------------------------------------------------------
@dataclass
class SourceConfig:
    id: str
    name: str
    tamil_name: str
    type: str  # 'rss', 'google_news_sitemap', 'rss_multi', 'proxy_fallback', 'google_news_topics', 'directory_catalog'
    image_extractor: str  # 'media_content', 'sitemap_image_loc', 'enclosure', 'bbc_thumbnail_upgrade', etc.
    default_category: str = "tamilnadu"
    feed_url: Optional[str] = None
    feeds: Optional[Dict[str, str]] = None
    sitemap_fallback: Optional[str] = None
    youtube_feed: Optional[str] = None
    google_search_proxy: Optional[str] = None
    directory_url: Optional[str] = None
    role: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=lambda: {"User-Agent": DEFAULT_USER_AGENT})
    timeout: int = DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Master 15 Tamil News Sources Dictionary
# ---------------------------------------------------------------------------
TAMIL_NEWS_SOURCES: Dict[str, Dict[str, Any]] = {
    # 1. Daily Thanthi
    "daily_thanthi": {
        "id": "daily_thanthi",
        "name": "Daily Thanthi",
        "tamil_name": "தினத்தந்தி",
        "feed_url": "https://www.dailythanthi.com/stories.rss",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 2. Dinamalar
    "dinamalar": {
        "id": "dinamalar",
        "name": "Dinamalar",
        "tamil_name": "தினமலர்",
        "feed_url": "https://www.dinamalar.com/sitemap_latest.xml",
        "sitemap_images": "https://www.dinamalar.com/sitemap_images.xml",
        "type": "google_news_sitemap",
        "image_extractor": "sitemap_image_loc",
        "default_category": "tamilnadu",
    },
    # 3. Hindu Tamil Thisai
    "hindu_tamil": {
        "id": "hindu_tamil",
        "name": "Hindu Tamil Thisai",
        "tamil_name": "இந்து தமிழ் திசை",
        "feed_url": "https://www.hindutamil.in/stories.rss",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 4. Dinamani
    "dinamani": {
        "id": "dinamani",
        "name": "Dinamani",
        "tamil_name": "தினமணி",
        "feed_url": "https://www.dinamani.com/stories.rss",
        "sitemap_fallback": "https://www.dinamani.com/news_sitemap.xml",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 5. Maalai Malar
    "maalai_malar": {
        "id": "maalai_malar",
        "name": "Maalai Malar",
        "tamil_name": "மாலை மலர்",
        "feed_url": "https://www.maalaimalar.com/stories.rss",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 6. Thinaboomi
    "thinaboomi": {
        "id": "thinaboomi",
        "name": "Thinaboomi",
        "tamil_name": "தினபூமி",
        "feed_url": "https://thinaboomi.com/rss/latest-posts",
        "fallback_feed": "https://thinaboomi.com/rss/category/news",
        "type": "rss",
        "image_extractor": "enclosure",
        "default_category": "tamilnadu",
    },
    # 7. Vikatan
    "vikatan": {
        "id": "vikatan",
        "name": "Vikatan",
        "tamil_name": "விகடன்",
        "feed_url": "https://www.vikatan.com/stories.rss",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "politics",
    },
    # 8. Samayam Tamil
    "samayam_tamil": {
        "id": "samayam_tamil",
        "name": "Samayam Tamil",
        "tamil_name": "சமயம் தமிழ்",
        "feed_url": "https://tamil.samayam.com/sitemap/rssfeed.xml",
        "sitemap_fast": "https://tamil.samayam.com/staticsitemap/tamil/news/sitemap-48hours.xml",
        "type": "rss",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 9. Oneindia Tamil
    "oneindia_tamil": {
        "id": "oneindia_tamil",
        "name": "Oneindia Tamil",
        "tamil_name": "ஒன்இந்தியா தமிழ்",
        "feeds": {
            "news": "https://tamil.oneindia.com/rss/feeds/tamil-news-fb.xml",
            "cinema": "https://tamil.oneindia.com/rss/feeds/tamil-cinema-fb.xml",
            "tech": "https://tamil.oneindia.com/rss/feeds/tamil-technology-fb.xml",
            "spiritual": "https://tamil.oneindia.com/rss/feeds/tamil-spirtuality-fb.xml",
        },
        "type": "rss_multi",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 10. BBC News Tamil
    "bbc_tamil": {
        "id": "bbc_tamil",
        "name": "BBC News Tamil",
        "tamil_name": "பிபிசி தமிழ்",
        "feed_url": "https://feeds.bbci.co.uk/tamil/rss.xml",
        "type": "rss",
        "image_extractor": "bbc_thumbnail_upgrade",
        "default_category": "world",
    },
    # 11. News18 Tamil
    "news18_tamil": {
        "id": "news18_tamil",
        "name": "News18 Tamil",
        "tamil_name": "நியூஸ்18 தமிழ்நாடு",
        "feeds": {
            "tamilnadu": "https://tamil.news18.com/commonfeeds/v1/tam/rss/tamil-nadu.xml",
            "national": "https://tamil.news18.com/commonfeeds/v1/tam/rss/national.xml",
            "cinema": "https://tamil.news18.com/commonfeeds/v1/tam/rss/cinema.xml",
            "sports": "https://tamil.news18.com/commonfeeds/v1/tam/rss/sports.xml",
            "business": "https://tamil.news18.com/commonfeeds/v1/tam/rss/business.xml",
            "lifestyle": "https://tamil.news18.com/commonfeeds/v1/tam/rss/lifestyle.xml",
        },
        "type": "rss_multi",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 12. Zee News Tamil
    "zee_news_tamil": {
        "id": "zee_news_tamil",
        "name": "Zee News Tamil",
        "tamil_name": "ஜீ நியூஸ் தமிழ்",
        "youtube_feed": "https://www.youtube.com/feeds/videos.xml?channel_id=UCxRRfF6qIoYntp3zNOozonQ",
        "google_search_proxy": "https://news.google.com/rss/search?q=Zee+Tamil+News&hl=ta&gl=IN&ceid=IN:ta",
        "type": "proxy_fallback",
        "image_extractor": "yt_or_google_thumbnail",
        "default_category": "tamilnadu",
    },
    # 13. Asianet News Tamil
    "asianet_tamil": {
        "id": "asianet_tamil",
        "name": "Asianet News Tamil",
        "tamil_name": "ஏசியாநெட் நியூஸ் தமிழ்",
        "feeds": {
            "all": "https://tamil.asianetnews.com/rss",
            "cinema": "https://tamil.asianetnews.com/rss/cinema",
            "sports": "https://tamil.asianetnews.com/rss/sports",
            "national": "https://tamil.asianetnews.com/rss/india",
            "business": "https://tamil.asianetnews.com/rss/business",
            "tech": "https://tamil.asianetnews.com/rss/technology",
        },
        "type": "rss_multi",
        "image_extractor": "media_content",
        "default_category": "tamilnadu",
    },
    # 14. Google News Tamil
    "google_news_tamil": {
        "id": "google_news_tamil",
        "name": "Google News Tamil",
        "tamil_name": "கூகுள் செய்திகள் தமிழ்",
        "feeds": {
            "home": "https://news.google.com/rss?hl=ta&gl=IN&ceid=IN:ta",
            "national": "https://news.google.com/rss/headlines/section/topic/NATION?hl=ta&gl=IN&ceid=IN:ta",
            "world": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ta&gl=IN&ceid=IN:ta",
            "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ta&gl=IN&ceid=IN:ta",
            "tech": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ta&gl=IN&ceid=IN:ta",
            "cinema": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ta&gl=IN&ceid=IN:ta",
            "sports": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ta&gl=IN&ceid=IN:ta",
            "tamilnadu_search": "https://news.google.com/rss/search?q=தமிழ்நாடு&hl=ta&gl=IN&ceid=IN:ta",
        },
        "type": "google_news_topics",
        "image_extractor": "og_image_or_google_cdn",
        "default_category": "tamilnadu",
    },
    # 15. W3Newspapers Tamil Directory
    "w3newspapers_directory": {
        "id": "w3newspapers_directory",
        "name": "W3Newspapers Tamil Directory",
        "tamil_name": "டபிள்யு3 தமிழ் செய்தித்தாள்கள்",
        "directory_url": "https://www.w3newspapers.com/india/tamil/",
        "type": "directory_catalog",
        "image_extractor": "none",
        "default_category": "tamilnadu",
        "role": "Source discovery, newspaper metadata, and feed health check index",
    },
}


def get_source_config(source_id: str) -> Optional[SourceConfig]:
    """Retrieve typed SourceConfig dataclass for a given source_id."""
    raw = TAMIL_NEWS_SOURCES.get(source_id)
    if not raw:
        return None
    return SourceConfig(
        id=raw.get("id", source_id),
        name=raw["name"],
        tamil_name=raw.get("tamil_name", raw["name"]),
        type=raw["type"],
        image_extractor=raw.get("image_extractor", "media_content"),
        default_category=raw.get("default_category", "tamilnadu"),
        feed_url=raw.get("feed_url"),
        feeds=raw.get("feeds"),
        sitemap_fallback=raw.get("sitemap_fallback"),
        youtube_feed=raw.get("youtube_feed"),
        google_search_proxy=raw.get("google_search_proxy"),
        directory_url=raw.get("directory_url"),
        role=raw.get("role"),
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
    )


def map_category(hint_or_text: str, default: str = "tamilnadu") -> str:
    """
    Map an incoming category hint, section name, or Tamil text to
    one of the 10 canonical Arachudar categories.
    Prioritizes specific domain categories before broad district keywords in tamilnadu.
    """
    if not hint_or_text:
        return default

    clean_text = hint_or_text.lower().strip()

    # Direct match against valid categories
    if clean_text in VALID_CATEGORIES:
        return clean_text

    # Prioritize specific domain categories before broad district keywords in tamilnadu
    category_order = [
        "sports",
        "cinema",
        "business",
        "spiritual",
        "tech",
        "world",
        "national",
        "politics",
        "epaper",
        "tamilnadu",
    ]
    for cat in CATEGORY_KEYWORDS_MAP:
        if cat not in category_order:
            category_order.append(cat)

    # Match against keyword dictionary in prioritized order
    for category in category_order:
        keywords = CATEGORY_KEYWORDS_MAP.get(category, [])
        for kw in keywords:
            if kw.lower() in clean_text:
                return category

    return default


def map_subcategory(category: str, hint_or_text: str) -> Optional[str]:
    """
    Map an incoming text/hint to an allowable subcategory for the given category.
    """
    if not hint_or_text or category not in VALID_SUBCATEGORIES:
        return None

    clean_text = hint_or_text.lower().strip()
    allowable = VALID_SUBCATEGORIES[category]

    for subcat in allowable:
        if subcat in clean_text:
            return subcat

    for subcat, keywords in SUBCATEGORY_KEYWORDS_MAP.items():
        if subcat in allowable:
            for kw in keywords:
                if kw.lower() in clean_text:
                    return subcat

    return None
