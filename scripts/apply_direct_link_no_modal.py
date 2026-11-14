#!/usr/bin/env python3
"""
scripts/apply_direct_link_no_modal.py
Permanently eliminates the modal popup box.
Directs every article click to its separate dedicated full post link (item.postUrl).
Upgrades the single post broadsheet reader to full-page layout without box framing.
"""

from pathlib import Path

for fname in ["blogger-theme.xml", "tamil-news-blogger.html"]:
    p = Path(fname)
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")

    # 1. Permanently hide any modal backdrop via CSS
    hide_modal_css = """
    /* ZERO MODAL BOX - DIRECT FULL PAGE READING */
    .article-modal-backdrop, #articleClippingModal {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
    }
    """
    if "ZERO MODAL BOX - DIRECT FULL PAGE READING" not in text:
        pos = text.find(".article-modal-backdrop {")
        if pos != -1:
            text = text[:pos] + hide_modal_css + "\n" + text[pos:]

    # 2. Upgrade single post view in XML
    old_single_card = """<article class='single-post-reader-card' style='background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:28px 32px; box-shadow:var(--shadow-sm);'>"""
    new_single_card = """<article class='article-main-broadsheet'>
                    <div class="article-reader-toolbar" style="margin-bottom:18px;">
                      <a href="/" class="btn-back-home" title="முகப்புக்குத் திரும்பு">
                        <span>← முகப்புக்குத் திரும்பு (Back to Front Page)</span>
                      </a>
                      <div style="display:flex; align-items:center; gap:8px;">
                        <button class="font-resize-btn" onclick="window.print()" title="அச்சிடுக">🖨️</button>
                      </div>
                    </div>"""
    if old_single_card in text:
        text = text.replace(old_single_card, new_single_card)

    old_single_title = """<h1 class='single-post-title' style='font-family:var(--font-display); font-size:1.75rem; font-weight:800; line-height:1.35; margin-bottom:16px; color:var(--text-main); text-align:left;'>"""
    new_single_title = """<h1 class='article-headline-main'>"""
    if old_single_title in text:
        text = text.replace(old_single_title, new_single_title)

    old_single_body = """<div class='single-post-body' style='font-size:1.12rem; line-height:2.0; color:var(--text-main); text-align:left;'>"""
    new_single_body = """<div class='article-editorial-body'>"""
    if old_single_body in text:
        text = text.replace(old_single_body, new_single_body)

    # 3. Update openArticleModalById in JS to do direct 1-click navigation to item.postUrl
    old_fn = """    function openArticleModalById(id) {
      openFullArticlePage(id);
    }"""
    new_fn = """    function openArticleModalById(id) {
      const db = window.NEWS_DATABASE || NEWS_DATABASE;
      let item = null;
      if (typeof id === 'number') {
        item = db.find(n => n.id === id);
      } else if (typeof id === 'string') {
        item = db.find(n => n.id === parseInt(id, 10) || n.title === id || n.postUrl === id);
      }
      if (!item && db && db.length > 0) {
        item = db[0];
      }
      // 1-Click: Open separate dedicated article link directly
      if (item && item.postUrl) {
        window.location.href = item.postUrl;
        return;
      }
      openFullArticlePage(id);
    }"""
    if old_fn in text:
        text = text.replace(old_fn, new_fn)

    p.write_text(text, encoding="utf-8")
    print(f"Updated {fname} for direct link full-page reading (zero modals)")

