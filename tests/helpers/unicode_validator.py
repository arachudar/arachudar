"""
tests/helpers/unicode_validator.py - Authentic Tamil Unicode & Content Quality Validator.
Validates Tamil script codepoints, detects conversational LLM leaks, and flags mojibake.
"""

import re
from typing import List

# Range: U+0B80 to U+0BFF (Tamil Unicode Block)
TAMIL_CODEPOINT_PATTERN = re.compile(r'[\u0B80-\u0BFF]')

# Common English conversational/reasoning phrases from LLMs
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

# Mojibake indicators (e.g. UTF-8 decoded as ISO-8859-1 or Windows-1252)
MOJIBAKE_PATTERNS: List[re.Pattern] = [
    re.compile(r'à®[^\s]'),
    re.compile(r'à¯[^\s]'),
    re.compile(r'Ã[\x80-\xBF]'),
    re.compile(r'â€™'),
]


def detect_mojibake(text: str) -> bool:
    """Checks whether text contains common mojibake sequences caused by double UTF-8 decoding."""
    if not text or not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in MOJIBAKE_PATTERNS)


def is_valid_tamil_text(text: str, min_tamil_ratio: float = 0.4) -> bool:
    """
    Verifies that a string contains authentic Tamil unicode characters.
    Calculates the ratio of Tamil codepoints against all alphabetic/symbolic characters.
    """
    if not text or not isinstance(text, str):
        return False

    # Filter out whitespace, digits, and common punctuation
    non_symbol = [c for c in text if not c.isspace() and not c.isdigit() and c not in '.,;:\'"-!()/?|#%*+=']
    if not non_symbol:
        return False

    tamil_chars = TAMIL_CODEPOINT_PATTERN.findall(text)
    ratio = len(tamil_chars) / len(non_symbol)
    return ratio >= min_tamil_ratio


def assert_clean_tamil_headline(headline: str, min_length: int = 10, min_tamil_ratio: float = 0.80):
    """
    Asserts that a news headline:
    1. Has at least min_length characters.
    2. Contains a dominant proportion of Tamil Unicode characters (>= min_tamil_ratio, default 0.80).
    3. Contains no reasoning tokens or conversational English phrases.
    4. Does not suffer from UTF-8 mojibake.
    """
    assert isinstance(headline, str), f"Headline must be str, got {type(headline)}"
    clean = headline.strip()
    assert len(clean) >= min_length, f"Headline too short ({len(clean)} chars): '{headline}'"
    assert is_valid_tamil_text(clean, min_tamil_ratio=min_tamil_ratio), (
        f"Headline is not authentic Tamil (ratio < {min_tamil_ratio}): '{headline}'"
    )
    assert not detect_mojibake(clean), f"Mojibake detected in headline: '{headline}'"

    for pattern in REASONING_LEAK_PATTERNS:
        assert not pattern.search(clean), (
            f"Reasoning token or conversational artifact detected in headline matching '{pattern.pattern}': '{headline}'"
        )


def assert_clean_tamil_body(body: str, min_length: int = 40):
    """
    Asserts that an article body:
    1. Has at least min_length characters.
    2. Contains authentic Tamil content.
    3. Does not contain leaked reasoning tags.
    4. Does not contain mojibake.
    """
    assert isinstance(body, str), f"Article body must be str, got {type(body)}"
    clean = body.strip()
    assert len(clean) >= min_length, f"Article body too short ({len(clean)} chars)"
    assert is_valid_tamil_text(clean, min_tamil_ratio=0.5), "Article body Tamil ratio too low"
    assert not detect_mojibake(clean), "Mojibake detected in article body"

    for pattern in REASONING_LEAK_PATTERNS:
        assert not pattern.search(clean), (
            f"Reasoning token or conversational artifact detected in article body matching '{pattern.pattern}'"
        )
