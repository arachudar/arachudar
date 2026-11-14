#!/usr/bin/env python3
"""
scripts/apply_full_article_reader.py
Implements full-page broadsheet newspaper article reader layout,
recommendation agent, right sidebar recommendations, and bottom related grid.
"""

from pathlib import Path

THEME_PATH = Path("blogger-theme.xml")
CANONICAL_PATH = Path("tamil-news-blogger.html")

READER_CSS = """
    /* ========================================================
       FULL-PAGE BROADSHEET ARTICLE READER & RECOMMENDATION AGENT
       ======================================================== */
    #fullArticleReaderContainer {
      display: none;
      background: var(--bg-body);
      color: var(--text-main);
      padding: 16px 0 60px 0;
      min-height: 85vh;
    }
    .article-reader-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
      flex-wrap: wrap;
      gap: 12px;
    }
    .btn-back-home {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 18px;
      background: var(--brand-red);
      color: #ffffff !important;
      font-weight: 700;
      font-size: 0.92rem;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    .btn-back-home:hover {
      background: #7a0000;
      transform: translateY(-1px);
    }
    .article-reader-grid {
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 36px;
      align-items: start;
    }
    @media (max-width: 992px) {
      .article-reader-grid {
        grid-template-columns: 1fr;
      }
    }
    .article-main-broadsheet {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 36px 40px;
      box-shadow: var(--shadow-sm);
    }
    @media (max-width: 768px) {
      .article-main-broadsheet {
        padding: 20px 16px;
      }
    }
    .article-headline-main {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1.35;
      color: var(--text-main);
      margin: 16px 0 20px 0;
      letter-spacing: -0.01em;
      text-align: left;
    }
    @media (max-width: 768px) {
      .article-headline-main {
        font-size: 1.65rem;
      }
    }
    .article-meta-ribbon {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      padding-bottom: 18px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .article-hero-media {
      margin: 0 0 28px 0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
    .article-hero-media img {
      width: 100%;
      max-height: 520px;
      object-fit: cover;
      display: block;
    }
    .article-hero-media figcaption {
      padding: 10px 14px;
      background: var(--bg-muted);
      font-size: 0.8rem;
      color: var(--text-muted);
      font-style: italic;
      border-top: 1px solid var(--border-color);
    }
    .article-lead-highlight {
      font-size: 1.25rem;
      line-height: 1.9;
      font-weight: 700;
      color: var(--text-main);
      padding: 20px 24px;
      margin-bottom: 30px;
      background: rgba(153, 0, 0, 0.04);
      border-left: 5px solid var(--brand-red);
      border-radius: 6px;
      text-align: left;
    }
    .article-editorial-body p {
      font-size: 1.18rem;
      line-height: 2.1;
      color: var(--text-main);
      margin-bottom: 24px;
      text-align: justify;
      text-indent: 2.2rem;
      word-break: normal;
      overflow-wrap: break-word;
    }
    .sidebar-recommendation-box {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 22px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
    }
    .sidebar-rec-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--brand-red);
      padding-bottom: 12px;
      margin-bottom: 16px;
      border-bottom: 2px solid var(--brand-red);
    }
    .rec-card-mini {
      display: flex;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid var(--border-color);
      cursor: pointer;
      transition: transform 0.2s ease;
      align-items: flex-start;
    }
    .rec-card-mini:last-child {
      border-bottom: none;
    }
    .rec-card-mini:hover {
      transform: translateX(4px);
    }
    .rec-card-mini-thumb {
      width: 80px;
      height: 60px;
      border-radius: 6px;
      object-fit: cover;
      flex-shrink: 0;
    }
    .rec-card-mini-content h4 {
      font-size: 0.88rem;
      font-weight: 700;
      line-height: 1.35;
      color: var(--text-main);
      margin: 0 0 4px 0;
      text-align: left;
    }
    .rec-card-mini-content .rec-meta {
      font-size: 0.72rem;
      color: var(--text-muted);
      text-align: left;
    }
    .bottom-recommendation-section {
      margin-top: 48px;
      padding-top: 36px;
      border-top: 2px dashed var(--border-color);
    }
    .bottom-rec-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
      margin-top: 20px;
    }
    @media (max-width: 768px) {
      .bottom-rec-grid {
        grid-template-columns: 1fr;
      }
    }
"""

