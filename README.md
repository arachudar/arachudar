# அறச்சுடர் (Arachudar) - Tamil News Automation Pipeline

**அறச்சுடர்** என்பது முன்னணி தமிழ் செய்தி ஊடகங்களில் இருந்து உடனுக்குடன் உண்மைச் செய்திகளையும் புகைப்படங்களையும் திரட்டி, NVIDIA NIM AI மூலம் சுருக்கமாகவும் எளிய நடையிலும் தொகுத்து, கூகிள் பிளாகர் மற்றும் சமூக ஊடகங்களில் தானியங்கியாக வெளியிடும் அதிநவீன தமிழ் செய்தி தளம் ஆகும்.

[![Arachudar Automation](https://github.com/arachudar/arachudar/actions/workflows/news_pipeline.yml/badge.svg)](https://github.com/arachudar/arachudar/actions/workflows/news_pipeline.yml)
[![Tests Passing](https://img.shields.io/badge/pytest-196%20passed-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.15-blue.svg)](https://www.python.org/)
[![Website](https://img.shields.io/badge/Blog-அறச்சுடர்-red.svg)](https://arachudar.blogspot.com/)

---

## 🌟 முதன்மை அம்சங்கள் (Key Features)

1. **15 முன்னணி தமிழ் செய்தி மூலங்கள் (15 Tamil News Sources)**:
   - **நாளிதழ்கள் (Daily Newspapers)**: தினத்தந்தி (Daily Thanthi), தினமலர் (Dinamalar), இந்து தமிழ் திசை (Hindu Tamil Thisai), தினமணி (Dinamani), மாலை மலர் (Maalai Malar), தினபூமி (Thinaboomi).
   - **டிஜிட்டல் தளங்கள் & இதழ்கள் (Digital News Portals)**: விகடன் (Vikatan), சமயம் தமிழ் (Samayam Tamil), ஒன்இந்தியா தமிழ் (Oneindia Tamil), பிபிசி தமிழ் (BBC News Tamil), நியூஸ்18 தமிழ் (News18 Tamil), ஜீ நியூஸ் தமிழ் (Zee News Tamil), ஏசியாநெட் தமிழ் (Asianet News Tamil).
   - **செய்தி திரட்டிகள் (Aggregators)**: கூகிள் நியூஸ் தமிழ் (Google News Tamil), W3Newspapers Directory.

2. **உண்மை புகைப்படங்கள் மட்டுமே (Real News Photographs Only)**:
   - செய்திகளில் உள்ள நேரடி புகைப்படங்கள் (Media RSS, Enclosures, OpenGraph, JSON-LD, Sitemap Images) மட்டுமே பெறப்படுகின்றன.
   - போலி படங்கள், தளம் சார்ந்த லோகோக்கள், விளம்பர ஐகான்கள் தானாக நிராகரிக்கப்பட்டு, 1200px அகலமுள்ள உயர் தெளிவுத்திறன் படங்கள் தொகுக்கப்படுகின்றன.

3. **NVIDIA NIM AI தமிழ் மொழியாக்கம் (NVIDIA AI Tamil Synthesis)**:
   - NVIDIA NIM API (`meta/llama-3.1-70b-instruct` / Nemotron) மூலம் இயற்கை எழில் கொஞ்சும் இனிய தமிழ் நடையில் செய்திகள் தொகுக்கப்படுகின்றன.
   - இலவச பயன்பாட்டுக்கான 40 RPM வரம்பை மீறாமல், வினாடிக்கு 0.5 அழைப்புகள் (30 RPM உச்சவரம்பு) டோக்கன் பக்கெட் வீதக் கட்டுப்பாடு (Token Bucket Rate Limiter) மூலம் முறைப்படுத்தப்படுகிறது.

4. **கூகிள் பிளாகர் நேரடி வெளியீடு (Google Blogger Integration)**:
   - கூகிள் OAuth2 மற்றும் Blogger API v3 மூலம் `https://arachudar.blogspot.com/` தளத்திற்கு தானாகவே வடிமைக்கப்பட்ட கட்டுரைகளாக (HTML Posts & Labels) வெளியிடப்படுகின்றன.

5. **இ-பேப்பர் மற்றும் செய்தி வலைப்பக்க கட்டமைப்பு (Dual-Layer HTML Newspaper)**:
   - `tamil-news-blogger.html` கோப்பில் உள்ள முதன்மை செய்தி (Lead Hero), தலைப்புச் செய்திகள் மற்றும் `NEWS_DATABASE` தானியங்கியாகப் புதுப்பிக்கப்படுகிறது.

6. **GitHub Actions தொடர் இயக்கம் (Scheduled CI/CD Pipeline)**:
   - 4 மணி நேர இடைவெளியில் (`0 */4 * * *`) சுழற்சி முறையில் தொடர்ந்து இயங்கும் வகையில் பாதுகாப்பாக கட்டமைக்கப்பட்டுள்ளது.
   - தேவைப்படும் போது `workflow_dispatch` மூலம் உடனடி செய்திப் புதுப்பிப்பும் சாத்தியம்.

---

## 🏗️ கோப்பு கட்டமைப்பு (Project Structure)

```
Arachudar/
├── .github/workflows/
│   └── news_pipeline.yml         # GitHub Actions CI/CD workflow
├── config/
│   └── sources.py                # 15 Tamil news sources configuration
├── data/
│   └── seen_articles.json        # Deduplication cache
├── src/
│   ├── aggregator/
│   │   ├── feed_fetcher.py       # Multi-source RSS/Atom/Sitemap fetcher
│   │   ├── image_extractor.py    # Real editorial image extractor & CDN resolver
│   │   └── deduplicator.py       # Fingerprint hashing & deduplication
│   ├── ai/
│   │   ├── rate_limiter.py       # Token-bucket rate limiter (<= 30 RPM)
│   │   ├── nvidia_client.py      # NVIDIA NIM API client with exponential backoff
│   │   └── tamil_synthesizer.py  # Authentic Tamil news synthesis
│   ├── publisher/
│   │   ├── html_populator.py     # Dual-layer newspaper layout populator
│   │   ├── blogger_client.py     # Blogger API v3 OAuth2 publisher
│   │   └── social_hooks.py       # Social media hooks (X, FB, IG, YT)
│   └── pipeline.py               # Master orchestration runner
├── scripts/
│   └── verify_dry_run.py         # Ephemeral dry-run verifier
├── tests/                        # 196-test hermetic verification harness
│   ├── test_infra_smoke.py       # Infrastructure & hermetic guard tests
│   ├── test_tier1_features.py    # Feature specification tests (F1-F14)
│   ├── test_tier2_boundaries.py  # Boundary & fault injection tests
│   ├── test_tier3_pairwise.py    # Pairwise integration tests
│   └── test_tier4_scenarios.py   # Full operational scenario tests
├── blogger-theme.xml             # Blogger theme template
├── tamil-news-blogger.html       # Standalone newspaper HTML template
└── requirements.txt              # Production Python dependencies
```

---

## ⚙️ இயக்கும் முறை (How to Run)

### 1. தேவைகளை நிறுவுதல் (Install Dependencies)
```bash
pip install -r requirements.txt
```

### 2. மெய்நிகர் சோதனை இயக்கம் (Dry-Run Verification)
உண்மையான இணைய வெளியீடுகள் இன்றி சோதிக்க:
```bash
python scripts/verify_dry_run.py
# அல்லது
python -m src.pipeline --dry-run --limit=5
```

### 3. முழுமையான சோதனை ஓட்டம் (Run Test Suite)
அனைத்து 196 சோதனைகளையும் இயக்க:
```bash
python -m pytest tests/
```

### 4. நேரடி வெளியீடு (Live Pipeline Execution)
சுற்றுச்சூழல் மாறிகளை அமைத்து இயக்கவும்:
```bash
export NVIDIA_API_KEY="nvapi-..."
export BLOGGER_BLOG_ID="563563588050874327"
export BLOGGER_CLIENT_ID="..."
export BLOGGER_CLIENT_SECRET="..."
export BLOGGER_REFRESH_TOKEN="..."

python -m src.pipeline --limit=5
```

---

## 🔒 GitHub Actions இரகசிய மாறிகள் (Repository Secrets)

GitHub Actions களஞ்சியத்தில் (`arachudar/arachudar`) பின்வரும் இரகசிய மாறிகள் உள்ளமைக்கப்பட்டுள்ளன:
- `NVIDIA_API_KEY`: NVIDIA NIM API விசை.
- `BLOGGER_BLOG_ID`: கூகிள் பிளாகர் அடையாள எண் (`563563588050874327`).
- `BLOGGER_CLIENT_ID`: கூகிள் OAuth Client ID.
- `BLOGGER_CLIENT_SECRET`: கூகிள் OAuth Client Secret.
- `BLOGGER_REFRESH_TOKEN`: கூகிள் OAuth Refresh Token.

---

## 📄 உரிமம் (License)
அறச்சுடர் தமிழ் செய்தி ஊடகம் © 2026. அனைத்து உரிமைகளும் பாதுகாக்கப்பட்டவை.

