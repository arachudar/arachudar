"""
tests/fixtures/sample_feeds.py - Master RSS, Atom, and Sitemap XML Fixtures.
Provides realistic, parseable XML feeds for all 15 supported Tamil news publications,
plus malformed and boundary feed samples for fault injection testing.
"""

from typing import Dict

# 1. Daily Thanthi (RSS 2.0 with Yahoo Media RSS <media:content>)
DAILY_THANTHI_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Daily Thanthi - தினத்தந்தி</title>
    <link>https://www.dailythanthi.com</link>
    <description>தமிழ்நாட்டின் முன்னணி நாளிதழ்</description>
    <language>ta</language>
    <item>
      <title>சென்னையில் தொழில் முதலீடுகள் அதிகரிப்பு: 50,000 பேருக்கு வேலைவாய்ப்பு</title>
      <link>https://www.dailythanthi.com/news/state/investments-chennai-101</link>
      <guid isPermaLink="true">https://www.dailythanthi.com/news/state/investments-chennai-101</guid>
      <description>சென்னையில் நடைபெற்ற முதலீட்டாளர்கள் மாநாட்டில் பல புதிய ஒப்பந்தங்கள் கையெழுத்தாகின.</description>
      <category>தமிழ்நாடு</category>
      <pubDate>Tue, 10 Nov 2026 08:30:00 GMT</pubDate>
      <media:content url="https://media.assettype.com/dailythanthi/2026-11-10/bb18cb3b/dollar.jpg?w=1200" type="image/jpeg" medium="image" />
    </item>
    <item>
      <title>மெட்ரோ ரயில் 2-ஆம் கட்ட பணிகள் துரிதம்</title>
      <link>https://www.dailythanthi.com/news/state/metro-phase2-102</link>
      <guid isPermaLink="true">https://www.dailythanthi.com/news/state/metro-phase2-102</guid>
      <description>பூந்தமல்லி முதல் போரூர் வரையிலான வழித்தடத்தில் சோதனை ஓட்டம் நிறைவு.</description>
      <category>சென்னை</category>
      <pubDate>Tue, 10 Nov 2026 09:00:00 GMT</pubDate>
      <media:content url="https://media.assettype.com/dailythanthi/2026-11-10/metro_line.jpg?w=1200" type="image/jpeg" medium="image" />
    </item>
  </channel>
</rss>"""

# 2. Dinamalar (Google News Sitemap XML with <image:image><image:loc>)
DINAMALAR_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://www.dinamalar.com/news_detail.asp?id=345678</loc>
    <news:news>
      <news:publication>
        <news:name>தினமலர்</news:name>
        <news:language>ta</news:language>
      </news:publication>
      <news:publication_date>2026-11-10T09:15:00+05:30</news:publication_date>
      <news:title>சென்னை மெட்ரோ 2-ஆம் கட்ட பூந்தமல்லி - போரூர் சோதனை ஓட்டம்</news:title>
    </news:news>
    <image:image>
      <image:loc>https://images.dinamalar.com/data/large_2025/Tamil_News_lrg_4372635.jpg</image:loc>
      <image:title>சென்னை மெட்ரோ சோதனை ஓட்டம்</image:title>
    </image:image>
  </url>
</urlset>"""

# 3. Dinamani (RSS 2.0 with <media:content>)
DINAMANI_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>தினமணி - Dinamani</title>
    <link>https://www.dinamani.com</link>
    <item>
      <title>ரிசர்வ் வங்கியின் முக்கிய கொள்கை முடிவு: கடன்களுக்கான வட்டி குறைய வாய்ப்பு</title>
      <link>https://www.dinamani.com/business/rbi-rates-2026-67890</link>
      <description>பணவீக்கம் தணிந்துள்ளதால் நடுத்தர வர்க்க மக்களின் வீட்டுக் கடன் வட்டி குறையலாம்.</description>
      <category>வணிகம்</category>
      <pubDate>Tue, 10 Nov 2026 09:15:00 GMT</pubDate>
      <media:content url="https://cf-images.assettype.com/dinamani/2026-11-10/6ns58v9g/arayavir.jpg?w=1200" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# 4. Hindu Tamil Thisai (RSS 2.0)