READER_HTML = """
  <!-- ========================================================
       FULL-PAGE BROADSHEET ARTICLE READER (NEWSPAPER EXPERIENCE)
       ======================================================== -->
  <div id="fullArticleReaderContainer">
    <div class="container">
      <!-- READER TOP ACTION TOOLBAR -->
      <div class="article-reader-toolbar">
        <button class="btn-back-home" onclick="closeFullArticlePage()" title="முகப்புக்குத் திரும்பு">
          <span>← முகப்புக்குத் திரும்பு (Back to Front Page)</span>
        </button>
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <button id="readerAudioBtn" class="audio-narration-btn" onclick="toggleAudioReadAloud()" title="செய்தியை வாசிக்க">
            <span>🔊 வாசிக்க</span>
          </button>
          <button class="font-resize-btn" onclick="adjustArticleFontSize(-1)" title="சிறிய எழுத்து">A-</button>
          <button class="font-resize-btn" onclick="adjustArticleFontSize(1)" title="பெரிய எழுத்து">A+</button>
          <button class="font-resize-btn" onclick="window.print()" title="அச்சிடுக">🖨️</button>
          <button class="font-resize-btn" onclick="closeFullArticlePage()" title="மூடுக" style="font-weight:bold;">✕</button>
        </div>
      </div>

      <!-- MAIN ARTICLE BROADSHEET GRID (72% Main + 28% Recs Sidebar) -->
      <div class="article-reader-grid">
        <!-- LEFT: MAIN EDITORIAL STORY -->
        <article class="article-main-broadsheet">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
            <span class="category-tag-badge" id="readerCategoryBadge" style="margin-bottom:0;">செய்தி</span>
            <span style="font-size:0.8rem; color:var(--text-muted);" id="readerBreadcrumbCategory">முகப்பு</span>
            <span style="font-size:0.8rem; color:var(--text-muted);">›</span>
            <span style="font-size:0.8rem; color:var(--text-muted); font-weight:700;" id="readerBreadcrumbTitle">முழு செய்தி</span>
          </div>

          <h1 class="article-headline-main" id="readerHeadlineTitle">
            செய்தி தலைப்பு
          </h1>

          <!-- EDITORIAL BYLINE RIBBON -->
          <div class="article-meta-ribbon">
            <span class="meta-pill" id="readerAuthorBadge">✍️ அறச்சுடர் நிருபர்</span>
            <span class="meta-pill" id="readerDateBadge">📅 இன்று</span>
            <span class="meta-pill" id="readerReadTimeBadge">⏱️ 3 நிமிடம் வாசிப்பு</span>
            <span class="meta-pill" id="readerViewsBadge">👁️ 5,000 பார்வையாளர்கள்</span>
          </div>

          <!-- FEATURED 1200PX PRESS VISUAL -->
          <figure class="article-hero-media" id="readerArticleFigure">
            <img src="" id="readerArticleImage" alt="செய்தி படம்" />
            <figcaption id="readerArticleCaption">அறச்சுடர் புகைப்படப் பதிவு</figcaption>
          </figure>

          <!-- BOLD EDITORIAL LEAD BOX -->
          <div class="article-lead-highlight" id="readerLeadHighlight">
            <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:var(--brand-red); margin-bottom:6px;">முக்கியச் செய்திச் சுருக்கம்</div>
            <div id="readerLeadText"></div>
          </div>

          <!-- FULL MULTI-PARAGRAPH EDITORIAL BODY -->
          <div class="article-editorial-body" id="readerEditorialBody">
          </div>

          <!-- TOPIC TAGS CLOUD -->
          <div style="margin:28px 0 24px 0; display:flex; align-items:center; gap:8px; flex-wrap:wrap;" id="readerArticleTags">
          </div>

          <!-- 1-CLICK SOCIAL SHARING BAR -->
          <div class="share-buttons-row" style="margin-top:24px; padding-top:20px; border-top:1px solid var(--border-color);">
            <span style="font-size:0.85rem; font-weight:700; color:var(--text-main);">செய்தியை பகிர:</span>
            <button class="share-btn share-wa" onclick="shareArticleOnWhatsApp()" title="வாட்ஸ்அப்பில் பகிர">WhatsApp</button>
            <button class="share-btn share-x" onclick="shareArticleOnX()" title="X தளத்தில் பகிர">X (Twitter)</button>
            <button class="share-btn share-fb" onclick="shareArticleOnFB()" title="பேஸ்புக்கில் பகிர">Facebook</button>
            <button class="share-btn share-copy" onclick="copyArticleLink()" title="இணைப்பை பிரதி செய்க">🔗 Copy Link</button>
          </div>
        </article>

        <!-- RIGHT: RECOMMENDATION & TRENDING SIDEBAR -->
        <aside class="sidebar-wrapper" style="position:sticky; top:20px;">
          <div class="sidebar-recommendation-box">
            <div class="sidebar-rec-header">
              <span>📌 தொடர்புடைய செய்திகள்</span>
            </div>
            <div id="sidebarRelatedNewsList">
            </div>
          </div>

          <div class="sidebar-recommendation-box">
            <div class="sidebar-rec-header">
              <span>🔥 அதிகம் வாசிக்கப்பட்டவை</span>
            </div>
            <div id="sidebarTrendingNewsList">
            </div>
          </div>
        </aside>
      </div>

      <!-- BOTTOM: MORE RECOMMENDED STORIES GRID (3 COLUMNS) -->
      <section class="bottom-recommendation-section">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
          <h2 style="font-family:var(--font-display); font-size:1.5rem; font-weight:800; color:var(--text-main); margin:0;">
            📰 மேலும் நீங்கள் படிக்க விரும்பலாம் (More Recommendations)
          </h2>
          <button class="btn-back-home" onclick="closeFullArticlePage()" style="padding:6px 14px; font-size:0.8rem;">அனைத்து செய்திகள் →</button>
        </div>
        <div class="bottom-rec-grid" id="bottomRelatedStoriesGrid">
        </div>
      </section>
    </div>
  </div>
"""

