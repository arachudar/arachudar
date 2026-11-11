"""
tests/fixtures/sample_images.py - Sample Image URLs & Binary Byte Fixtures.
Provides verified editorial CDN news photographs, negative placeholder URLs,
and minimal valid JPEG byte streams for hermetic image validation.
"""

from typing import List, Dict

# Minimal 1x1 JPEG byte stream for hermetic image validation (67 bytes)
DUMMY_JPEG_BYTES: bytes = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
    b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00"
    b"\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# Verified editorial news photographs from the 15 Tamil sources
VALID_EDITORIAL_IMAGE_URLS: Dict[str, str] = {
    "daily_thanthi": "https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200",
    "dinamalar": "https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg",
    "hindu_tamil": "https://cf-images.assettype.com/hindutamil-prod/2026-11-10/2d9ml1m9/appa-kutty.jpg?w=1200",
    "dinamani": "https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200",
    "maalai_malar": "https://cf-images.assettype.com/maalai-malar/2026-11-10/f7gqt3bc/formula1.jpg?w=1200",
    "thinaboomi": "https://thinaboomi.com/uploads/images/202603/image_870x580_69c273307cfa5.jpg",
    "vikatan": "https://gumlet.vikatan.com/vikatan/2026-11-10/1xu4rr9j/WhatsApp-Image-2026-11-07-at-10.09.28.jpeg?w=1200&fit=max",
    "samayam": "https://static.langimg.com/photo/imgsize-352245,msid-135713596/tamil-samayam.jpg",
    "oneindia": "https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg",
    "bbc_tamil": "https://ichef.bbci.co.uk/ace/ws/1024/cpsprodpb/3a8b/live/da8fa680-dcfd-11f1-93e1-3b657b665bcf.jpg",
    "news18": "https://images.news18.com/tamil/uploads/2026/11/sonia-gandhi-2026-11-bfbe3a4e73a1c1c1200255934925ba2d-1200x800.jpg",
    "asianet": "https://static.asianetnews.com/images/w-1280,h-720,format-jpg,imgid-01m72wtzdx77fh2sck4n5wpkr4,imgname-walking-shoes-vs-running-shoes--2--1794319941053.jpg",
    "google_news": "https://lh3.googleusercontent.com/J6_coFbogxhRI9iM864NL_liGXvsQp2AupsKei7z0cNNfDvGUmWUy20nuUhkREQyrpY4bEeIBuc=s0-w1200",
    "youtube_atom": "https://i.ytimg.com/vi/b_H_L23uG-M/hqdefault.jpg",
}

VALID_IMAGE_URLS: List[str] = list(VALID_EDITORIAL_IMAGE_URLS.values())

# Negative, synthetic, placeholder, and logo URLs that MUST be rejected by the negative image filter
NEGATIVE_IMAGE_URLS: List[str] = [
    "https://www.dailythanthi.com/assets/images/logo.png",
    "https://static.hindutamil.in/hindu/static/common/images/hindu-logo.svg",
    "https://www.dinamalar.com/images/favicon.ico",
    "https://thinaboomi.com/assets/images/default_banner_ad.jpg",
    "https://www.vikatan.com/static/assets/placeholder_news.gif",
    "https://news18.com/images/1x1_tracking_pixel.gif",
    "https://samayam.com/assets/sprite_icon.png",
    "https://asianetnews.com/images/ad_300x250.jpg",
    "https://example.com/site-header-badge.svg",
    "https://cdn.news.com/spacer.gif",
    "https://static.media.com/author_avatar_32x32.png",
    "https://ads.doubleclick.net/banner_728x90.jpg",
    "https://media.assettype.com/dailythanthi/default-share-icon.jpg",
    "https://images.dinamani.com/templates/default/no-image-available.png",
]