HINDU_TAMIL_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>இந்து தமிழ் திசை - Hindu Tamil Thisai</title>
    <link>https://www.hindutamil.in</link>
    <item>
      <title>தமிழ்நாட்டில் புதிய பசுமை மின் திட்டங்கள்: முதலமைச்சர் துவக்கி வைத்தார்</title>
      <link>https://www.hindutamil.in/news/tamilnadu/green-power-2026.html</link>
      <description>சூரிய மின்சக்தி உற்பத்தியை பெருக்க அரசு புதிய இலக்கு நிர்ணயம்.</description>
      <category>தமிழகம்</category>
      <pubDate>Tue, 10 Nov 2026 09:30:00 GMT</pubDate>
      <media:content url="https://cf-images.assettype.com/hindutamil-prod/2026-11-10/2d9ml1m9/appa-kutty.jpg?w=1200" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# 5. Vikatan (RSS 2.0 with Gumlet CDN)
VIKATAN_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>ஆனந்த விகடன் - Vikatan</title>
    <link>https://www.vikatan.com</link>
    <item>
      <title>விவசாயிகளுக்கு நவீன தொழில்நுட்ப பயிற்சி: ஆளில்லா ட்ரோன் பயன்பாடு</title>
      <link>https://www.vikatan.com/agriculture/drone-technology-2026</link>
      <description>இயற்கை விவசாயத்தில் புதிய தொழில்நுட்ப முறைகள் அறிமுகம் செய்யப்பட்டுள்ளன.</description>
      <category>விவசாயம்</category>
      <pubDate>Tue, 10 Nov 2026 09:40:00 GMT</pubDate>
      <media:content url="https://gumlet.vikatan.com/vikatan/2026-11-10/1xu4rr9j/WhatsApp-Image-2026-11-07-at-10.09.28.jpeg?w=1200" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# 6. Thinaboomi (RSS 2.0 with standard <enclosure>)
THINABOOMI_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>தினபூமி - Thinaboomi</title>
    <link>https://thinaboomi.com</link>
    <item>
      <title>மதுரையில் சர்வதேச மாநாடு: தொழில் வளர்ச்சிக்கான புதிய முன்னெடுப்புகள்</title>
      <link>https://thinaboomi.com/rss/latest-posts/madurai-conclave-5544</link>
      <description>தென் மாவட்டங்களில் தொழில் வளர்ச்சியை ஊக்குவிக்க சிறப்பு நிதி ஒதுக்கீடு.</description>
      <category>மதுரை</category>
      <pubDate>Tue, 10 Nov 2026 08:45:00 GMT</pubDate>
      <enclosure url="https://thinaboomi.com/uploads/images/202603/image_870x580_69c273307cfa5.jpg" length="145620" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# 7. BBC News Tamil (RSS 2.0 with <media:thumbnail>)
BBC_TAMIL_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>பிபிசி தமிழ் - BBC News Tamil</title>
    <link>https://feeds.bbci.co.uk/tamil</link>
    <item>
      <title>காலநிலை மாற்றமும் கடல் மட்ட உயர்வும்: உலக நாடுகளுக்கு புதிய எச்சரிக்கை</title>
      <link>https://www.bbc.com/tamil/articles/c12345678</link>
      <description>புவி வெப்பமயமாதலைக் கட்டுப்படுத்த தீவிர நடவடிக்கை தேவை என ஐ.நா அறிக்கை.</description>
      <category>உலகம்</category>
      <pubDate>Tue, 10 Nov 2026 07:30:00 GMT</pubDate>
      <media:thumbnail url="https://ichef.bbci.co.uk/ace/ws/240/cpsprodpb/3a8b/live/da8fa680-dcfd-11f1-93e1-3b657b665bcf.jpg" width="240" height="135" />
    </item>
  </channel>