READER_JS = """
    /* ========================================================
       AUTONOMOUS RECOMMENDATION AGENT & BROADSHEET ARTICLE ENGINE
       ======================================================== */
    const RecommendationAgent = {
      getRelatedStories(article, limit) {
        limit = limit || 4;
        const db = window.NEWS_DATABASE || NEWS_DATABASE;
        if (!db || db.length === 0) return [];
        return db
          .filter(item => item.id !== article.id && item.title !== article.title)
          .map(item => {
            let score = 0;
            if (item.category === article.category) score += 50;
            if (item.subCategory && item.subCategory === article.subCategory) score += 20;
            if (item.tags && article.tags) {
              const overlap = item.tags.filter(t => article.tags.includes(t));
              score += overlap.length * 15;
            }
            score += ((item.views || 5000) % 1000) / 100;
            return { item: item, score: score };
          })
          .sort((a, b) => b.score - a.score)
          .slice(0, limit)
          .map(entry => entry.item);
      },

      getTrendingStories(article, limit) {
        limit = limit || 4;
        const db = window.NEWS_DATABASE || NEWS_DATABASE;
        if (!db || db.length === 0) return [];
        return db
          .filter(item => item.id !== article.id)
          .sort((a, b) => (b.views || 0) - (a.views || 0))
          .slice(0, limit);
      },

      render(article) {
        // 1. Right Sidebar: Related Stories
        const relContainer = document.getElementById('sidebarRelatedNewsList');
        const relStories = this.getRelatedStories(article, 4);
        if (relContainer) {
          if (relStories.length > 0) {
            relContainer.innerHTML = relStories.map(s => `
              <article class="rec-card-mini" onclick="openFullArticlePage(${s.id})">
                <img src="${s.image}" alt="${s.title}" class="rec-card-mini-thumb" loading="lazy" />
                <div class="rec-card-mini-content">
                  <span class="category-tag-badge" style="font-size:0.65rem; padding:2px 6px; margin-bottom:4px;">${CATEGORY_TITLES[s.category] || s.category}</span>
                  <h4>${s.title}</h4>
                  <div class="rec-meta">⏱️ ${s.readTime || '3 நிமிடம்'} • 👁️ ${s.views || 5000}</div>
                </div>
              </article>
            `).join('');
          } else {
            relContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; padding:12px 0;">தொடர்புடைய செய்திகள் சேகரிக்கப்படுகின்றன...</p>';
          }
        }

        // 2. Right Sidebar: Trending Stories
        const trendContainer = document.getElementById('sidebarTrendingNewsList');
        const trendStories = this.getTrendingStories(article, 4);
        if (trendContainer) {
          if (trendStories.length > 0) {
            trendContainer.innerHTML = trendStories.map((s, idx) => `
              <article class="rec-card-mini" onclick="openFullArticlePage(${s.id})">
                <div class="trend-rank-badge" style="font-size:1.1rem; font-weight:900; color:var(--brand-red); width:28px; text-align:center; flex-shrink:0;">#${idx+1}</div>
                <div class="rec-card-mini-content">
                  <span class="category-tag-badge" style="font-size:0.65rem; padding:2px 6px; margin-bottom:4px;">${CATEGORY_TITLES[s.category] || s.category}</span>
                  <h4>${s.title}</h4>
                  <div class="rec-meta">${s.date || 'இன்று'} • 👁️ ${s.views || 6200}</div>
                </div>
              </article>
            `).join('');
          } else {
            trendContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; padding:12px 0;">டிரெண்டிங் செய்திகள் பெறப்படுகின்றன...</p>';
          }
        }

        // 3. Bottom Recommended News Grid (3-columns)
        const bottomGrid = document.getElementById('bottomRelatedStoriesGrid');
        const db = window.NEWS_DATABASE || NEWS_DATABASE;
        const bottomStories = db.filter(item => item.id !== article.id).slice(0, 3);
        if (bottomGrid) {
          if (bottomStories.length > 0) {
            bottomGrid.innerHTML = bottomStories.map(s => `
              <article class="news-grid-card" onclick="openFullArticlePage(${s.id})" style="cursor:pointer;">
                <div class="card-media-wrap">
                  <img src="${s.image}" alt="${s.title}" loading="lazy" />
                </div>
                <div class="card-content-area">
                  <span class="category-tag-badge" style="align-self:flex-start;">${CATEGORY_TITLES[s.category] || s.category}</span>
                  <h3 class="card-headline" style="font-size:1.05rem;">${s.title}</h3>
                  <p class="card-snippet">${s.summary}</p>
                  <div class="card-footer-meta">
                    <span>⏱️ ${s.readTime || '3 நிமி'}</span>
                    <span>👁️ ${s.views || 5000} வாசிப்புகள்</span>
                  </div>
                </div>
              </article>
            `).join('');
          }
        }
      }
    };

    function openFullArticlePage(id) {
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
      if (!item) return;

      currentActiveArticleId = item.id;
      currentActiveArticleText = item.title + '. ' + (item.summary || '') + '. ' + (item.body || '');

      // 1. Hide homepage and category sections
      hideHeroAndWires();
      const catSection = document.getElementById('categoryDynamicSection');
      if (catSection) catSection.style.display = 'none';
      const staticGrid = document.getElementById('bloggerStaticPostsGrid');
      if (staticGrid) staticGrid.style.display = 'none';
      const breadcrumbNav = document.getElementById('breadcrumbNav');
      if (breadcrumbNav) breadcrumbNav.style.display = 'none';

      // 2. Show Full Article Broadsheet Container
      const reader = document.getElementById('fullArticleReaderContainer');
      if (reader) reader.style.display = 'block';

      // 3. Inject Breadcrumb & Header Data
      const catTitle = CATEGORY_TITLES[item.category] || item.category;
      const breadcrumbEl = document.getElementById('readerBreadcrumbCategory');
      if (breadcrumbEl) breadcrumbEl.textContent = catTitle;
      const breadcrumbTitle = document.getElementById('readerBreadcrumbTitle');
      if (breadcrumbTitle) breadcrumbTitle.textContent = item.title;

      const catBadge = document.getElementById('readerCategoryBadge');
      if (catBadge) catBadge.textContent = catTitle.toUpperCase();

      const titleEl = document.getElementById('readerHeadlineTitle');
      if (titleEl) titleEl.textContent = item.title;

      const authorEl = document.getElementById('readerAuthorBadge');
      if (authorEl) authorEl.textContent = item.author ? '✍️ ' + item.author : '✍️ அறச்சுடர் நிருபர்';

      const dateEl = document.getElementById('readerDateBadge');
      if (dateEl) dateEl.textContent = '📅 ' + (item.date || 'இன்று');

      const readTimeEl = document.getElementById('readerReadTimeBadge');
      if (readTimeEl) readTimeEl.textContent = '⏱️ ' + (item.readTime || '3 நிமிடம் வாசிப்பு');

      const viewsEl = document.getElementById('readerViewsBadge');
      if (viewsEl) viewsEl.textContent = '👁️ ' + (item.views ? item.views.toLocaleString() : '5,000') + ' வாசிப்புகள்';

      // 4. Featured Hero Image
      const imgEl = document.getElementById('readerArticleImage');
      const figEl = document.getElementById('readerArticleFigure');
      if (item.image) {
        if (imgEl) imgEl.src = item.image;
        if (figEl) figEl.style.display = 'block';
      } else {
        if (figEl) figEl.style.display = 'none';
      }

      // 5. Bold Lead Box
      const leadBox = document.getElementById('readerLeadHighlight');
      const leadText = document.getElementById('readerLeadText');
      if (item.summary) {
        if (leadText) leadText.textContent = item.summary;
        if (leadBox) leadBox.style.display = 'block';
      } else {
        if (leadBox) leadBox.style.display = 'none';
      }

      // 6. Full Body Paragraphs
      const pList = (item.body || '').split('\\n\\n')
        .map(p => p.trim())
        .filter(p => p.length > 0);

      const bodyEl = document.getElementById('readerEditorialBody');
      if (bodyEl) {
        let html = '';
        pList.forEach((p, idx) => {
          if (idx === 0 && item.summary && (p === item.summary || item.summary.startsWith(p.substring(0, 50)))) {
            return;
          }
          html += '<p>' + p + '</p>';
        });
        bodyEl.innerHTML = html;
      }

      // 7. Topic Tags
      const tagsWrap = document.getElementById('readerArticleTags');
      if (tagsWrap) {
        const allTags = item.tags && item.tags.length > 0 ? item.tags : [catTitle, 'செய்திகள்', 'அறச்சுடர்'];
        tagsWrap.innerHTML = allTags.map(t => `<span class="category-tag-badge" style="cursor:default; font-size:0.75rem; margin-right:6px;">#${t}</span>`).join('');
      }

      // 8. Trigger Recommendation Agent
      RecommendationAgent.render(item);

      // 9. Update URL hash
      try {
        history.pushState(null, '', '#article/' + item.id);
      } catch(e) {}

      // 10. Scroll smoothly to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function closeFullArticlePage() {
      stopAudioReadAloud();
      const reader = document.getElementById('fullArticleReaderContainer');
      if (reader) reader.style.display = 'none';

      if (currentCategory === 'home' || currentCategory === 'all') {
        showHeroAndWires();
        const staticGrid = document.getElementById('bloggerStaticPostsGrid');
        if (staticGrid) staticGrid.style.display = 'grid';
      } else {
        const catSection = document.getElementById('categoryDynamicSection');
        if (catSection) catSection.style.display = 'block';
      }

      try {
        history.pushState(null, '', window.location.pathname + window.location.search);
      } catch(e) {}

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function openArticleModalById(id) {
      openFullArticlePage(id);
    }
"""

