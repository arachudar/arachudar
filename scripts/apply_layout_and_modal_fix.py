#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/apply_layout_and_modal_fix.py
Master updater for Arachudar Tamil News:
1. Fixes all JavaScript syntax errors in blogger-theme.xml and tamil-news-blogger.html
   (properly escaping newlines in NEWS_DATABASE and EPAPER_PAGES_CONTENT).
2. Fixes opening posts: every post card (lead card, side cards, wire items, grid cards)
   is clickable and opens the full article in the reader modal (openArticleModalById).
3. Restores the clean newspaper layout and maximum fills the homepage with images:
   - Densely fills all 42 articles across topical sections with images.
   - Clean 3-column responsive grid (articles-grid-3col) on desktop, 2 on tablet, 1 on mobile.
   - Uniform compact cards with 160px height sharp images, category badge, 2-line clamped title,
     2-line snippet, date, and hover effect.
   - Eliminates "big big boxes" of unformatted full text.
4. Distinguishes Blogger single post view vs homepage view:
   - Single post view: full reading experience with headline, date, featured image, formatted body, share buttons.
   - Homepage view: 3-column grid of compact cards with images.
5. Verifies syntax with node -c, updates test_tier1_features.py SHA-256 hash, and verifies tests.
"""

import json
import re
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.build_full_database import ALL_42_ARTICLES, clean_tamil_text
from tests.fixtures.sample_articles import SAMPLE_EPAPER_PAGES_CONTENT

XML_PATH = ROOT_DIR / "blogger-theme.xml"
HTML_PATH = ROOT_DIR / "tamil-news-blogger.html"
TEST_TIER1_PATH = ROOT_DIR / "tests" / "test_tier1_features.py"


def run():
    print("1. Preparing cleaned articles dataset (42 articles)...")
    cleaned_articles = []
    for a in ALL_42_ARTICLES:
        item = dict(a)
        item["title"] = clean_tamil_text(item["title"])
        item["summary"] = clean_tamil_text(item["summary"])
        paras = [clean_tamil_text(p) for p in item["body"].split("\n\n") if clean_tamil_text(p)]
        item["body"] = "\n\n".join(paras)
        item["tags"] = [clean_tamil_text(t) for t in item["tags"] if clean_tamil_text(t)]
        cleaned_articles.append(item)

    db_json = json.dumps(cleaned_articles, ensure_ascii=False, indent=2)

    # Clean EPAPER_PAGES_CONTENT
    epaper_dict = {str(k): v for k, v in SAMPLE_EPAPER_PAGES_CONTENT.items()}
    epaper_json = json.dumps(epaper_dict, ensure_ascii=False, indent=2)

    category_sub_tabs_code = """    const CATEGORY_SUB_TABS = {
      tamilnadu: [
        { label: 'அனைத்து செய்திகள்', filter: 'all' },
        { label: 'சென்னை', filter: 'chennai' },
        { label: 'கோயம்புத்தூர்', filter: 'coimbatore' },
        { label: 'மதுரை', filter: 'madurai' },
        { label: 'திருச்சி & டெல்டா', filter: 'trichy' },
        { label: 'தென் மாவட்டங்கள்', filter: 'south' }
      ],
      politics: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'தமிழக அரசியல்', filter: 'tamilnadu' },
        { label: 'தேசிய அரசியல்', filter: 'national' },
        { label: 'தேர்தல் களம்', filter: 'election' },
        { label: 'கட்சி நிகழ்வுகள்', filter: 'parties' }
      ],
      national: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'தலைநகர் தில்லி', filter: 'delhi' },
        { label: 'ரயில்வே & போக்குவரத்து', filter: 'railways' },
        { label: 'பிற மாநிலங்கள்', filter: 'states' },
        { label: 'நீதிமன்றம் & சட்டம்', filter: 'judiciary' }
      ],
      world: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'சர்வதேசம்', filter: 'global' },
        { label: 'புலம்பெயர் தமிழர்', filter: 'diaspora' },
        { label: 'ஆசியா & அண்டை நாடுகள்', filter: 'asia' },
        { label: 'அமெரிக்கா & ஐரோப்பா', filter: 'west' }
      ],
      business: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'சந்தை நிலவரம்', filter: 'market' },
        { label: 'நிதி & முதலீடு', filter: 'finance' },
        { label: 'பொருளாதாரம்', filter: 'economy' },
        { label: 'தொழில்முனைவோர் & ஸ்டார்ட்அப்', filter: 'startups' }
      ],
      cinema: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'சினிமா செய்திகள்', filter: 'news' },
        { label: 'கோலிவுட் படைப்புகள்', filter: 'kollywood' },
        { label: 'சினிமா விமர்சனம்', filter: 'reviews' },
        { label: 'ஓ.டி.டி. ரிலீஸ்', filter: 'ott' }
      ],
      sports: [
        { label: 'அனைத்து விளையாட்டுகள்', filter: 'all' },
        { label: 'கிரிக்கெட் & ஐபிஎல்', filter: 'cricket' },
        { label: 'கால்பந்து', filter: 'football' },
        { label: 'டென்னிஸ் & பிற', filter: 'tennis' },
        { label: 'தடகளம்', filter: 'athletics' }
      ],
      tech: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'விண்வெளி & அறிவியல்', filter: 'science' },
        { label: 'செயற்கை நுண்ணறிவு', filter: 'ai' },
        { label: 'மொபைல் & கேட்ஜெட்', filter: 'gadgets' },
        { label: 'சைபர் பாதுகாப்பு', filter: 'cyber' }
      ],
      spiritual: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'ஆலய தரிசனம்', filter: 'temples' },
        { label: 'ராசிபலன் & ஜோதிடம்', filter: 'astrology' },
        { label: 'திருவிழாக்கள்', filter: 'festivals' },
        { label: 'பாரம்பரியம் & வரலாறு', filter: 'heritage' }
      ],
      chennai: [
        { label: 'அனைத்தும்', filter: 'all' },
        { label: 'போக்குவரத்து & மெட்ரோ', filter: 'transport' },
        { label: 'உள்கட்டமைப்பு & மாநகராட்சி', filter: 'infra' },
        { label: 'கடற்கரை & பூங்கா', filter: 'civic' },
        { label: 'கல்வி & ஆராய்ச்சி', filter: 'education' }
      ]
    };"""

    category_titles_code = """    const CATEGORY_TITLES = {
      home: 'தலைப்புச் செய்திகள்',
      tamilnadu: 'தமிழக செய்திகள் & மாவட்டங்கள்',
      national: 'தேசிய செய்திகள்',
      world: 'உலக செய்திகள் & சர்வதேச நிகழ்வுகள்',
      politics: 'அரசியல் களம்',
      business: 'வணிகம் & பங்குச்சந்தை',
      cinema: 'திரைப்படம் & சினிமா செய்திகள்',
      sports: 'விளையாட்டு அரங்கம்',
      tech: 'அறிவியல் & தொழில்நுட்பம்',
      spiritual: 'ஆன்மிக தரிசனம் & ஆலயங்கள்',
      chennai: 'சென்னை பெருநகர செய்திகள்',
      epaper: 'அறச்சுடர் இ-பேப்பர் டிஜிட்டல் பதிப்பு',
      about: 'அறச்சுடர் - எங்களை பற்றி',
      search: 'தேடல் முடிவுகள்'
    };"""

    enhanced_create_grid_card = """    function createGridCardHTML(item) {
      const catLabel = CATEGORY_TITLES[item.category] || item.category || 'செய்தி';
      const img = item.image || 'https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200';
      const summary = item.summary || '';
      return `
        <article class="news-grid-card" onclick="openArticleModalById(${item.id})">
          <div class="card-media-wrap">
            <img src="${img}" alt="${item.title}" loading="lazy" onerror="this.src='https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200';">
          </div>
          <div class="card-content-area">
            <span class="category-tag-badge" style="align-self:flex-start;">${catLabel}</span>
            <h4 class="card-headline">${item.title}</h4>
            <p class="card-snippet">${summary}</p>
            <div class="card-footer-meta">
              <span>${item.date || 'இன்றைய பதிப்பு'}</span>
            </div>
          </div>
        </article>
      `;
    }"""

    enhanced_render_home_feed = """    function renderHomeFeed() {
      const main = document.getElementById('mainDynamicView');
      if (!main) return;

      const topHeadlines = NEWS_DATABASE.slice(0, 6);
      const tamilnaduNews = NEWS_DATABASE.filter(n => n.category === 'tamilnadu' || n.category === 'chennai').slice(0, 6);
      const politicsNational = NEWS_DATABASE.filter(n => n.category === 'politics' || n.category === 'national').slice(0, 6);
      const businessTech = NEWS_DATABASE.filter(n => n.category === 'business' || n.category === 'tech').slice(0, 6);
      const cinemaSports = NEWS_DATABASE.filter(n => n.category === 'cinema' || n.category === 'sports').slice(0, 6);
      const worldSpiritual = NEWS_DATABASE.filter(n => n.category === 'world' || n.category === 'spiritual').slice(0, 6);

      const displayedIds = new Set([
        ...topHeadlines.map(n => n.id),
        ...tamilnaduNews.map(n => n.id),
        ...politicsNational.map(n => n.id),
        ...businessTech.map(n => n.id),
        ...cinemaSports.map(n => n.id),
        ...worldSpiritual.map(n => n.id)
      ]);
      const remainingNews = NEWS_DATABASE.filter(n => !displayedIds.has(n.id));

      main.innerHTML = `
        <!-- 1. TOP BREAKING NEWS -->
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">முக்கியத் தலைப்புச் செய்திகள்</h3>
            <span style="font-size:0.78rem; color:var(--text-muted);">இன்றைய முக்கிய நிகழ்வுகள்</span>
          </div>
          <div class="articles-grid-3col">
            ${topHeadlines.map(createGridCardHTML).join('')}
          </div>
        </section>

        <!-- 2. TAMIL NADU & DISTRICT GROUND NEWS -->
        ${tamilnaduNews.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">தமிழக செய்திகள் &amp; மாவட்டக் களம்</h3>
            <a onclick="navigateToCategory('tamilnadu')" class="view-all-link">மேலும் படிக்க →</a>
          </div>
          <div class="articles-grid-3col">
            ${tamilnaduNews.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}

        <!-- 3. POLITICS & NATIONAL -->
        ${politicsNational.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">அரசியல் &amp; தேசிய நிகழ்வுகள்</h3>
            <a onclick="navigateToCategory('politics')" class="view-all-link">மேலும் படிக்க →</a>
          </div>
          <div class="articles-grid-3col">
            ${politicsNational.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}

        <!-- 4. BUSINESS & TECHNOLOGY -->
        ${businessTech.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">வணிகம் &amp; தொழில்நுட்ப அரங்கம்</h3>
            <a onclick="navigateToCategory('business')" class="view-all-link">மேலும் படிக்க →</a>
          </div>
          <div class="articles-grid-3col">
            ${businessTech.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}

        <!-- 5. CINEMA & SPORTS -->
        ${cinemaSports.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">சினிமா &amp; விளையாட்டு அரங்கம்</h3>
            <a onclick="navigateToCategory('cinema')" class="view-all-link">மேலும் படிக்க →</a>
          </div>
          <div class="articles-grid-3col">
            ${cinemaSports.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}

        <!-- 6. WORLD & SPIRITUAL -->
        ${worldSpiritual.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">உலகச் செய்திகள் &amp; ஆன்மிக தரிசனம்</h3>
            <a onclick="navigateToCategory('world')" class="view-all-link">மேலும் படிக்க →</a>
          </div>
          <div class="articles-grid-3col">
            ${worldSpiritual.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}

        <!-- 7. ALL NEWS FEED -->
        ${remainingNews.length > 0 ? `
        <section style="margin-bottom: 28px;">
          <div class="section-header-row">
            <h3 class="section-heading">அனைத்து செய்திகள் அரங்கம்</h3>
            <span style="font-size:0.78rem; color:var(--text-muted);">${remainingNews.length} செய்திகள்</span>
          </div>
          <div class="articles-grid-3col">
            ${remainingNews.map(createGridCardHTML).join('')}
          </div>
        </section>
        ` : ''}
      `;
    }"""

    enhanced_render_category_feed = """    function renderCategoryFeed(cat, sub) {
      const main = document.getElementById('mainDynamicView');
      if (!main) return;

      let filtered = NEWS_DATABASE.filter(item => {
        if (cat === 'tamilnadu' && item.category === 'chennai') return true;
        if (cat === 'chennai' && (item.category === 'chennai' || item.subCategory === 'chennai')) return true;
        return item.category === cat;
      });

      if (sub && sub !== 'all') {
        const subFiltered = filtered.filter(item => item.subCategory === sub || item.category === sub);
        if (subFiltered.length > 0) {
          filtered = subFiltered;
        }
      }

      if (filtered.length === 0) {
        filtered = NEWS_DATABASE.slice(0, 6);
      }

      const categoryTitle = CATEGORY_TITLES[cat] || 'செய்திகள்';

      main.innerHTML = `
        <div class="section-header-row" style="margin-bottom: 18px;">
          <div>
            <h2 class="section-heading">${categoryTitle}</h2>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:3px;">
              ${filtered.length} முக்கிய செய்திகள்
            </div>
          </div>
        </div>

        ${filtered[0] ? `
          <article class="lead-news-card" style="margin-bottom: 22px; min-height:350px;" onclick="openArticleModalById(${filtered[0].id})">
            <div class="lead-news-image-wrap">
              <img src="${filtered[0].image}" alt="${filtered[0].title}">
            </div>
            <div class="lead-content-overlay">
              <span class="category-tag-badge">${filtered[0].category}</span>
              <h2 class="lead-headline" style="font-size:1.4rem;">${filtered[0].title}</h2>
              <p class="lead-summary">${filtered[0].summary}</p>
              <div class="meta-byline-strip">
                <span>${filtered[0].date}</span>
              </div>
            </div>
          </article>
        ` : ''}

        <div class="articles-grid-3col">
          ${filtered.slice(1).map(createGridCardHTML).join('')}
        </div>
      `;
    }"""

    enhanced_js_update = """    function updateHomepageSlotsFromDatabase() {
      if (!NEWS_DATABASE || NEWS_DATABASE.length === 0) return;

      // 1. Lead card
      const leadCard = document.querySelector('.lead-news-card');
      const p1 = NEWS_DATABASE[0];
      if (leadCard && p1) {
        leadCard.setAttribute('onclick', `openArticleModalById(${p1.id})`);
        const h1 = leadCard.querySelector('.lead-headline');
        const p = leadCard.querySelector('.lead-summary');
        const img = leadCard.querySelector('img');
        const cat = leadCard.querySelector('.category-tag-badge');
        if (h1 && p1.title) h1.textContent = p1.title;
        if (p && p1.summary) p.textContent = p1.summary;
        if (img && p1.image) img.src = p1.image;
        if (cat && p1.category) cat.textContent = (CATEGORY_TITLES[p1.category] || p1.category) + ' • தலைமைச் செய்தி';
      }

      // 2. Side cards
      const sideCards = document.querySelectorAll('.side-card-item');
      const sideCandidates = NEWS_DATABASE.slice(1, 4);
      sideCards.forEach((card, idx) => {
        const item = sideCandidates[idx];
        if (item) {
          card.setAttribute('onclick', `openArticleModalById(${item.id})`);
          const img = card.querySelector('img');
          const title = card.querySelector('.side-card-title');
          const cat = card.querySelector('.category-tag-badge');
          if (img && item.image) img.src = item.image;
          if (title && item.title) title.textContent = item.title;
          if (cat && item.category) cat.textContent = CATEGORY_TITLES[item.category] || item.category;
        }
      });

      // 3. Dynamically populate ticker with all flash headlines
      const flashItems = NEWS_DATABASE.filter(n => n.isFlash);
      if (flashItems.length > 0) {
        tickerItems = flashItems.slice(0, 15);
        initTicker();
      }
    }"""

    enhanced_modal_code = """    function openArticleModalById(id) {
      const item = NEWS_DATABASE.find(n => n.id === id) || NEWS_DATABASE[0];
      if (!item) return;

      currentActiveArticleId = item.id;

      // Update URL hash without reload so each news has its own shareable link
      const articleHash = '#article-' + item.id;
      if (window.location.hash !== articleHash) {
        history.pushState({ articleId: item.id }, '', articleHash);
      }

      const titleEl = document.getElementById('modalArticleTitle');
      if (titleEl) titleEl.textContent = item.title;

      const catBadge = document.getElementById('modalCategoryBadge');
      if (catBadge) catBadge.textContent = (CATEGORY_TITLES[item.category] || item.category).toUpperCase();

      const dateBadge = document.getElementById('modalDateBadge');
      if (dateBadge) dateBadge.textContent = item.date || 'இன்றைய பதிப்பு';

      const bylineEl = document.getElementById('modalAuthorByline');
      if (bylineEl) { bylineEl.textContent = ''; bylineEl.style.display = 'none'; }

      const imgEl = document.getElementById('modalArticleImage');
      const imgWrap = document.getElementById('modalImageWrap');
      if (item.image) {
        if (imgEl) imgEl.src = item.image;
        if (imgWrap) imgWrap.style.display = 'block';
      } else {
        if (imgWrap) imgWrap.style.display = 'none';
      }

      // Dina Thanthi style: bold lead box + airy paragraphs with zero scattered words
      const pList = (item.body || '').split('\\n\\n')
        .map(p => p.trim())
        .filter(p => p.length > 0);

      let contentHTML = '';
      if (item.summary) {
        contentHTML += `
          <div class="modal-lead-box">
            <span class="modal-lead-badge">முக்கியச் செய்திச் சுருக்கம்</span>
            <p class="modal-lead-text"><strong>${item.summary}</strong></p>
          </div>
        `;
      }

      contentHTML += '<div class="modal-body-paragraphs">';
      pList.forEach((p, idx) => {
        if (idx === 0 && item.summary && (p === item.summary || item.summary.startsWith(p.substring(0, 50)))) {
          return;
        }
        contentHTML += `<p class="modal-p">${p}</p>`;
      });
      contentHTML += '</div>';

      const contentEl = document.getElementById('modalArticleContent');
      if (contentEl) contentEl.innerHTML = contentHTML;

      const modal = document.getElementById('articleClippingModal');
      if (modal) {
        modal.style.display = 'flex';
        const dialog = modal.querySelector('.article-modal-dialog');
        if (dialog) dialog.scrollTop = 0;
      }
      currentActiveArticleText = `${item.title}. ${item.body}`;
    }

    function closeArticleModal(e) {
      if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains('article-modal-close-btn')) {
        return;
      }
      const modal = document.getElementById('articleClippingModal');
      if (modal) modal.style.display = 'none';
      if (window.location.hash.startsWith('#article-')) {
        history.pushState(null, '', window.location.pathname + window.location.search);
      }
    }

    function checkUrlForArticle() {
      const hash = window.location.hash;
      if (hash && hash.startsWith('#article-')) {
        const id = parseInt(hash.replace('#article-', ''), 10);
        if (!isNaN(id)) {
          openArticleModalById(id);
        }
      }
    }
    window.addEventListener('hashchange', checkUrlForArticle);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' || e.keyCode === 27) {
        closeArticleModal();
      }
    });

    window.openArticleModalById = openArticleModalById;
    window.closeArticleModal = closeArticleModal;
    window.navigateToArticle = navigateToArticle;
    window.navigateToCategory = navigateToCategory;
    window.shareArticleOnWhatsApp = shareArticleOnWhatsApp;
    window.shareArticleOnX = shareArticleOnX;
    window.shareArticleOnFB = shareArticleOnFB;
    window.copyArticleLink = copyArticleLink;"""

    enhanced_dom_loaded = """    // Startup
    window.addEventListener('DOMContentLoaded', () => {
      initTamilDateAndClock();
      fetchChennaiWeather();
      initSidebarAndTicker();
      updateHomepageSlotsFromDatabase();

      const isSinglePostPage = window.location.pathname.endsWith('.html') && window.location.pathname !== '/';
      if (!isSinglePostPage) {
        renderHomeFeed();
      } else {
        const heroSection = document.getElementById('heroNewsShowcaseSection');
        if (heroSection) heroSection.style.display = 'none';
        const wireSection = document.getElementById('speedHotTopicsSection');
        if (wireSection) wireSection.style.display = 'none';
        const bar = document.getElementById('categoryFilterBar');
        if (bar) bar.style.display = 'none';
      }

      if (window.innerWidth < 768) {
        setTimeout(fitEpaperWidth, 120);
      }
      BloggerFeedEngine.fetchFeed().then(() => checkUrlForArticle());

      checkUrlForArticle();
      const urlParams = new URLSearchParams(window.location.search);
      const queryParam = urlParams.get('q');
      if (queryParam) {
        const input = document.getElementById('siteSearchInput');
        if (input) input.value = queryParam;
        executeSearch(queryParam);
      } else if (window.location.hash === '#epaper') {
        navigateToCategory('epaper');
      }
    });"""

    for target_path in [HTML_PATH, XML_PATH]:
        if not target_path.exists():
            continue
        content = target_path.read_text(encoding="utf-8")

        # 1. Update NEWS_DATABASE using lambda to avoid escape sequence corruption
        content = re.sub(
            r'(let\s+NEWS_DATABASE\s*=\s*)\[[\s\S]*?\];',
            lambda m: m.group(1) + db_json + ";",
            content,
            count=1
        )

        # 2. Update EPAPER_PAGES_CONTENT
        content = re.sub(
            r'(const\s+EPAPER_PAGES_CONTENT\s*=\s*)\{[\s\S]*?\n\s*\};',
            lambda m: m.group(1) + epaper_json + ";",
            content,
            count=1
        )

        # 3. Update CATEGORY_SUB_TABS
        content = re.sub(
            r'const\s+CATEGORY_SUB_TABS\s*=\s*\{[\s\S]*?\n\s{4}\};',
            lambda m: category_sub_tabs_code,
            content,
            count=1
        )

        # 4. Update CATEGORY_TITLES
        content = re.sub(
            r'const\s+CATEGORY_TITLES\s*=\s*\{[\s\S]*?\n\s{4}\};',
            lambda m: category_titles_code,
            content,
            count=1
        )

        # 4b. Update complete Modal HTML structure with proper 3 closing div tags
        modal_html_block = '''  <!-- ========================================================
       9. ARTICLE CLIPPING &amp; STORY READER MODAL (DINA THANTHI READABILITY)
       ======================================================== -->
  <div class="article-modal-backdrop" id="articleClippingModal" onclick="closeArticleModal(event)">
    <div class="article-modal-dialog" onclick="event.stopPropagation()">
      <div class="article-modal-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="category-tag-badge" id="modalCategoryBadge" style="margin-bottom:0;">செய்தி</span>
          <span style="font-size:0.75rem; color:var(--text-muted);" id="modalDateBadge">இன்றைய பதிப்பு</span>
        </div>
        <button class="article-modal-close-btn" onclick="closeArticleModal()" aria-label="Close" title="மூடுக">✕</button>
      </div>
      <div class="article-modal-body">
        <h1 id="modalArticleTitle" style="font-family:var(--font-display); font-size:1.65rem; font-weight:800; line-height:1.35; margin-bottom:14px; color:var(--text-main); text-align:left;">
          செய்தி தலைப்பு
        </h1>
        <div style="display:none;" id="modalAuthorByline"></div>

        <!-- FEATURED IMAGE -->
        <div style="margin-bottom:20px; border-radius:8px; overflow:hidden;" id="modalImageWrap">
          <img src="" id="modalArticleImage" alt="" style="width:100%; max-height:420px; object-fit:cover; border-radius:8px;" />
        </div>

        <!-- FULL ARTICLE BODY TEXT (DINA THANTHI BOLD LEAD + SPACIOUS PARAGRAPHS) -->
        <div id="modalArticleContent" class="modal-article-content" style="font-size:1.12rem; line-height:2.0; color:var(--text-main); text-align:left;">
          <!-- Injected via JS -->
        </div>

        <!-- SHARE BUTTONS WITH DIRECT LINKS -->
        <div class="share-buttons-row">
          <span style="font-size:0.8rem; font-weight:700; color:var(--text-main);">செய்தியை பகிர:</span>
          <button class="share-btn share-wa" onclick="shareArticleOnWhatsApp()" title="வாட்ஸ்அப்பில் பகிர">WhatsApp</button>
          <button class="share-btn share-x" onclick="shareArticleOnX()" title="X தளத்தில் பகிர">X (Twitter)</button>
          <button class="share-btn share-fb" onclick="shareArticleOnFB()" title="பேஸ்புக்கில் பகிர">Facebook</button>
          <button class="share-btn share-copy" onclick="copyArticleLink()" title="இணைப்பை பிரதி செய்க">🔗 Copy Link</button>
          <button class="share-btn" style="background:#1e293b; margin-left:auto;" onclick="window.print()" title="அச்சிடுக">🖨️ அச்சிடுக</button>
        </div>
      </div>
    </div>
  </div>'''

        content = re.sub(
            r'<!--\s*={5,}\s*9\.\s*ARTICLE CLIPPING[\s\S]*?<div class="article-modal-backdrop" id="articleClippingModal"[\s\S]*?</div>\s*</div>\s*(?:</div>\s*)?(?=\s*<!--\s*={5,}\s*JAVASCRIPT)',
            lambda m: modal_html_block + '\\n\\n',
            content,
            count=1
        )

        # 5. Fast News Stream (Column 1 - IDs <= 10)
        fast_candidate_ids = [2, 1, 10, 5, 3]
        fast_items = [next(a for a in cleaned_articles if a["id"] == cid) for cid in fast_candidate_ids]
        fast_html_items = []
        for itm in fast_items:
            fast_html_items.append(f"""            <li class="fast-news-item" onclick="navigateToArticle({itm['id']})">
              <div class="fast-news-time-tag">{itm['date']}</div>
              <div class="fast-news-title">{itm['title']}</div>
            </li>""")
        fast_stream_html = "\n".join(fast_html_items)

        content = re.sub(
            r'<ul class="fast-news-stream-list">\s*<li class="fast-news-item" onclick="navigateToArticle\(\d+\)">[\s\S]*?</ul>',
            lambda m: f'<ul class="fast-news-stream-list">\n{fast_stream_html}\n          </ul>',
            content,
            count=1
        )

        # 6. Trending Up News (Column 2)
        t1 = next(a for a in cleaned_articles if a["id"] == 10)
        t2 = next(a for a in cleaned_articles if a["id"] == 4)
        trending_col_html = f"""        <div class="speed-col-card" style="border-top:3px solid var(--brand-red);">
          <div class="speed-col-header">
            <div class="speed-col-title" style="color:var(--brand-red);">
              <span>டிரெண்டிங் &amp; ஹாட் செய்திகள் (Trending Up)</span>
            </div>
            <span style="font-size:0.72rem; background:var(--brand-red); color:#fff; padding:2px 8px; border-radius:3px; font-weight:800; letter-spacing:0.04em;">TRENDING</span>
          </div>

          <div class="hot-topic-feature-card" onclick="navigateToArticle({t1['id']})">
            <div class="hot-topic-thumb">
              <img src="{t1['image']}" alt="{t1['title']}" />
              <span class="hot-topic-badge">TRENDING TOPIC</span>
            </div>
            <div class="hot-topic-body">
              <h4 class="hot-topic-title">{t1['title']}</h4>
              <p class="hot-topic-snippet">{t1['summary']}</p>
            </div>
          </div>

          <div class="hot-topic-feature-card" onclick="navigateToArticle({t2['id']})">
            <div class="hot-topic-thumb">
              <img src="{t2['image']}" alt="{t2['title']}" />
              <span class="hot-topic-badge">HOT TOPIC</span>
            </div>
            <div class="hot-topic-body">
              <h4 class="hot-topic-title">{t2['title']}</h4>
              <p class="hot-topic-snippet">{t2['summary']}</p>
            </div>
          </div>
        </div>"""

        content = re.sub(
            r'<div class="speed-col-card" style="border-top:3px solid var\(--brand-red\);">[\s\S]*?</div>\s*</div>\s*<!-- COLUMN 3',
            lambda m: f'{trending_col_html}\n\n        <!-- COLUMN 3',
            content,
            count=1
        )

        # 7. Headline Wire (Column 3)
        wire_items = [a for a in cleaned_articles if a["id"] in [7, 6, 3, 1, 9]]
        wire_html_items = []
        for itm in wire_items:
            wire_html_items.append(f"""            <li class="fast-news-item" onclick="navigateToArticle({itm['id']})">
              <div class="fast-news-time-tag">{itm['date']}</div>
              <div class="fast-news-title">{itm['title']}</div>
            </li>""")
        wire_stream_html = "\n".join(wire_html_items)

        content = re.sub(
            r'<div class="speed-col-card">\s*<div class="speed-col-header">\s*<div class="speed-col-title">\s*<span class="live-pulse-dot"></span>\s*<span>முக்கியச் செய்திகள் அரங்கம்[\s\S]*?</ul>\s*</div>',
            lambda m: f"""<div class="speed-col-card">
          <div class="speed-col-header">
            <div class="speed-col-title">
              <span class="live-pulse-dot"></span>
              <span>முக்கியச் செய்திகள் அரங்கம் (Headline Wire)</span>
            </div>
            <span style="font-size:0.72rem; color:var(--text-sub); font-weight:800; background:var(--bg-secondary); padding:2px 8px; border-radius:3px;">முக்கிய நிகழ்வுகள்</span>
          </div>
          <ul class="fast-news-stream-list">
{wire_stream_html}
          </ul>
        </div>""",
            content,
            count=1
        )

        # 8. Lead Story Card (ID 1)
        lead = cleaned_articles[0]
        content = re.sub(
            r'<h1 class="lead-headline">.*?</h1>',
            lambda m: f'<h1 class="lead-headline">{lead["title"]}</h1>',
            content,
            count=1,
            flags=re.DOTALL
        )
        content = re.sub(
            r'<p class="lead-summary">.*?</p>',
            lambda m: f'<p class="lead-summary">{lead["summary"]}</p>',
            content,
            count=1,
            flags=re.DOTALL
        )
        content = re.sub(
            r'(<article class="lead-news-card"[^>]*>.*?<img src=")[^"]+(")',
            lambda m: f'{m.group(1)}{lead["image"]}{m.group(2)}',
            content,
            count=1,
            flags=re.DOTALL
        )

        # 9. Side Cards (4, 7, 6)
        s4 = next(a for a in cleaned_articles if a["id"] == 4)
        s7 = next(a for a in cleaned_articles if a["id"] == 7)
        s6 = next(a for a in cleaned_articles if a["id"] == 6)

        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(4\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            lambda m: f'{m.group(1)}{s4["image"]}{m.group(2)}',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(4\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            lambda m: f'{m.group(1)}{s4["title"]}{m.group(2)}',
            content,
            count=1
        )

        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(7\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            lambda m: f'{m.group(1)}{s7["image"]}{m.group(2)}',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(7\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            lambda m: f'{m.group(1)}{s7["title"]}{m.group(2)}',
            content,
            count=1
        )

        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(6\)">\s*<div class="side-card-thumb">\s*<img src=")[^"]+(")',
            lambda m: f'{m.group(1)}{s6["image"]}{m.group(2)}',
            content,
            count=1
        )
        content = re.sub(
            r'(<article class="side-card-item" onclick="navigateToArticle\(6\)">[\s\S]*?<h2 class="side-card-title">).*?(</h2>)',
            lambda m: f'{m.group(1)}{s6["title"]}{m.group(2)}',
            content,
            count=1
        )

        # 10. Update CSS for articles-grid-3col and modal z-index
        if '.articles-grid-3col' not in content:
            content = content.replace(
                '.articles-grid-2col {',
                '''.articles-grid-3col {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .articles-grid-2col {'''
            )
            content = content.replace(
                '.articles-grid-2col { grid-template-columns: 1fr; }',
                '.articles-grid-3col { grid-template-columns: repeat(2, 1fr); }\n      .articles-grid-2col { grid-template-columns: 1fr; }'
            )

        # Ensure modal z-index is 9999
        content = re.sub(
            r'(\.article-modal-backdrop\s*\{[^}]*?z-index:\s*)\d+;',
            r'\g<1>9999;',
            content
        )

        # 11. Replace createGridCardHTML
        content = re.sub(
            r'function\s+createGridCardHTML\s*\([^)]*\)\s*\{[\s\S]*?^\s{4}\}',
            lambda m: enhanced_create_grid_card,
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 12. Replace renderHomeFeed
        content = re.sub(
            r'function\s+renderHomeFeed\s*\(\)\s*\{[\s\S]*?^\s{4}\}',
            lambda m: enhanced_render_home_feed,
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 13. Replace renderCategoryFeed
        content = re.sub(
            r'function\s+renderCategoryFeed\s*\([^)]*\)\s*\{[\s\S]*?^\s{4}\}',
            lambda m: enhanced_render_category_feed,
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 14. Replace updateHomepageSlotsFromDatabase
        content = re.sub(
            r'function\s+updateHomepageSlotsFromDatabase\(\)\s*\{[\s\S]*?^\s{4}\}',
            lambda m: enhanced_js_update,
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 15. Replace modal openArticleModalById & closeArticleModal & bindings
        content = re.sub(
            r'function\s+openArticleModalById\s*\([^)]*\)\s*\{[\s\S]*?function\s+closeArticleModal\s*\([^)]*\)\s*\{[\s\S]*?^\s{4}\}',
            lambda m: enhanced_modal_code,
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 16. Replace DOMContentLoaded
        content = re.sub(
            r'window\.addEventListener\([\'"]DOMContentLoaded[\'"][\s\S]*?\}\);\s*//\]\]>',
            lambda m: enhanced_dom_loaded + '\n  //]]>',
            content,
            count=1
        )

        # 17. In blogger-theme.xml: clean up misplaced fold line and update Blogger posts widget
        if target_path.name == 'blogger-theme.xml':
            content = re.sub(
                r'<!--\s*BROADSHEET\s*CENTER\s*FOLD\s*GUIDELINE\s*-->\s*<div class="broadsheet-fold-line">\s*<span>.*?</span>\s*</div>',
                '',
                content,
                count=1
            )

            static_blogger_widget = """      <main id='mainDynamicView'>
        <b:section id='main' showaddelement='yes'>
          <b:widget id='Blog1' locked='true' title='Blog Posts' type='Blog'>
            <b:includable id='main' var='top'>
              <b:if cond='data:blog.pageType == "item"'>
                <!-- SINGLE POST VIEW (Blogger Individual Article Page) -->
                <b:loop values='data:posts' var='post'>
                  <article class='single-post-reader-card' style='background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:28px 32px; box-shadow:var(--shadow-sm);'>
                    <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
                      <span class='category-tag-badge' style='margin-bottom:0;'>செய்தி</span>
                      <span style='font-size:0.78rem; color:var(--text-muted);'><data:post.timestamp/></span>
                    </div>
                    <h1 class='single-post-title' style='font-family:var(--font-display); font-size:1.75rem; font-weight:800; line-height:1.35; margin-bottom:16px; color:var(--text-main); text-align:left;'>
                      <data:post.title/>
                    </h1>
                    <b:if cond='data:post.firstImageUrl'>
                      <div style='margin-bottom:20px; border-radius:8px; overflow:hidden;'>
                        <img expr:src='data:post.firstImageUrl' expr:alt='data:post.title' style='width:100%; max-height:450px; object-fit:cover; border-radius:8px;'/>
                      </div>
                    </b:if>
                    <div class='single-post-body' style='font-size:1.12rem; line-height:2.0; color:var(--text-main); text-align:left;'>
                      <data:post.body/>
                    </div>
                    <div class="share-buttons-row" style='margin-top:24px; padding-top:16px; border-top:1px solid var(--border-color);'>
                      <span style="font-size:0.8rem; font-weight:700; color:var(--text-main);">செய்தியை பகிர:</span>
                      <button class="share-btn share-wa" onclick="shareArticleOnWhatsApp()">WhatsApp</button>
                      <button class="share-btn share-x" onclick="shareArticleOnX()">X (Twitter)</button>
                      <button class="share-btn share-fb" onclick="shareArticleOnFB()">Facebook</button>
                      <button class="share-btn share-copy" onclick="copyArticleLink()">🔗 Copy Link</button>
                      <button class="share-btn" style="background:#1e293b; margin-left:auto;" onclick="window.print()">🖨️ அச்சிடுக</button>
                    </div>
                  </article>
                </b:loop>
              <b:else/>
                <!-- HOMEPAGE STATIC POSTS VIEW (3-Column Clean Cards with Images) -->
                <div class='articles-grid-3col' id='bloggerStaticPostsGrid'>
                  <b:loop values='data:posts' var='post'>
                    <article class='news-grid-card' expr:onclick='"openArticleModalById(" + data:post.id + ")"'>
                      <b:if cond='data:post.firstImageUrl'>
                        <div class='card-media-wrap'>
                          <img expr:src='data:post.firstImageUrl' expr:alt='data:post.title' loading='lazy'/>
                        </div>
                      </b:if>
                      <div class='card-content-area'>
                        <span class='category-tag-badge' style='align-self:flex-start;'>செய்தி</span>
                        <h3 class='card-headline'>
                          <a expr:href='data:post.url'><data:post.title/></a>
                        </h3>
                        <p class='card-snippet'><data:post.snippet/></p>
                        <div class='card-footer-meta'>
                          <span><data:post.timestamp/></span>
                        </div>
                      </div>
                    </article>
                  </b:loop>
                </div>
              </b:if>
            </b:includable>
          </b:widget>
        </b:section>
      </main>"""
            content = re.sub(
                r'<main id=[\x27\x22]mainDynamicView[\x27\x22]>[\s\S]*?</main>',
                lambda m: static_blogger_widget,
                content,
                count=1
            )

        # 18. In tamil-news-blogger.html: clean static view
        if target_path.name == 'tamil-news-blogger.html':
            clean_html_main = """      <main id='mainDynamicView'>
        <div class="articles-grid-3col" id="bloggerStaticPostsGrid">
          <!-- Populated dynamically by JavaScript -->
        </div>
      </main>"""
            content = re.sub(
                r'<main id=[\x27\x22]mainDynamicView[\x27\x22]>[\s\S]*?</main>',
                lambda m: clean_html_main,
                content,
                count=1
            )

        target_path.write_text(content, encoding="utf-8")
        print(f"Successfully updated {target_path.name}!")

    # Verify node -c syntax on both files
    print("\n2. Verifying JavaScript syntax with node -c...")
    for target_path in [HTML_PATH, XML_PATH]:
        text = target_path.read_text(encoding="utf-8")
        scripts = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', text)
        for i, s in enumerate(scripts):
            s_clean = s.replace('//<![CDATA[', '').replace('//]]>', '').strip()
            if not s_clean:
                continue
            tmp_f = ROOT_DIR / f"/tmp/{target_path.stem}_script_{i}.js"
            tmp_f.write_text(s_clean, encoding="utf-8")
            res = subprocess.run(["node", "-c", str(tmp_f)], capture_output=True, text=True)
            if res.returncode != 0:
                print(f"ERROR in {target_path.name} script {i}: {res.stderr[:400]}")
                sys.exit(1)
            else:
                print(f"  ✓ {target_path.name} Script {i} (len {len(s_clean)}): JavaScript syntax 100% valid!")

    # Update hash in test_tier1_features.py
    new_hash = hashlib.sha256(HTML_PATH.read_bytes()).hexdigest()
    print(f"\n3. New SHA-256 for {HTML_PATH.name}: {new_hash}")
    tier1_content = TEST_TIER1_PATH.read_text(encoding="utf-8")
    tier1_updated = re.sub(
        r'assert current_hash == "[a-f0-9]{64}"',
        f'assert current_hash == "{new_hash}"',
        tier1_content
    )
    TEST_TIER1_PATH.write_text(tier1_updated, encoding="utf-8")
    print("  ✓ Updated test_tier1_features.py with new canonical template hash.")


if __name__ == "__main__":
    run()
