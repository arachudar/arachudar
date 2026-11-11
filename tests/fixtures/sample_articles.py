"""
tests/fixtures/sample_articles.py - RawArticle and ProcessedArticle Data Contracts & Fixtures.
Defines canonical dataclasses and sample collections covering multiple news categories,
homepage DOM slot IDs, dynamic JavaScript NEWS_DATABASE arrays, and EPAPER_PAGES_CONTENT schemas.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# ============================================================================
# Dataclass Contracts (PROJECT.md Interface Contracts)
# ============================================================================

@dataclass
class RawArticle:
    """M1 (Aggregator) -> M2 (AI Synthesizer) Interface Contract."""
    source_id: str          # e.g. "daily_thanthi", "dinamalar"
    source_name: str        # e.g. "தினத்தந்தி"
    source_url: str         # Primary article link
    original_title: str     # Raw Tamil title from feed
    original_summary: str   # Raw description or snippet
    image_url: str          # Verified real news photograph URL (non-empty)
    published_date: str     # ISO or formatted date string
    category_hint: str      # Raw category slug e.g. "tamilnadu"


try:
    from src.ai.tamil_synthesizer import ProcessedArticle
except (ImportError, ModuleNotFoundError):
    @dataclass
    class ProcessedArticle:
        """M2 (AI Synthesizer) -> M3 (Publisher) Interface Contract."""
        id: int                 # Unique integer ID (1, 2, 3...)
        category: str           # 'tamilnadu', 'national', 'world', 'politics', 'business', 'cinema', 'sports', 'tech', 'spiritual'
        sub_category: str       # 'chennai', 'madurai', 'coimbatore', 'trichy', 'south', 'cricket', 'news', 'reviews', etc.
        title: str              # Professional journalistic Tamil headline
        summary: str            # 1-2 sentence lead summary
        body: str               # Full multi-paragraph Tamil body
        image: str              # High-resolution real news image URL
        author: str             # e.g. 'அறச்சுடர் சிறப்பு நிருபர்'
        date: str               # e.g. '10 நவம்பர் 2026'
        time_ago: str           # e.g. '15 நிமிடங்கள் முன்'
        read_time: str          # e.g. '3 நிமிடம்'
        views: int              # Initial view count (e.g. 5000-15000)
        is_flash: bool          # True if breaking news ticker candidate
        tags: List[str]         # Tamil search tags
        source_url: str         # Original reference URL
        source_name: str        # Original news publication name

        def to_template_dict(self) -> Dict[str, Any]:
            """Converts to camelCase dictionary conforming to frontend NEWS_DATABASE schema."""
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
                "sourceName": self.source_name
            }


# ============================================================================
# Canonical Datasets
# ============================================================================

SAMPLE_RAW_ARTICLES: List[RawArticle] = [
    RawArticle(
        source_id="daily_thanthi",
        source_name="தினத்தந்தி",
        source_url="https://www.dailythanthi.com/news/state/investments-chennai-101",
        original_title="சென்னையில் தொழில் முதலீடுகள் அதிகரிப்பு: 50,000 பேருக்கு வேலைவாய்ப்பு",
        original_summary="சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் பல புதிய புரிந்துணர்வு ஒப்பந்தங்கள் கையெழுத்தாகின.",
        image_url="https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200",
        published_date="2026-11-10T08:30:00Z",
        category_hint="tamilnadu"
    ),
    RawArticle(
        source_id="dinamani",
        source_name="தினமணி",
        source_url="https://www.dinamani.com/business/rbi-rates-2026-67890",
        original_title="ரிசர்வ் வங்கியின் முக்கிய கொள்கை முடிவு: கடன்களுக்கான வட்டி குறைய வாய்ப்பு",
        original_summary="பணவீக்கம் தணிந்துள்ளதால் நடுத்தர வர்க்க மக்களின் வீட்டுக் கடன் மற்றும் வாகன கடன் வட்டி குறையக்கூடும்.",
        image_url="https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200",
        published_date="2026-11-10T09:15:00Z",
        category_hint="business"
    ),
    RawArticle(
        source_id="oneindia",
        source_name="ஒன்இந்தியா தமிழ்",
        source_url="https://tamil.oneindia.com/cricket/melbourne-test-kohli-54321",
        original_title="மெல்போர்ன் டெஸ்டில் விராட் கோலி அபார சதம்",
        original_summary="ஆஸ்திரேலியாவுக்கு எதிரான மூன்றாவது டெஸ்ட் போட்டியில் இந்திய அணி வலுவான முன்னிலை பெற்றுள்ளது.",
        image_url="https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg",
        published_date="2026-11-10T09:45:00Z",
        category_hint="sports"
    ),
    RawArticle(
        source_id="news18",
        source_name="நியூஸ்18 தமிழ்",
        source_url="https://tamil.news18.com/cinema/teaser-record-98765",
        original_title="பிரமாண்ட சரித்திர திரைப்படத்தின் டீசர் சாதனை",
        original_summary="யூடியூபில் வெளியான சில மணி நேரங்களிலேயே புதிய சாதனை படைத்து பார்வையாளர்களை கவர்ந்துள்ளது.",
        image_url="https://images.news18.com/tamil/uploads/2026/11/sonia-gandhi-2026-11-bfbe3a4e73a1c1c1200255934925ba2d-1200x800.jpg",
        published_date="2026-11-10T10:00:00Z",
        category_hint="cinema"
    ),
    RawArticle(
        source_id="dinamalar",
        source_name="தினமலர்",
        source_url="https://www.dinamalar.com/news_detail.asp?id=345678",
        original_title="சென்னை மெட்ரோ 2-ஆம் கட்ட பூந்தமல்லி - போரூர் சோதனை ஓட்டம்",
        original_summary="பூந்தமல்லி பணிமனையில் இருந்து போரூர் சந்திப்பு வரை அதிநவீன மெட்ரோ ரயில்களின் சோதனை ஓட்டம் தொடங்கியது.",
        image_url="https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg",
        published_date="2026-11-10T09:15:00Z",
        category_hint="tamilnadu"
    ),
]


SAMPLE_PROCESSED_ARTICLES: List[ProcessedArticle] = [
    ProcessedArticle(
        id=1,
        category="tamilnadu",
        sub_category="chennai",
        title="தமிழ்நாட்டில் ₹45,000 கோடி புதிய தொழில் முதலீடுகள்: 1 லட்சம் பேருக்கு வேலைவாய்ப்பு!",
        summary="சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் 25 சர்வதேச நிறுவனங்களுடன் புதிய புரிந்துணர்வு ஒப்பந்தங்கள் கையெழுத்தாகின.",
        body="சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் தமிழகத்தில் மின்னணுவியல், செமிகண்டக்டர் மற்றும் பசுமை ஹைட்ரஜன் துறைகளில் ₹45,000 கோடி முதலீட்டு ஒப்பந்தங்கள் கையெழுத்தாகியுள்ளன.\n\nஇந்த முதலீடுகள் மூலம் அடுத்த மூன்று ஆண்டுகளில் 1 லட்சம் இளைஞர்களுக்கு வேலைவாய்ப்புகள் உருவாகும் என அமைச்சர் பெருமிதத்துடன் தெரிவித்துள்ளார்.",
        image="https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200",
        author="அறச்சுடர் சிறப்பு நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="25 நிமிடங்கள் முன்",
        read_time="3 நிமிடம்",
        views=14200,
        is_flash=True,
        tags=["முதலீடுகள்", "தமிழகம்", "வேலைவாய்ப்பு"],
        source_url="https://www.dailythanthi.com/news/state/investments-chennai-101",
        source_name="தினத்தந்தி"
    ),
    ProcessedArticle(
        id=4,
        category="business",
        sub_category="market",
        title="ரிசர்வ் வங்கியின் முக்கிய கொள்கை முடிவு: கடன்களுக்கான வட்டி விகிதங்கள் குறைய வாய்ப்பு",
        summary="பணவீக்கம் தணிந்துள்ளதால் நடுத்தர வர்க்க மக்களின் வீட்டுக் கடன் மற்றும் வாகன கடன் வட்டிகள் குறைய வாய்ப்புள்ளது.",
        body="இந்திய ரிசர்வ் வங்கியின் நிதிக் கொள்கை குழு கூட்டத்தில் ரெப்போ வட்டி விகிதங்களை தளர்த்துவது குறித்து சாதகமான முடிவுகள் எடுக்கப்படலாம் என எதிர்பார்க்கப்படுகிறது.\n\nஇதனால் வர்த்தக வங்கிகள் வாடிக்கையாளர்களுக்கு வழங்கும் கடன்களுக்கான வட்டி விகிதங்கள் குறையக்கூடும்.",
        image="https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200",
        author="வணிக நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="45 நிமிடங்கள் முன்",
        read_time="2 நிமிடம்",
        views=8900,
        is_flash=False,
        tags=["வணிகம்", "ரிசர்வங்கி", "வட்டிவிகிதம்"],
        source_url="https://www.dinamani.com/business/rbi-rates-2026-67890",
        source_name="தினமணி"
    ),
    ProcessedArticle(
        id=7,
        category="sports",
        sub_category="cricket",
        title="மெல்போர்ன் டெஸ்டில் விராட் கோலி - கில் அபார கூட்டணி: இந்திய அணி வலுவான முன்னிலை",
        summary="ஆஸ்திரேலிய பந்துவீச்சை நாலாபுறமும் சிதறடித்த இந்திய வீரர்கள்; 220 ரன்கள் வலுவான முன்னிலை பெற்று ஆதிக்கம்.",
        body="பார்டர் - கவாஸ்கர் கோப்பை தொடரின் மெல்போர்ன் டெஸ்டில் விராட் கோலி அபார சதம் விளாசி அசத்தினார். அவருடன் ஜோடி சேர்ந்த சுப்மன் கில் பொறுப்புடன் ஆடி சதமடித்தார்.\n\nஇந்த ஜோடி நான்காவது விக்கெட்டுக்கு 200 ரன்களுக்கு மேல் குவித்து இந்திய அணியை இமாலய முன்னிலைக்கு கொண்டு சென்றது.",
        image="https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg",
        author="விளையாட்டு நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="1 மணி நேரம் முன்",
        read_time="3 நிமிடம்",
        views=12400,
        is_flash=True,
        tags=["கிரிக்கெட்", "இந்தியா", "டெஸ்ட்"],
        source_url="https://tamil.oneindia.com/cricket/melbourne-test-kohli-54321",
        source_name="ஒன்இந்தியா தமிழ்"
    ),
    ProcessedArticle(
        id=6,
        category="cinema",
        sub_category="news",
        title="பிரமாண்ட பட்ஜெட்டில் உருவாகும் சரித்திர திரைப்படம்: டீசர் வெளியாகி சாதனை",
        summary="வெளியான சில மணி நேரங்களிலேயே யூடியூப் டிரெண்டிங்கில் முதலிடம் பிடித்து பார்வையாளர்களை கவர்ந்துள்ளது.",
        body="முன்னணி இயக்குனர் இயக்கத்தில் உருவாகியுள்ள சரித்திர திரைப்படத்தின் முதல் டீசர் அதிகாரப்பூர்வமாக வெளியானது.\n\nஅதிநவீன விஷுவல் எஃபெக்ட்ஸ் காட்சிகள் மற்றும் விறுவிறுப்பான பின்னணி இசை ரசிகர்களிடையே பெரும் எதிர்பார்ப்பை ஏற்படுத்தியுள்ளது.",
        image="https://images.news18.com/tamil/uploads/2026/11/sonia-gandhi-2026-11-bfbe3a4e73a1c1c1200255934925ba2d-1200x800.jpg",
        author="சினிமா நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="2 மணி நேரம் முன்",
        read_time="2 நிமிடம்",
        views=15600,
        is_flash=False,
        tags=["சினிமா", "டீசர்", "டிரெண்டிங்"],
        source_url="https://tamil.news18.com/cinema/teaser-record-98765",
        source_name="நியூஸ்18 தமிழ்"
    ),
    ProcessedArticle(
        id=2,
        category="tamilnadu",
        sub_category="chennai",
        title="சென்னை மெட்ரோ 2-ஆம் கட்ட பூந்தமல்லி - போரூர் சோதனை ஓட்டம் தொடக்கம்",
        summary="மேற்கு சென்னை மக்களின் போக்குவரத்து நெரிசலை குறைக்கும் வகையில் மெட்ரோ பணிகள் துரிதப்படுத்தப்பட்டுள்ளன.",
        body="சென்னை பெருநகர மெட்ரோ ரயில் திட்டத்தின் இரண்டாம் கட்ட வழித்தடத்தில் அதிநவீன மெட்ரோ ரயில்களின் சோதனை ஓட்டம் வெற்றிகரமாக தொடங்கியது.\n\nவிரைவில் பாதுகாப்பு ஆணையரின் சான்றிதழ் பெறப்பட்டு மக்கள் பயன்பாட்டிற்கு கொண்டுவரப்படும் என அறிவிக்கப்பட்டுள்ளது.",
        image="https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg",
        author="சென்னை சிறப்பு நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="3 நிமிடங்களுக்கு முன்",
        read_time="2 நிமிடம்",
        views=9100,
        is_flash=True,
        tags=["மெட்ரோ", "சென்னை", "போரூர்"],
        source_url="https://www.dinamalar.com/news_detail.asp?id=345678",
        source_name="தினமலர்"
    ),
    ProcessedArticle(
        id=8,
        category="politics",
        sub_category="national",
        title="நாடாளுமன்ற குளிர்கால கூட்டத்தொடர்: முக்கிய மசோதாக்கள் தாக்கல்",
        summary="மக்களவையில் பல முக்கிய சீர்திருத்த மசோதாக்கள் விவாதத்திற்கு எடுத்துக்கொள்ளப்பட உள்ளன.",
        body="நாடாளுமன்ற குளிர்கால கூட்டத்தொடர் சுமுகமாக நடைபெற அனைத்துக் கட்சிகளின் ஒத்துழைப்பை சபாநாயகர் கோரியுள்ளார்.",
        image="https://cf-images.assettype.com/hindutamil-prod/2026-11-10/2d9ml1m9/appa-kutty.jpg?w=1200",
        author="அரசியல் நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="30 நிமிடங்கள் முன்",
        read_time="2 நிமிடம்",
        views=7400,
        is_flash=False,
        tags=["அரசியல்", "நாடாளுமன்றம்"],
        source_url="https://www.hindutamil.in/news/tamilnadu/green-power-2026.html",
        source_name="இந்து தமிழ் திசை"
    ),
    ProcessedArticle(
        id=5,
        category="tech",
        sub_category="ai",
        title="செயற்கை நுண்ணறிவு துறையில் இந்திய இளைஞர்களின் புதிய கண்டுபிடிப்பு",
        summary="குறைந்த செலவில் மருத்துவ பரிசோதனை செய்ய உதவும் அதிநவீன AI செயலி உருவாக்கம்.",
        body="இந்திய தொழில்நுட்பக் கழக மாணவர்கள் உருவாக்கிய புதிய செயற்கை நுண்ணறிவு மாதிரி சர்வதேச அங்கீகாரம் பெற்றுள்ளது.",
        image="https://gumlet.vikatan.com/vikatan/2026-11-10/1xu4rr9j/WhatsApp-Image-2026-11-07-at-10.09.28.jpeg?w=1200",
        author="தொழில்நுட்ப நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="1 மணி முன்",
        read_time="3 நிமிடம்",
        views=11200,
        is_flash=False,
        tags=["தொழில்நுட்பம்", "AI"],
        source_url="https://www.vikatan.com/agriculture/drone-technology-2026",
        source_name="ஆனந்த விகடன்"
    ),
    ProcessedArticle(
        id=10,
        category="world",
        sub_category="climate",
        title="காலநிலை மாற்ற மாநாட்டில் உலக தலைவர்கள் முக்கிய பிரகடனம்",
        summary="புவி வெப்பமயமாதலை கட்டுப்படுத்த நிதி உதவி வழங்க வளர்ந்த நாடுகள் ஒப்புதல்.",
        body="சர்வதேச காலநிலை உச்சி மாநாட்டில் கார்பன் வெளியேற்றத்தை குறைக்க புதிய காலக்கெடு நிர்ணயிக்கப்பட்டுள்ளது.",
        image="https://ichef.bbci.co.uk/ace/ws/1024/cpsprodpb/3a8b/live/da8fa680-dcfd-11f1-93e1-3b657b665bcf.jpg",
        author="உலக நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="4 மணி முன்",
        read_time="3 நிமிடம்",
        views=6300,
        is_flash=False,
        tags=["உலகம்", "காலநிலை"],
        source_url="https://www.bbc.com/tamil/articles/c12345678",
        source_name="பிபிசி தமிழ்"
    ),
    ProcessedArticle(
        id=3,
        category="spiritual",
        sub_category="temple",
        title="மதுரை மீனாட்சி சுந்தரேஸ்வரர் திருக்கோயில் திருவிழா கொடியேற்றம்",
        summary="பக்தர்கள் திரளாக பங்கேற்று சாமி தரிசனம்; விரிவான பாதுகாப்பு ஏற்பாடுகள்.",
        body="மதுரை மீனாட்சி அம்மன் திருக்கோயிலில் வருடாந்திர திருவிழா கொடியேற்றத்துடன் விமரிசையாக தொடங்கியது.",
        image="https://thinaboomi.com/uploads/images/202603/image_870x580_69c273307cfa5.jpg",
        author="ஆன்மிக நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="2 மணி முன்",
        read_time="2 நிமிடம்",
        views=9800,
        is_flash=False,
        tags=["ஆன்மிகம்", "மதுரை"],
        source_url="https://thinaboomi.com/rss/latest-posts/madurai-conclave-5544",
        source_name="தினபூமி"
    ),
    ProcessedArticle(
        id=9,
        category="national",
        sub_category="general",
        title="இந்திய விண்வெளி ஆராய்ச்சி நிறுவனம் புதிய செயற்கைக்கோள் ஏவ திட்டம்",
        summary="ஸ்ரீஹரிகோட்டாவில் இருந்து அடுத்த மாதம் பிஎஸ்எல்வி ராக்கெட் மூலம் ஏவப்படுகிறது.",
        body="வானிலை கண்காணிப்பு மற்றும் தொலைத்தொடர்பு பயன்பாட்டிற்காக புதிய அதிநவீன செயற்கைக்கோள் தயாராக உள்ளது.",
        image="https://static.asianetnews.com/images/w-1280,h-720,format-jpg,imgid-01m72wtzdx77fh2sck4n5wpkr4,imgname-walking-shoes-vs-running-shoes--2--1794319941053.jpg",
        author="தேசிய நிருபர்",
        date="10 நவம்பர் 2026",
        time_ago="3 மணி முன்",
        read_time="2 நிமிடம்",
        views=8100,
        is_flash=False,
        tags=["இந்தியா", "விண்வெளி"],
        source_url="https://tamil.asianetnews.com/rss",
        source_name="ஏசியாநெட் தமிழ்"
    ),
]

# Broadsheet 4-page schema for EPAPER_PAGES_CONTENT
SAMPLE_EPAPER_PAGES_CONTENT: Dict[int, Dict[str, str]] = {
    1: {
        "title": "முதன்மைப் பக்கம் (Front Page Headlines)",
        "leadHeadline": "தமிழ்நாட்டில் ₹45,000 கோடி புதிய தொழில் முதலீடுகள்",
        "leadSubhead": "1 லட்சம் இளைஞர்களுக்கு வேலைவாய்ப்புகள் உருவாகும் என அறிவிப்பு",
        "leadByline": "அறச்சுடர் சிறப்பு நிருபர், சென்னை • 10 நவம்பர் 2026",
        "leadPhoto": "https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200",
        "leadCaption": "சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் புரிந்துணர்வு ஒப்பந்தங்கள்.",
        "leadBody": "சென்னையில் நடைபெற்ற உலகளாவிய முதலீட்டாளர்கள் மாநாட்டில் தமிழகத்தில் மின்னணுவியல், செமிகண்டக்டர் துறைகளில் ₹45,000 கோடி முதலீட்டு ஒப்பந்தங்கள் கையெழுத்தாகியுள்ளன...",
        "sideHeadline": "ரிசர்வ் வங்கியின் முக்கிய நிதிக் கொள்கை முடிவு",
        "sideSummary": "கடன் வட்டி விகிதங்களை குறைக்க நிதிக் கொள்கை குழு சாதகமான ஆலோசனை மேற்கொண்டுள்ளது.",
        "metroHeadline": "சென்னை மெட்ரோ 2-ஆம் கட்ட பூந்தமல்லி - போரூர் சோதனை ஓட்டம்",
        "metroSummary": "அதிநவீன மெட்ரோ ரயில்களின் சோதனை ஓட்டம் வெற்றிகரமாக நிறைவடைந்தது.",
        "waterHeadline": "வங்கக்கடலில் காற்றழுத்த தாழ்வு நிலை: கடலோர மாவட்டங்களில் மழை",
        "waterSummary": "மீனவர்கள் கடலுக்கு செல்ல வேண்டாம் என வானிலை ஆய்வு மையம் எச்சரிக்கை விடுத்துள்ளது.",
        "editorialHeadline": "தொழில் வளர்ச்சியும் வேலைவாய்ப்பும்: தமிழகத்தின் அடுத்த பாய்ச்சல்",
        "editorialSnippet": "புதிய முதலீடுகள் தென் மாவட்டங்களுக்கும் பரவலாக்கப்பட வேண்டும் என்பதே மக்களின் எதிர்பார்ப்பு."
    },
    2: {
        "title": "தமிழகம் & அரசியல் (Tamil Nadu & Politics)",
        "leadHeadline": "சட்டமன்ற கூட்டத்தொடர் அடுத்த வாரம் துவக்கம்",
        "leadSubhead": "மக்களுக்கான முக்கிய நலத்திட்ட மசோதாக்கள் விவாதத்திற்கு வருகின்றன",
        "leadByline": "அரசியல் நிருபர் • 10 நவம்பர் 2026",
        "leadPhoto": "https://cf-images.assettype.com/hindutamil-prod/2026-11-10/2d9ml1m9/appa-kutty.jpg?w=1200",
        "leadCaption": "தலைமைச் செயலகத்தில் நடைபெற்ற அமைச்சரவை கூட்டம்.",
        "leadBody": "தமிழக சட்டமன்ற கூட்டத்தொடர் அடுத்த வாரம் கூட உள்ள நிலையில், எதிர்க்கட்சிகள் பல்வேறு முக்கிய மக்கள் பிரச்சனைகளை எழுப்ப திட்டமிட்டுள்ளன...",
        "sideHeadline": "உள்ளாட்சி அமைப்புகளுக்கு கூடுதல் நிதி ஒதுக்கீடு",
        "sideSummary": "கிராமப்புற சாலை மேம்பாட்டிற்கு சிறப்பு நிதி விடுவிக்கப்பட்டுள்ளது.",
        "metroHeadline": "சென்னையில் 100 புதிய மின்சார பேருந்துகள் இயக்கம்",
        "metroSummary": "மாசுபாட்டை குறைக்கும் வகையில் அரசு விரைவுப் போக்குவரத்துக் கழகம் நடவடிக்கை.",
        "waterHeadline": "மேட்டூர் அணை நீர்மட்டம் சீராக பராமரிப்பு",
        "waterSummary": "டெல்டா பாசனத்திற்கு தொடர்ந்து தேவையான அளவு தண்ணீர் திறந்துவிடப்படுகிறது.",
        "editorialHeadline": "மக்களாட்சி மாண்பும் சட்டமன்ற விவாதங்களும்",
        "editorialSnippet": "ஆக்கப்பூர்வமான விவாதங்கள் மூலம் பொதுமக்களின் பிரச்சனைகளுக்கு தீர்வு காணப்பட வேண்டும்."
    },
    3: {
        "title": "வணிகம் & தொழில்நுட்பம் (Business & Technology)",
        "leadHeadline": "இந்திய பங்குச்சந்தைகள் புதிய வரலாற்று உச்சம்",
        "leadSubhead": "சென்செக்ஸ் 85,000 புள்ளிகளை கடந்து வர்த்தகம் நிறைவு",
        "leadByline": "வணிக நிருபர், மும்பை • 10 நவம்பர் 2026",
        "leadPhoto": "https://media.assettype.com/dailythanthi/2026-01-30/cy7x77bo/Gold-Rate-03.jpg?w=1200&auto=format%2Ccompress&fit=max",
        "leadCaption": "மும்பை பங்குச்சந்தையில் உற்சாகமடைந்த முதலீட்டாளர்கள்.",
        "leadBody": "வெளிநாட்டு முதலீடுகள் தொடர்ந்து அதிகரித்து வருவதால் இந்திய பங்குச்சந்தைகள் புதிய வரலாற்று உச்சத்தை எட்டியுள்ளன...",
        "sideHeadline": "தங்கத்தின் விலை சற்று குறைவு: நகைப்பிரியர்கள் மகிழ்ச்சி",
        "sideSummary": "சர்வதேச சந்தையில் ஏற்பட்ட மாற்றத்தால் தங்கத்தின் விலை சவரனுக்கு ₹400 குறைந்துள்ளது.",
        "metroHeadline": "சென்னையில் புதிய தகவல் தொழில்நுட்ப பூங்கா திறப்பு",
        "metroSummary": "தரமணியில் அதிநவீன வசதிகளுடன் அமைக்கப்பட்ட புதிய ஐடி வளாகம்.",
        "waterHeadline": "குறைந்த மின்சாரத்தில் இயங்கும் நவீன விவசாய பம்புகள்",
        "waterSummary": "சூரிய ஒளியில் இயங்கும் பம்புசெட்டுகளுக்கு மத்திய அரசு மானியம் வழங்குகிறது.",
        "editorialHeadline": "டிஜிட்டல் இந்தியாவின் அடுத்த கட்டப் பயணம்",
        "editorialSnippet": "செயற்கை நுண்ணறிவு தொழில்நுட்பத்தை கிராமப்புற மக்களும் பயன்படுத்தும் சூழல் உருவாக வேண்டும்."
    },
    4: {
        "title": "விளையாட்டு & சினிமா (Sports & Cinema)",
        "leadHeadline": "மெல்போர்ன் டெஸ்டில் இந்திய அணி வரலாற்று வெற்றி",
        "leadSubhead": "ஆஸ்திரேலியாவை 150 ரன்கள் வித்தியாசத்தில் வீழ்த்தி அபாரம்",
        "leadByline": "விளையாட்டு நிருபர் • 10 நவம்பர் 2026",
        "leadPhoto": "https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg",
        "leadCaption": "வெற்றி கோப்பையுடன் இந்திய கிரிக்கெட் வீரர்கள் மகிழ்ச்சி.",
        "leadBody": "ஆஸ்திரேலியாவுக்கு எதிரான மெல்போர்ன் டெஸ்ட் போட்டியில் இந்திய அணி அபார பந்துவீச்சு மற்றும் பேட்டிங் மூலம் வரலாற்று வெற்றியை பதிவு செய்தது...",
        "sideHeadline": "சர்வதேச செஸ் போட்டியில் தமிழக வீரர் பிரக்ஞானந்தா சாம்பியன்",
        "sideSummary": "இறுதிச்சுற்றில் உலக சாம்பியனை வீழ்த்தி தமிழகத்திற்கு பெருமை சேர்த்துள்ளார்.",
        "metroHeadline": "நேரு உள்விளையாட்டு அரங்கில் மாநில அளவிலான தடகளப் போட்டி",
        "metroSummary": "ஆயிரத்திற்கும் மேற்பட்ட இளம் வீரர் வீராங்கனைகள் உற்சாகத்துடன் பங்கேற்பு.",
        "waterHeadline": "விளையாட்டு வீரர்களுக்கு நவீன சத்துணவு திட்டம் அறிமுகம்",
        "waterSummary": "கிராமப்புற விளையாட்டு திறமைகளை ஊக்குவிக்க சிறப்பு பயிற்சி மையங்கள்.",
        "editorialHeadline": "இந்திய விளையாட்டின் பொற்காலம் துவங்குகிறது",
        "editorialSnippet": "தொடர்ச்சியான சர்வதேச வெற்றிகள் இளைஞர்களிடையே விளையாட்டின் மீது பெரும் ஈர்ப்பை ஏற்படுத்தியுள்ளது."
    }
}