def update_file(path: Path):
    text = path.read_text(encoding="utf-8")

    # 1. Inject CSS if not present
    if "#fullArticleReaderContainer" not in text:
        skin_pos = text.find("]]></b:skin>")
        if skin_pos != -1:
            text = text[:skin_pos] + "\n" + READER_CSS + "\n" + text[skin_pos:]
        else:
            style_pos = text.find("</style>")
            if style_pos != -1:
                text = text[:style_pos] + "\n" + READER_CSS + "\n" + text[style_pos:]
            else:
                print(f"Warning: Could not find style injection spot in {path}")

    # 2. Inject HTML right above </main> or right before footer
    if 'id="fullArticleReaderContainer"' not in text:
        main_dyn = text.find("</main>")
        if main_dyn != -1:
            text = text[:main_dyn] + "\n" + READER_HTML + "\n" + text[main_dyn:]
        else:
            footer_pos = text.find("<footer")
            if footer_pos != -1:
                text = text[:footer_pos] + "\n" + READER_HTML + "\n" + text[footer_pos:]
            else:
                print(f"Warning: Could not find HTML injection spot in {path}")

    # 3. Inject JS right after `let currentActiveArticleId = 1;`
    if "const RecommendationAgent = {" not in text:
        marker = "let currentActiveArticleId = 1;"
        idx = text.find(marker)
        if idx != -1:
            insert_pos = idx + len(marker)
            text = text[:insert_pos] + "\n" + READER_JS + "\n" + text[insert_pos:]
        else:
            print(f"Warning: Marker '{marker}' not found in {path}")

    # 4. Make sure window exports are present
    exports = [
        "window.openFullArticlePage = openFullArticlePage;",
        "window.closeFullArticlePage = closeFullArticlePage;",
        "window.RecommendationAgent = RecommendationAgent;"
    ]
    for exp in exports:
        if exp not in text:
            win_exp_pos = text.find("window.openArticleModalById = openArticleModalById;")
            if win_exp_pos != -1:
                text = text[:win_exp_pos] + exp + "\n    " + text[win_exp_pos:]
            else:
                script_end = text.rfind("</script>")
                if script_end != -1:
                    text = text[:script_end] + "\n    " + exp + "\n" + text[script_end:]

    path.write_text(text, encoding="utf-8")
    print(f"Successfully updated {path}")

def main():
    if THEME_PATH.exists():
        update_file(THEME_PATH)
    if CANONICAL_PATH.exists():
        update_file(CANONICAL_PATH)

if __name__ == "__main__":
    main()
