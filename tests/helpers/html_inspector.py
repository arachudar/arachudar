"""
tests/helpers/html_inspector.py - Production Newspaper HTML Template Validator.
Inspects static DOM slots, JavaScript NEWS_DATABASE arrays, and e-paper schemas
to verify structural consistency and prevent broken article references.
"""

import re
from typing import List, Set


def extract_dom_slot_ids(html_content: str) -> List[int]:
    """Extracts all article IDs referenced by static click handlers: navigateToArticle(id)."""
    return [int(match) for match in re.findall(r'navigateToArticle\((\d+)\)', html_content)]


def extract_news_database_ids(html_content: str) -> List[int]:
    """
    Extracts all numeric IDs defined within the embedded NEWS_DATABASE JavaScript array.
    """
    db_match = re.search(r'(?:let|var|const)\s+NEWS_DATABASE\s*=\s*\[(.*?)\];', html_content, re.DOTALL)
    if not db_match:
        # Check without semicolon in case formatted differently
        db_match = re.search(r'(?:let|var|const)\s+NEWS_DATABASE\s*=\s*\[(.*?)\]', html_content, re.DOTALL)

    if not db_match:
        return []

    db_block = db_match.group(1)
    # Match id: 1, or "id": 1,
    return [int(m) for m in re.findall(r'["\']?id["\']?\s*:\s*(\d+)', db_block)]


def has_epaper_pages_content(html_content: str) -> bool:
    """Checks whether the EPAPER_PAGES_CONTENT dictionary is present in the document."""
    return bool(re.search(r'(?:let|var|const)\s+EPAPER_PAGES_CONTENT\s*=', html_content))


def verify_template_integrity(
    html_content: str,
    min_static_cards: int = 1,
    require_epaper: bool = True
):
    """
    Asserts structural and relational integrity of the populated HTML template:
    1. Validates presence of top bar date display.
    2. Extracts static card article IDs and verifies min_static_cards threshold.
    3. Locates NEWS_DATABASE array and extracts all article IDs.
    4. Guarantees that EVERY static HTML card ID exists in NEWS_DATABASE (no broken reader modals).
    5. Checks EPAPER_PAGES_CONTENT definition if require_epaper is True.
    """
    assert 'id="currentDateDisplay"' in html_content or "currentDateDisplay" in html_content, (
        "Required date display container (#currentDateDisplay) missing from HTML template"
    )

    card_ids = extract_dom_slot_ids(html_content)
    assert len(card_ids) >= min_static_cards, (
        f"Expected at least {min_static_cards} static cards with navigateToArticle(id), found {len(card_ids)}"
    )

    db_ids = extract_news_database_ids(html_content)
    assert len(db_ids) > 0, "No article IDs found in JavaScript NEWS_DATABASE array"

    missing_ids: Set[int] = set(card_ids) - set(db_ids)
    assert not missing_ids, (
        f"Integrity Violation: Static HTML cards reference article IDs {sorted(list(missing_ids))} "
        f"which are missing from JavaScript NEWS_DATABASE! Clicking them causes runtime reader failure."
    )

    if require_epaper:
        assert has_epaper_pages_content(html_content), (
            "EPAPER_PAGES_CONTENT broadsheet schema missing from HTML template script"
        )
