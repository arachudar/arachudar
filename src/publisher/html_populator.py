"""
src/publisher/html_populator.py - Dual-layer template populator.
Updates static DOM slots and dynamic JavaScript arrays (NEWS_DATABASE, EPAPER_PAGES_CONTENT)
in copies or canonical files of tamil-news-blogger.html.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from src.ai.tamil_synthesizer import ProcessedArticle


class HtmlPopulator:
    """
    Dual-layer template populator updating static DOM slots and dynamic JavaScript
    arrays (NEWS_DATABASE, EPAPER_PAGES_CONTENT) in tamil-news-blogger.html.
    """

    def __init__(self, template_path: Union[str, Path]):
        self.template_path = Path(template_path)

    def populate(
        self,
        articles: List[ProcessedArticle],
        epaper_pages: Optional[Dict[Union[int, str], Dict[str, str]]] = None,
        current_date_str: str = "திங்கள், 10 நவம்பர் 2026"
    ) -> str:
        """
        Populate the template with synthesized Tamil articles.
        
        :param articles: List of ProcessedArticle instances
        :param epaper_pages: Optional e-paper page content mapping
        :param current_date_str: Formatted Tamil date string
        :return: Updated HTML string
        """
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
            lead_id = getattr(lead, "id", 1)
            lead_title = getattr(lead, "title", "")
            lead_summary = getattr(lead, "summary", "")
            lead_image = getattr(lead, "image", "")

            # Lead headline
            html = re.sub(
                r'<h1 class="lead-headline">.*?</h1>',
                f'<h1 class="lead-headline">{lead_title}</h1>',
                html,
                count=1,
                flags=re.DOTALL
            )
            # Lead summary
            html = re.sub(
                r'<p class="lead-summary">.*?</p>',
                f'<p class="lead-summary">{lead_summary}</p>',
                html,
                count=1,
                flags=re.DOTALL
            )
            # Lead card onclick navigation
            html = re.sub(
                r'<article class="lead-news-card" onclick="navigateToArticle\(\d+\)">',
                f'<article class="lead-news-card" onclick="navigateToArticle({lead_id})">',
                html,
                count=1
            )
            # Lead card image src
            html = re.sub(
                r'(<article class="lead-news-card"[^>]*>.*?<img src=")[^"]+(")',
                rf'\g<1>{lead_image}\g<2>',
                html,
                count=1,
                flags=re.DOTALL
            )

        # 3. Update NEWS_DATABASE JavaScript array
        db_entries = []
        for a in articles:
            if hasattr(a, "to_template_dict"):
                db_entries.append(a.to_template_dict())
            elif isinstance(a, dict):
                db_entries.append(a)

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