</rss>"""

# 8. Zee News Tamil Fallback (YouTube Atom Feed)
ZEE_TAMIL_YOUTUBE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/">
  <title>Zee Tamil News Breaking Feed</title>
  <entry>
    <id>yt:video:b_H_L23uG-M</id>
    <yt:videoId>b_H_L23uG-M</yt:videoId>
    <title>தமிழகத்தில் கனமழை எச்சரிக்கை: பள்ளி, கல்லூரிகளுக்கு விடுமுறை அறிவிப்பு</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=b_H_L23uG-M"/>
    <published>2026-11-10T09:20:00+00:00</published>
    <media:group>
      <media:title>தமிழகத்தில் கனமழை எச்சரிக்கை</media:title>
      <media:thumbnail url="https://i.ytimg.com/vi/b_H_L23uG-M/hqdefault.jpg" width="480" height="360"/>
      <media:description>வங்கக்கடலில் உருவான காற்றழுத்த தாழ்வு மண்டலம் காரணமாக கனமழை பெய்ய வாய்ப்பு.</media:description>
    </media:group>
  </entry>
</feed>"""

# 9. Oneindia Tamil (RSS 2.0 with <media:content>)
ONEINDIA_TAMIL_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>ஒன்இந்தியா தமிழ் - Oneindia Tamil</title>
    <link>https://tamil.oneindia.com</link>
    <item>
      <title>மெல்போர்ன் டெஸ்டில் விராட் கோலி அபார சதம்: இந்திய அணி வலுவான முன்னிலை</title>
      <link>https://tamil.oneindia.com/cricket/melbourne-test-kohli-54321</link>
      <description>ஆஸ்திரேலியாவுக்கு எதிரான போட்டியில் இந்திய அணி அபார ஆட்டம்.</description>
      <category>விளையாட்டு</category>
      <pubDate>Tue, 10 Nov 2026 09:45:00 GMT</pubDate>
      <media:content url="https://imagesvs.oneindia.com/webp/ta/img/2026/11/sheikhhasina-30211794324120.jpg" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# 10. News18 Tamil (RSS 2.0 with <media:content>)
NEWS18_TAMIL_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>நியூஸ்18 தமிழ்நாடு - News18 Tamil</title>
    <link>https://tamil.news18.com</link>
    <item>
      <title>பிரமாண்ட சரித்திர திரைப்படத்தின் டீசர் சாதனை: ரசிகர்கள் உற்சாகம்</title>
      <link>https://tamil.news18.com/cinema/teaser-record-98765</link>
      <description>யூடியூபில் வெளியான சில மணி நேரங்களிலேயே புதிய பார்வையாளர் சாதனை.</description>
      <category>சினிமா</category>
      <pubDate>Tue, 10 Nov 2026 10:00:00 GMT</pubDate>
      <media:content url="https://images.news18.com/tamil/uploads/2026/11/sonia-gandhi-2026-11-bfbe3a4e73a1c1c1200255934925ba2d-1200x800.jpg" type="image/jpeg" />
    </item>
  </channel>
</rss>"""

# Map of all sample feeds by source key
SAMPLE_FEEDS: Dict[str, str] = {
    "daily_thanthi": DAILY_THANTHI_RSS,
    "dinamalar": DINAMALAR_SITEMAP,
    "dinamani": DINAMANI_RSS,
    "hindu_tamil": HINDU_TAMIL_RSS,
    "vikatan": VIKATAN_RSS,
    "thinaboomi": THINABOOMI_RSS,
    "bbc_tamil": BBC_TAMIL_RSS,
    "zee_tamil": ZEE_TAMIL_YOUTUBE_ATOM,
    "oneindia": ONEINDIA_TAMIL_RSS,
    "news18": NEWS18_TAMIL_RSS,
}

# Malformed feed samples for fault injection & boundary testing
MALFORMED_EMPTY_FEED = ""
MALFORMED_UNCLOSED_XML = "<rss version='2.0'><channel><title>Incomplete Stream"
MALFORMED_NO_ITEMS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <link>https://example.com</link>
    <description>No items available</description>
  </channel>
</rss>"""
MALFORMED_HTML_FEED = """<!DOCTYPE html>
<html>
<head><title>502 Bad Gateway</title></head>
<body><center><h1>502 Bad Gateway</h1></center></body>
</html>"""
