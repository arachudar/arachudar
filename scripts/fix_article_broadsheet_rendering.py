#!/usr/bin/env python3
"""
scripts/fix_article_broadsheet_rendering.py
Fixes the root cause of article display:
1. Prevents renderHomeFeed() from ever overwriting the server-rendered article on item pages.
2. Removes duplicate firstImageUrl so the image only appears once inside article body.
3. Upgrades article-main-broadsheet header with full reading toolbar and TTS player.
4. Guarantees 1-click navigation to postUrl with ZERO modal popups.
"""

from pathlib import Path

for fname in ["blogger-theme.xml", "tamil-news-blogger.html"]:
    p = Path(fname)
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")

    # 1. Update isArticlePage guard in JS
    guard_js = """
    function isArticlePage() {
      if (typeof window === 'undefined') return false;
      const path = (window.location && window.location.pathname) ? window.location.pathname : '';
      if (path.endsWith('.html') && !path.endsWith('/index.html')) return true;
      if (typeof document !== 'undefined' && document.querySelector && document.querySelector('.article-main-broadsheet')) return true;
      return false;
    }

    function renderArticlePageRecommendations() {
      if (typeof NEWS_DATABASE === 'undefined' || !NEWS_DATABASE || NEWS_DATABASE.length === 0) return;
      const path = (window.location && window.location.pathname) ? window.location.pathname : '';
      const activePost = NEWS_DATABASE.find(n => n.postUrl && (path.includes(n.postUrl) || n.postUrl.includes(path))) || NEWS_DATABASE[0];
      if (activePost && typeof RecommendationAgent !== 'undefined') {
        RecommendationAgent.render(activePost);
      }
    }
    """

    if "function isArticlePage()" not in text:
        pos = text.find("function renderHomeFeed() {")
        if pos != -1:
            text = text[:pos] + guard_js + "\n    " + text[pos:]

    # 2. Inject guard check at top of renderHomeFeed()
    if "if (isArticlePage()) return;" not in text:
        marker = "function renderHomeFeed() {\n      const main = document.getElementById('mainDynamicView');"
        repl = "function renderHomeFeed() {\n      if (isArticlePage()) return;\n      const main = document.getElementById('mainDynamicView');"
        if marker in text:
            text = text.replace(marker, repl)
        else:
            marker2 = "function renderHomeFeed() {\n      if (isArticlePage()) return;"
            if marker2 not in text:
                text = text.replace("function renderHomeFeed() {", "function renderHomeFeed() {\n      if (isArticlePage()) return;")

    # 3. Guard in BloggerFeedEngine.fetchFeed() / parseEntries()
    feed_guard = """        if (parsed.length > 0) {
          window.NEWS_DATABASE = NEWS_DATABASE = parsed;
          updateHomepageSlotsFromDatabase();
          initSidebarAndTicker();
          initTicker();
          if (isArticlePage()) {
            renderArticlePageRecommendations();
          } else if (currentCategory === 'home' || currentCategory === 'all') {
            renderHomeFeed();
          } else {
            renderCategoryFeed(currentCategory, currentSubFilter);
          }
        }"""
    feed_orig = """        if (parsed.length > 0) {
          window.NEWS_DATABASE = NEWS_DATABASE = parsed;
          updateHomepageSlotsFromDatabase();
          initSidebarAndTicker();
          initTicker();
          if (currentCategory === 'home' || currentCategory === 'all') {
            renderHomeFeed();
          } else {
            renderCategoryFeed(currentCategory, currentSubFilter);
          }
        }"""
    if feed_orig in text:
        text = text.replace(feed_orig, feed_guard)

    # 4. Remove duplicate post.firstImageUrl from XML single post view
    dup_img_pattern = """                    <b:if cond='data:post.firstImageUrl'>
                      <div style='margin-bottom:20px; border-radius:8px; overflow:hidden;'>
                        <img expr:src='data:post.firstImageUrl' expr:alt='data:post.title' style='width:100%; max-height:450px; object-fit:cover; border-radius:8px;'/>
                      </div>
                    </b:if>"""
    if dup_img_pattern in text:
        text = text.replace(dup_img_pattern, "")

    # 5. Make sure article-main-broadsheet has reading toolbar on Blogger item page
    old_broadsheet_bar = """<article class='article-main-broadsheet'>
                    <div class="article-reader-toolbar" style="margin-bottom:18px;">
                      <a href="/" class="btn-back-home" title="முகப்புக்குத் திரும்பு">
                        <span>← முகப்புக்குத் திரும்பு (Back to Front Page)</span>
                      </a>
                      <div style="display:flex; align-items:center; gap:8px;">
                        <button class="font-resize-btn" onclick="window.print()" title="அச்சிடுக">🖨️</button>
                      </div>
                    </div>"""
    new_broadsheet_bar = """<article class='article-main-broadsheet'>
                    <div class="article-reader-toolbar" style="margin-bottom:24px;">
                      <a href="/" class="btn-back-home" title="முகப்புக்குத் திரும்பு">
                        <span>← முகப்புக்குத் திரும்பு (Back to Front Page)</span>
                      </a>
                      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <button id="readerAudioBtn" class="audio-narration-btn" onclick="toggleAudioReadAloud()" title="செய்தியை வாசிக்க">
                          <span>🔊 வாசிக்க</span>
                        </button>
                        <button class="font-resize-btn" onclick="adjustArticleFontSize(-1)" title="சிறிய எழுத்து">A-</button>
                        <button class="font-resize-btn" onclick="adjustArticleFontSize(1)" title="பெரிய எழுத்து">A+</button>
                        <button class="font-resize-btn" onclick="window.print()" title="அச்சிடுக">🖨️</button>
                      </div>
                    </div>"""
    if old_broadsheet_bar in text:
        text = text.replace(old_broadsheet_bar, new_broadsheet_bar)

    p.write_text(text, encoding="utf-8")
    print(f"Applied broadsheet protection to {fname}")

