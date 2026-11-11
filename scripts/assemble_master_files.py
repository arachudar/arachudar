# -*- coding: utf-8 -*-
"""
scripts/assemble_master_files.py
Assembles all 42 enriched articles and generates:
1. scripts/build_full_database.py
2. arachudar-blogger-import.xml
"""

import os
import re
import json
from pathlib import Path
from xml.sax.saxutils import escape

from scripts.enriched_part1 import ARTICLES_P1
from scripts.enriched_part2 import ARTICLES_P2
from scripts.enriched_part3 import ARTICLES_P3
from scripts.enriched_part4 import ARTICLES_P4
from scripts.enriched_part5 import ARTICLES_P5

ALL_42_ARTICLES = ARTICLES_P1 + ARTICLES_P2 + ARTICLES_P3 + ARTICLES_P4 + ARTICLES_P5
assert len(ALL_42_ARTICLES) == 42, f"Expected 42 articles, got {len(ALL_42_ARTICLES)}"

# Validate every single article
for idx, a in enumerate(ALL_42_ARTICLES, 1):
    assert a["id"] == idx, f"ID mismatch at {idx}: {a['id']}"
    assert not re.search(r"[a-zA-Z]", a["title"]), f"English in title {idx}"
    assert not re.search(r"[a-zA-Z]", a["summary"]), f"English in summary {idx}"
    assert not re.search(r"[a-zA-Z]", a["body"]), f"English in body {idx}"
    paras = [p for p in a["body"].split("\n\n") if p.strip()]
    assert len(paras) in [4, 5], f"Expected 4-5 paras, got {len(paras)} in {idx}"
    for forbidden in ["ஆசிரியர்:", "வழங்குபவர்:", "வாசிப்பு:"]:
        assert forbidden not in a["body"], f"Found forbidden {forbidden} in {idx}"
    assert a["image"].startswith("https://"), f"Invalid image in {idx}"

print(f"Successfully validated all {len(ALL_42_ARTICLES)} articles!")

# 1. Generate arachudar-blogger-import.xml
blog_id = "563563588050874327"
entries_xml = []
indent = "&emsp;&emsp;"

for idx, art in enumerate(ALL_42_ARTICLES):
    post_id = f"arachudar-20261111-{art['id']:03d}"
    pub_iso = f"2026-11-11T06:{idx:02d}:00+05:30"
    
    # HTML formatted post
    content_html = f'''<div class="arachudar-post" style="font-family: 'Mukta Malar', sans-serif; max-width: 800px; margin: 0 auto; padding: 10px 0;">
<style>
  .arachudar-post {{ font-family: 'Mukta Malar', sans-serif; max-width: 800px; margin: 0 auto; }}
  .arachudar-post .post-body p {{ font-size: 1.15rem; line-height: 2.0; color: #1e293b; margin-bottom: 22px; text-align: justify; text-indent: 2rem; word-break: normal; overflow-wrap: break-word; }}
  .arachudar-post .post-lead {{ font-size: 1.25rem; line-height: 1.85; color: #0f172a; margin-top: 18px; margin-bottom: 26px; padding: 16px 20px; background-color: #f8fafc; border-left: 5px solid #990000; border-radius: 6px; font-weight: 700; text-indent: 1.5rem; text-align: left; }}
</style>
<div class="post-media" style="margin-top: 10px; margin-bottom: 24px; text-align: center;">
  <img src="{art['image']}" alt="{escape(art['title'])}" style="max-width:100%; height:auto; border-radius:8px; box-shadow: 0 4px 14px rgba(0,0,0,0.08);" />
</div>
<div class="post-lead">{indent}{escape(art['summary'])}</div>
<div class="post-body">
'''
    for p in art["body"].split("\n\n"):
        clean_p = p.strip()
        if clean_p:
            content_html += f'<p>{indent}{escape(clean_p)}</p>\n'
    content_html += '</div></div>'

    categories_xml = '\n'.join([
        f'    <category scheme="http://www.blogger.com/atom/ns#" term="{escape(lbl)}"/>'
        for lbl in art.get("tags", ["தமிழகம்", "செய்திகள்"])
    ])

    entry_str = f'''  <entry>
    <id>tag:blogger.com,1999:blog-{blog_id}.post-{post_id}</id>
    <published>{pub_iso}</published>
    <updated>{pub_iso}</updated>
    <category scheme="http://schemas.google.com/g/2005#kind" term="http://schemas.google.com/blogger/2008/kind#post"/>
{categories_xml}
    <title type="text">{escape(art["title"])}</title>
    <content type="html"><![CDATA[{content_html}]]></content>
    <author>
      <name>அறச்சுடர்</name>
      <email>arachudarnews@gmail.com</email>
    </author>
  </entry>'''
    entries_xml.append(entry_str)

full_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/" xmlns:blogger="http://schemas.google.com/blogger/2008" xmlns:georss="http://www.georss.org/georss" xmlns:gd="http://schemas.google.com/g/2005" xmlns:thr="http://purl.org/syndication/thread/1.0">
  <id>tag:blogger.com,1999:blog-{blog_id}</id>
  <updated>2026-11-11T08:00:00Z</updated>
  <title type="text">அறச்சுடர்</title>
  <link rel="http://schemas.google.com/g/2005#feed" type="application/atom+xml" href="https://arachudar.blogspot.com/feeds/posts/default"/>
  <link rel="self" type="application/atom+xml" href="https://arachudar.blogspot.com/feeds/posts/default"/>
  <link rel="alternate" type="text/html" href="https://arachudar.blogspot.com/"/>
  <author>
    <name>அறச்சுடர்</name>
    <email>arachudarnews@gmail.com</email>
  </author>
  <generator version="7.00" uri="http://www.blogger.com">Blogger</generator>
{chr(10).join(entries_xml)}
</feed>'''

Path("arachudar-blogger-import.xml").write_text(full_xml, encoding="utf-8")
print(f"Generated arachudar-blogger-import.xml ({len(full_xml)} bytes, {len(ALL_42_ARTICLES)} posts)")

# 2. Write scripts/build_full_database.py
bfd_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_full_database.py
Authoritative database of 42 articles with 100% matched verified images and 4-5 paragraphs.
"""

import json
import re
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))


def clean_tamil_text(text: str) -> str:
    """Removes Latin/English characters and normalizes whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[a-zA-Z]+", "", text)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned


ALL_42_ARTICLES: List[Dict[str, Any]] = {json.dumps(ALL_42_ARTICLES, ensure_ascii=False, indent=2)}


def update_all_templates():
    from scripts.apply_layout_and_modal_fix import run
    run()


if __name__ == '__main__':
    update_all_templates()
'''

Path("scripts/build_full_database.py").write_text(bfd_code, encoding="utf-8")
print(f"Generated scripts/build_full_database.py ({len(bfd_code)} bytes)")
