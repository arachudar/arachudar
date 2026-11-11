"""
scripts/populate_live_news.py - Live Tamil News Synthesizer and Publisher.
Fetches today's live Tamil news across 15 sources, extracts real editorial images,
synthesizes articles topic-by-topic using NVIDIA NIM AI (<= 30 RPM),
updates tamil-news-blogger.html and blogger-theme.xml, and publishes to Blogger.
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.aggregator.feed_fetcher import fetch_all_sources, RawArticle
from src.ai.rate_limiter import TokenBucketRateLimiter
from src.ai.nvidia_client import NvidiaClient
from src.ai.tamil_synthesizer import TamilSynthesizer, ProcessedArticle
from src.publisher.blogger_client import BloggerClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("populate_live_news")

SLOT_MAPPING = [
    (1, "tamilnadu", "chennai", ["துவரம் பருப்பு", "உளுந்து", "இருப்பு", "விலைவாசி", "பொருட்கள்"]),
    (2, "tamilnadu", "districts", ["டாஸ்மாக்", "பணியிட மாற்றம்", "விதிகள்", "அரசு", "தொழிலாளர்கள்"]),
    (3, "national", "delhi", ["சோனியா காந்தி", "புற்றுநோய்", "நினைவுக்குறிப்பு", "போராட்டம்", "தில்லி"]),
    (4, "business", "market", ["போஸ்ட் ஆபீஸ்", "முதலீடு", "வட்டி", "சேமிப்பு", "தங்கம்", "பங்குச்சந்தை"]),
    (5, "tech", "science", ["ககன்யான்", "கோவையில்", "இஸ்ரோ", "பாதுகாப்பு சாதனம்", "விண்கலம்"]),
    (6, "cinema", "kollywood", ["அமலா ஷாஜி", "நடிகை", "பவன் கல்யாண்", "திரைப்படம்", "சினிமா"]),
    (7, "sports", "cricket", ["தந்தையின் வழியில்", "மகுடம்", "டாப் 5", "சுடு தண்ணி", "விளையாட்டு"]),
    (8, "tamilnadu", "trichy", ["தீபாவளி", "முதல்வர் விஜய்", "ஆலோசனை", "திருச்சி", "அரசியல்"]),
    (9, "world", "global", ["அமெரிக்க ராணுவ வீரர்", "லண்டனில் கைது", "ரஷ்யா", "உளவு", "சர்வதேசம்"]),
    (10, "politics", "karnataka", ["கர்நாடக அரசு", "விளம்பரம்", "ரூ. 473 கோடி", "பாஜக", "காங்கிரஸ்"]),
    (11, "spiritual", "astrology", ["இன்றைய ராசிபலன்", "நவம்பர் 11", "மேஷம்", "ஜோதிட", "ராசி"]),
    (12, "chennai", "transport", ["பொங்கல் ரெயில்", "டிக்கெட் முன்பதிவு", "பயணிகள்", "ரயில்வே", "சென்னை"])
]


def is_valid_real_image(url: str) -> bool:
    """Rejects placeholder, dummy, logo, and unsplash URLs."""
    if not url or not url.startswith("https://"):
        return False
    u = url.lower()
    bad_substrings = ["unsplash", "logo", "icon", "placeholder", "dummy", "avatar", "default", "blank"]
    return not any(b in u for b in bad_substrings)


def run_topic_synthesis(publish_blogger: bool = True):
    logger.info("================================================================")
    logger.info("   அறச்சுடர் - இன்றைய நேரலை செய்திகள் திரட்டுதல் மற்றும் தொகுத்தல்")
    logger.info("================================================================")

    # 1. Fetch live articles from sources
    logger.info("1. 15 தமிழ் ஊடகங்களில் இருந்து இன்றைய செய்திகளைத் திரட்டுகிறது...")
    raws = fetch_all_sources(limit_per_source=5)
    candidates = [r for r in raws if is_valid_real_image(r.image_url)]
    logger.info(f"திரட்டப்பட்ட மொத்த செய்திகள்: {len(raws)}, உண்மைப் புகைப்படங்கள் கொண்டவை: {len(candidates)}")

    # 2. Match candidates to slots
    used_titles = set()
    selected_slots: List[Dict[str, Any]] = []

    for slot_id, cat, sub, kws in SLOT_MAPPING:
        matched = None
        for cand in candidates:
            if cand.original_title in used_titles:
                continue
            t_lower = cand.original_title.lower()
            if any(kw in t_lower for kw in kws):
                matched = cand
                break
        if not matched:
            for cand in candidates:
                if cand.original_title in used_titles:
                    continue
                if (cand.category_hint or "") == cat:
                    matched = cand
                    break
        if not matched:
            for cand in candidates:
                if cand.original_title not in used_titles:
                    matched = cand
                    break
        if matched:
            used_titles.add(matched.original_title)
            selected_slots.append({
                "slot_id": slot_id,
                "category": cat,
                "sub_category": sub,
                "raw": matched
            })
            logger.info(f"Slot {slot_id:2d} [{cat:10s}]: [{matched.source_name}] {matched.original_title[:50]}...")

    # 3. Initialize NVIDIA client & TamilSynthesizer
    logger.info("2. NVIDIA NIM AI (nvidia/nemotron-3.5-bolt-e4b) மூலம் தமிழ் கட்டுரைகளை உருவாக்குகிறது...")
    rate_limiter = TokenBucketRateLimiter(rate_rpm=28.0, capacity=3.0)
    client = NvidiaClient(rate_limiter=rate_limiter)
    synthesizer = TamilSynthesizer(nvidia_client=client)

    processed_articles: List[ProcessedArticle] = []

    for item in selected_slots:
        slot_id = item["slot_id"]
        cat = item["category"]
        sub = item["sub_category"]
        raw = item["raw"]

        logger.info(f"செய்தி தொகுப்பு [{slot_id}/12 - {cat}]: {raw.original_title[:45]}...")
        try:
            processed = synthesizer.synthesize(raw, article_id=slot_id)
            processed.category = cat
            processed.sub_category = sub
            processed_articles.append(processed)
            logger.info(f"   -> தலைப்பு: {processed.title[:50]}")
        except Exception as exc:
            logger.error(f"Slot {slot_id} synthesis failed: {exc}")
            raise

    # 4. Build EPAPER_PAGES_CONTENT
    logger.info("3. இ-பேப்பர் 4 பக்கங்களுக்கான தரவுகளைத் தயார் செய்கிறது...")
    epaper_pages = {
        1: {
            "title": "முதன்மைப் பக்கம் (Front Page Headlines)",
            "leadHeadline": processed_articles[0].title,
            "leadSubhead": processed_articles[0].summary,
            "leadByline": f"அறச்சுடர் சிறப்பு நிருபர் • 11 நவம்பர் 2026",
            "leadPhoto": processed_articles[0].image,
            "leadCaption": f"{processed_articles[0].title} - கள நிலவரப் படம்.",
            "leadBody": processed_articles[0].body,
            "sideHeadline": processed_articles[3].title,
            "sideSummary": processed_articles[3].summary,
            "metroHeadline": processed_articles[1].title,
            "metroSummary": processed_articles[1].summary,
            "waterHeadline": processed_articles[7].title,
            "waterSummary": processed_articles[7].summary
        },
        2: {
            "title": "தமிழ்நாடு & மண்டலச் செய்திகள் (State & Regional)",
            "leadHeadline": processed_articles[1].title,
            "leadSubhead": processed_articles[1].summary,
            "leadByline": f"மண்டல நிருபர் குழு • 11 நவம்பர் 2026",
            "leadPhoto": processed_articles[1].image,
            "leadCaption": f"தமிழக அரசு நிர்வாக நடவடிக்கைகள் தொடர்பான காட்சி.",
            "leadBody": processed_articles[1].body,
            "sideHeadline": processed_articles[7].title,
            "sideSummary": processed_articles[7].summary,
            "metroHeadline": processed_articles[11].title,
            "metroSummary": processed_articles[11].summary,
            "waterHeadline": processed_articles[0].title,
            "waterSummary": processed_articles[0].summary
        },
        3: {
            "title": "வணிகம் & தொழில்நுட்பம் (Business & Technology)",
            "leadHeadline": processed_articles[3].title,
            "leadSubhead": processed_articles[3].summary,
            "leadByline": f"பொருளாதாரப் பிரிவு • 11 நவம்பர் 2026",
            "leadPhoto": processed_articles[3].image,
            "leadCaption": f"இந்திய நிதி மற்றும் சேமிப்பு திட்ட நிலவரங்கள்.",
            "leadBody": processed_articles[3].body,
            "sideHeadline": processed_articles[4].title,
            "sideSummary": processed_articles[4].summary,
            "metroHeadline": processed_articles[9].title,
            "metroSummary": processed_articles[9].summary,
            "waterHeadline": processed_articles[2].title,
            "waterSummary": processed_articles[2].summary
        },
        4: {
            "title": "தேசியம், உலகம் & விளையாட்டு (National, World & Sports)",
            "leadHeadline": processed_articles[6].title,
            "leadSubhead": processed_articles[6].summary,
            "leadByline": f"விளையாட்டு நிருபர் • 11 நவம்பர் 2026",
            "leadPhoto": processed_articles[6].image,
            "leadCaption": f"சர்வதேச விளையாட்டு அரங்கம் மற்றும் உலக நிகழ்வுகள்.",
            "leadBody": processed_articles[6].body,
            "sideHeadline": processed_articles[8].title,
            "sideSummary": processed_articles[8].summary,
            "metroHeadline": processed_articles[2].title,
            "metroSummary": processed_articles[2].summary,
            "waterHeadline": processed_articles[5].title,
            "waterSummary": processed_articles[5].summary
        }
    }

    # 5. Update HTML and XML templates
    logger.info("4. செய்தி நாளிதழ் தளத்தைப் புதுப்பிக்கிறது (tamil-news-blogger.html & blogger-theme.xml)...")
    for file_path in [ROOT_DIR / "tamil-news-blogger.html", ROOT_DIR / "blogger-theme.xml"]:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")

        # 5.1 Date display
        content = re.sub(
            r'(<span[^>]*id="currentDateDisplay"[^>]*>).*?(</span>)',
            r'\g<1>புதன், 11 நவம்பர் 2026\g<2>',
            content
        )

        # 5.2 Lead card (Card 1)
        p1 = processed_articles[0]
        content = re.sub(
            r'<h1 class="lead-headline">.*?</h1>',
            f'<h1 class="lead-headline">{p1.title}</h1>',
            content,
            count=1,
            flags=re.DOTALL
        )
        content = re.sub(
            r'<p class="lead-summary">.*?</p>',
            f'<p class="lead-summary">{p1.summary}</p>',
            content,
            count=1,
            flags=re.DOTALL
        )
        content = re.sub(
            r'(<article class="lead-news-card"[^>]*>.*?<img src=")[^"]+(")',
            rf'\g<1>{p1.image}\g<2>',
            content,
            count=1,
            flags=re.DOTALL
        )

        # 5.3 Side Cards (Card 4 = Slot 4, Card 7 = Slot 7, Card 6 = Slot 6)
        p4 = processed_articles[3]
        p7 = processed_articles[6]
        p6 = processed_articles[5]

        # Side card 4
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(4\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            rf'\g<1>{p4.image}\g<2>',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(4\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            rf'\g<1>{p4.title}\g<2>',
            content,
            count=1
        )

        # Side card 7
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(7\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            rf'\g<1>{p7.image}\g<2>',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(7\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            rf'\g<1>{p7.title}\g<2>',
            content,
            count=1
        )

        # Side card 6
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(6\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            rf'\g<1>{p6.image}\g<2>',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(6\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            rf'\g<1>{p6.title}\g<2>',
            content,
            count=1
        )

        # 5.4 Speed & Hot Topics thumbnails (replace any unsplash URLs)
        content = content.replace(
            "https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=600&q=80",
            processed_articles[1].image
        )
        content = content.replace(
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=600&q=80",
            processed_articles[4].image
        )

        # 5.5 E-paper modal broadsheet static image references
        content = content.replace(
            "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=600&q=80",
            processed_articles[7].image
        )

        # 5.6 NEWS_DATABASE JavaScript array
        db_entries = [p.to_template_dict() for p in processed_articles]
        db_json = json.dumps(db_entries, ensure_ascii=False, indent=2)
        content = re.sub(
            r'(let\s+NEWS_DATABASE\s*=\s*)\[[\s\S]*?\];',
            rf'\g<1>{db_json};',
            content,
            count=1
        )

        # 5.7 EPAPER_PAGES_CONTENT JavaScript object
        epaper_json = json.dumps(epaper_pages, ensure_ascii=False, indent=2)
        content = re.sub(
            r'(const\s+EPAPER_PAGES_CONTENT\s*=\s*)\{[\s\S]*?\};',
            rf'\g<1>{epaper_json};',
            content,
            count=1
        )

        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Updated {file_path.name} with real news articles and real editorial photos.")

    # 6. Publish to Blogger
    if publish_blogger:
        logger.info("5. கூகிள் பிளாகர் தளத்தில் (https://arachudar.blogspot.com/) கட்டுரைகளை வெளியிடுகிறது...")
        blogger_client = BloggerClient()
        for p in processed_articles:
            try:
                res = blogger_client.publish_article(p, dry_run=False)
                logger.info(f"வெளியிடப்பட்டது: {p.title[:40]} -> {res.get('url', 'OK')}")
            except Exception as exc:
                logger.warning(f"பிளாகரில் வெளியிடுவதில் பிழை ({p.title[:30]}): {exc}")

    logger.info("================================================================")
    logger.info("   அனைத்து தலைப்புகளுக்கும் இன்றைய நேரலை செய்திகள் வெற்றிகரமாக நிரப்பப்பட்டன!")
    logger.info("================================================================")


if __name__ == "__main__":
    run_topic_synthesis(publish_blogger=True)

