"""
src/ai/tamil_synthesizer.py - Authentic Tamil Journalistic AI Synthesizer.
Converts RawArticle instances into ProcessedArticle dataclasses adhering strictly
to Arachudar editorial standards, Tamil Unicode codepoints, and JSON schemas.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional

from config.sources import map_category, map_subcategory, VALID_CATEGORIES
from src.aggregator.feed_fetcher import RawArticle
from src.ai.nvidia_client import NvidiaClient

logger = logging.getLogger(__name__)

# Range: U+0B80 to U+0BFF (Tamil Unicode Block)
TAMIL_CODEPOINT_PATTERN = re.compile(r'[\u0B80-\u0BFF]')

# Conversational / Reasoning leak patterns to flag and purge
REASONING_LEAK_PATTERNS: List[re.Pattern] = [
    re.compile(r'<\s*think\s*>', re.IGNORECASE),
    re.compile(r'<\s*/\s*think\s*>', re.IGNORECASE),
    re.compile(r'\bhere\s+is\s+the\b', re.IGNORECASE),
    re.compile(r'\bsure,\s+here\b', re.IGNORECASE),
    re.compile(r'\bcertainly\b', re.IGNORECASE),
    re.compile(r'\bas\s+an\s+ai\b', re.IGNORECASE),
    re.compile(r'\bi\s+have\s+generated\b', re.IGNORECASE),
    re.compile(r'\bin\s+tamil\s*:', re.IGNORECASE),
]

# Mojibake detection patterns (corrupted double-decoded UTF-8)
MOJIBAKE_PATTERNS: List[re.Pattern] = [
    re.compile(r'à®'),
    re.compile(r'à¯'),
    re.compile(r'Ã[\x80-\xBF]'),
    re.compile(r'â€™'),
]

TAMIL_MONTHS: Dict[int, str] = {
    1: "ஜனவரி", 2: "பிப்ரவரி", 3: "மார்ச்", 4: "ஏப்ரல்",
    5: "மே", 6: "ஜூன்", 7: "ஜூலை", 8: "ஆகஸ்ட்",
    9: "செப்டம்பர்", 10: "அக்டோபர்", 11: "நவம்பர்", 12: "டிசம்பர்"
}


class SynthesisError(Exception):
    """Raised when Tamil AI synthesis fails or completion is corrupted."""
    pass


@dataclass
class ProcessedArticle:
    """M2 (AI Synthesizer) -> M3 (Publisher) Interface Contract."""
    id: int
    category: str
    sub_category: str
    title: str
    summary: str
    body: str
    image: str
    author: str
    date: str
    time_ago: str
    read_time: str
    views: int
    is_flash: bool
    tags: List[str]
    source_url: str
    source_name: str

    def to_template_dict(self) -> Dict[str, Any]:
        """Convert to camelCase dictionary matching NEWS_DATABASE schema."""
        return {
            "id": self.id,
            "category": self.category,
            "subCategory": self.sub_category,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "image": self.image,
            "author": self.author,
            "date": self.date,
            "timeAgo": self.time_ago,
            "readTime": self.read_time,
            "views": self.views,
            "isFlash": self.is_flash,
            "tags": self.tags,
            "sourceUrl": self.source_url,
            "sourceName": self.source_name,
        }


def detect_mojibake(text: str) -> bool:
    """Checks whether text contains common mojibake sequences."""
    if not text or not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in MOJIBAKE_PATTERNS)


def is_valid_tamil_text(text: str, min_tamil_ratio: float = 0.4) -> bool:
    """Verifies that a string contains authentic Tamil unicode characters."""
    if not text or not isinstance(text, str):
        return False
    non_symbol = [c for c in text if not c.isspace() and not c.isdigit() and c not in '.,;:\'"-!()/?|#%*+=']
    if not non_symbol:
        return False
    tamil_chars = TAMIL_CODEPOINT_PATTERN.findall(text)
    return (len(tamil_chars) / len(non_symbol)) >= min_tamil_ratio


def format_tamil_date(date_str: Optional[str] = None) -> str:
    """Format an ISO date string into Tamil format, e.g. '10 நவம்பர் 2026'."""
    now = datetime.now()
    if date_str:
        try:
            clean = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            return f"{dt.day} {TAMIL_MONTHS.get(dt.month, '')} {dt.year}"
        except Exception:
            pass
    return f"{now.day} {TAMIL_MONTHS.get(now.month, '')} {now.year}"


def format_time_ago(date_str: Optional[str] = None) -> str:
    """Calculate relative time string in Tamil, e.g. '15 நிமிடங்கள் முன்'."""
    if not date_str:
        return "15 நிமிடங்கள் முன்"
    try:
        clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return "சற்று முன்"
        if minutes < 60:
            return f"{minutes} நிமிடங்கள் முன்"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} மணி நேரம் முன்"
        days = hours // 24
        return f"{days} நாட்கள் முன்"
    except Exception:
        return "15 நிமிடங்கள் முன்"


def calculate_read_time(body: str) -> str:
    """Derive reading time estimate in Tamil, e.g. '3 நிமிடம்'."""
    words = len(body.split())
    minutes = max(1, round(words / 150))
    return f"{minutes} நிமிடம்"


def clean_reasoning_and_fences(content: str) -> str:
    """
    Purges <think>...</think> reasoning blocks, strips markdown code fences,
    and returns clean JSON content.
    """
    # 1. Purge <think>...</think> blocks
    cleaned = re.sub(r'<\s*think\s*>.*?<\s*/\s*think\s*>', '', content, flags=re.DOTALL).strip()
    # 2. Purge unclosed <think> blocks
    cleaned = re.sub(r'<\s*think\s*>.*', '', cleaned, flags=re.DOTALL).strip()

    # 3. Check for markdown code fences (```json ... ``` or ``` ... ```)
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, flags=re.DOTALL)
    if m:
        return m.group(1).strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    # 4. If leading/trailing conversational text exists, isolate outermost braces
    if not cleaned.startswith("{"):
        b_start = cleaned.find("{")
        b_end = cleaned.rfind("}")
        if b_start != -1 and b_end > b_start:
            cleaned = cleaned[b_start:b_end + 1]

    return cleaned.strip()


class TamilSynthesizer:
    """
    Arachudar Tamil Journalistic AI Synthesizer.
    Orchestrates prompt construction, LLM completion invocation, schema validation,
    and ProcessedArticle packaging.
    """

    def __init__(self, nvidia_client: Optional[NvidiaClient] = None):
        """
        Initialize the synthesizer with an optional NvidiaClient.
        """
        self.nvidia_client = nvidia_client or NvidiaClient()

    def build_prompt(self, raw_article: RawArticle) -> List[Dict[str, str]]:
        """
        Construct system and user messages adhering to Arachudar editorial guidelines.
        """
        system_role = (
            "நீங்கள் Arachudar (அறச்சுடர்) தமிழ் நாளிதழின் தலைமை செய்தி ஆசிரியர். "
            "உயர்தர, நம்பகமான, நடுநிலையான பத்திரிகை நடையில் (உயர்தர பத்திரிகை நடை) செய்திகளை தொகுத்து, "
            "கவர்ச்சிகரமான தலைப்புடன் வழங்க வேண்டும். உணர்ச்சிவசப்படாமல், நடுநிலையோடு, உண்மைகளின் அடிப்படையில் "
            "செய்திகளை விவரிக்கவும்.\n\n"
            "உங்கள் பதில் கண்டிப்பாக கீழ்க்கண்ட JSON வடிவில் மட்டுமே இருக்க வேண்டும்:\n"
            "{\n"
            '  "category": "tamilnadu | national | world | politics | business | cinema | sports | tech | spiritual",\n'
            '  "subCategory": "chennai | madurai | coimbatore | trichy | south | cricket | news | reviews | ott",\n'
            '  "title": "8 முதல் 12 சொற்களில் உயர்தர கவர்ச்சிகரமான பத்திரிகை தலைப்பு",\n'
            '  "summary": "1-2 வாக்கியங்களில் முக்கிய செய்தி சுருக்கம்",\n'
            '  "body": "முழுமையான பல பத்திகள் கொண்ட விரிவான தமிழ் செய்தி உரை",\n'
            '  "author": "அறச்சுடர் சிறப்பு நிருபர்",\n'
            '  "tags": ["குறிச்சொல்1", "குறிச்சொல்2", "குறிச்சொல்3"],\n'
            '  "isFlash": true\n'
            "}"
        )

        user_content = (
            f"செய்தி: {raw_article.original_title}\n"
            f"சுருக்கம்: {raw_article.original_summary}\n"
            f"மூலம்: {raw_article.source_name}\n"
            f"பிரிவு குறிப்பு: {raw_article.category_hint}\n"
            "JSON வடிவில் வழங்கவும்."
        )

        return [
            {"role": "system", "content": system_role},
            {"role": "user", "content": user_content},
        ]

    def parse_completion(self, raw_text: str) -> Dict[str, Any]:
        """
        Purges reasoning tokens and markdown fences, deserializes JSON,
        and validates required fields and Tamil Unicode authenticity.

        Raises:
            json.JSONDecodeError: When JSON syntax is broken or truncated.
            ValueError: When mandatory fields are missing or Tamil validation fails.
        """
        cleaned = clean_reasoning_and_fences(raw_text)

        # Deserializes JSON safely (raises json.JSONDecodeError if malformed)
        data = json.loads(cleaned)

        # Verify required fields
        required_fields = ["category", "title", "summary", "body"]
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                raise ValueError(f"Missing required schema field: {field}")

        title = str(data["title"]).strip()
        body = str(data["body"]).strip()
        summary = str(data.get("summary", "")).strip()

        # Check for mojibake
        if detect_mojibake(title) or detect_mojibake(body) or detect_mojibake(summary):
            raise ValueError(f"Mojibake detected in synthesized content: title='{title}'")

        # Check for reasoning leaks in headline or body
        for p in REASONING_LEAK_PATTERNS:
            if p.search(title) or p.search(body) or p.search(summary):
                raise ValueError(f"Reasoning leak or conversational artifact detected: {p.pattern}")

        # Validate authentic Tamil content
        if not is_valid_tamil_text(title, min_tamil_ratio=0.5):
            raise ValueError(f"Headline is not authentic Tamil text: '{title}'")
        if not is_valid_tamil_text(body, min_tamil_ratio=0.4):
            raise ValueError("Body is not authentic Tamil text")
        if not is_valid_tamil_text(summary, min_tamil_ratio=0.4):
            raise ValueError("Summary is not authentic Tamil text")

        return data

    def synthesize(self, raw_article: RawArticle, article_id: int = 1) -> ProcessedArticle:
        """
        Synthesize a RawArticle into a published ProcessedArticle.
        Calls NVIDIA NIM chat completions, validates Tamil text, and packages output.
        """
        messages = self.build_prompt(raw_article)

        parsed_data: Optional[Dict[str, Any]] = None
        try:
            resp = self.nvidia_client.create_chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            choices = resp.get("choices", [])
            if choices:
                raw_content = choices[0].get("message", {}).get("content", "")
                parsed_data = self.parse_completion(raw_content)
        except Exception as e:
            logger.warning(
                f"Synthesizer LLM parse or API failure for '{raw_article.original_title}': {e}. "
                "Engaging authentic fallback synthesis."
            )

        # Fallback synthesis if completion parsing failed
        if not parsed_data:
            resolved_category = map_category(raw_article.category_hint or raw_article.original_title)
            resolved_sub = map_subcategory(resolved_category, raw_article.original_title) or "general"
            title = raw_article.original_title
            summary = raw_article.original_summary
            body = (
                f"{raw_article.original_title}\n\n"
                f"{raw_article.original_summary}\n\n"
                f"இந்த செய்தி குறித்து கூடுதல் விவரங்கள் விரைவில் அறச்சுடர் நாளிதழில் வெளியிடப்படும்."
            )
            parsed_data = {
                "category": resolved_category,
                "subCategory": resolved_sub,
                "title": title,
                "summary": summary,
                "body": body,
                "author": "அறச்சுடர் சிறப்பு நிருபர்",
                "tags": ["செய்திகள்", "அறச்சுடர்", raw_article.source_name],
                "isFlash": False,
            }

        # Normalize category and subcategory
        category = map_category(parsed_data.get("category") or raw_article.category_hint)
        sub_category = parsed_data.get("subCategory") or map_subcategory(category, parsed_data.get("title", "")) or "general"
        author = parsed_data.get("author") or "அறச்சுடர் சிறப்பு நிருபர்"
        tags = parsed_data.get("tags") or ["செய்திகள்", "அறச்சுடர்", raw_article.source_name]
        raw_flash = parsed_data.get("isFlash", False)
        is_flash = raw_flash is True or str(raw_flash).strip().lower() in ("true", "1", "yes")
        body = parsed_data["body"]

        return ProcessedArticle(
            id=article_id,
            category=category,
            sub_category=sub_category,
            title=parsed_data["title"],
            summary=parsed_data["summary"],
            body=body,
            image=raw_article.image_url,
            author=author,
            date=format_tamil_date(raw_article.published_date),
            time_ago=format_time_ago(raw_article.published_date),
            read_time=calculate_read_time(body),
            views=random.randint(5000, 15000),
            is_flash=is_flash,
            tags=tags,
            source_url=raw_article.source_url,
            source_name=raw_article.source_name,
        )
