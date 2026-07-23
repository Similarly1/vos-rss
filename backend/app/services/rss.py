import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from datetime import datetime
import time
import httpx
import re
from pathlib import Path

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

from app.database import get_db_connection
from app.config import settings
from app.services.feed_analyzer import analyze_feed_completeness, detect_language_from_text

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# Common feed URL migrations and aliases
KNOWN_FEED_ALIASES = {
    "https://www.rts.ch/rss/info.xml": "https://www.rts.ch/info/toute-info/?format=rss/news",
    "http://www.rts.ch/rss/info.xml": "https://www.rts.ch/info/toute-info/?format=rss/news",
    "https://www.rts.ch/info/rss": "https://www.rts.ch/info/toute-info/?format=rss/news",
    "https://www.rts.ch/info": "https://www.rts.ch/info/toute-info/?format=rss/news",
    "https://www.rts.ch/info/": "https://www.rts.ch/info/toute-info/?format=rss/news",
    "https://www.letemps.ch/rss": "https://www.letemps.ch/feed",
    "https://www.letemps.ch/rss/": "https://www.letemps.ch/feed"
}

def robust_parse_feed(url: str):
    """
    Robustly fetches and parses an RSS feed using httpx with browser User-Agent,
    known URL migrations, HTML RSS link autodiscovery, and fallback URL alias resolution.
    """
    if not HAS_FEEDPARSER:
        raise RuntimeError("Le paquet 'feedparser' n'est pas encore installé.")

    clean_url = url.strip()
    if clean_url in KNOWN_FEED_ALIASES:
        clean_url = KNOWN_FEED_ALIASES[clean_url]

    # 1. Primary fetch with httpx + browser headers
    try:
        r = httpx.get(clean_url, follow_redirects=True, headers=BROWSER_HEADERS, timeout=12.0)
        if r.status_code == 200:
            parsed = feedparser.parse(r.content)
            if parsed.entries:
                return parsed, clean_url

            # HTML Autodiscovery for RSS link tags inside HTML page
            if "text/html" in r.headers.get("content-type", "") or "<html" in r.text.lower()[:300]:
                rss_links = re.findall(r'href=["\']([^"\']+(?:format=rss|\.xml|/rss|/feed)[^"\']*)["\']', r.text, re.IGNORECASE)
                for found_link in set(rss_links):
                    if not found_link.startswith("http"):
                        found_link = "https://www.rts.ch" + found_link if found_link.startswith("/") else clean_url.rstrip("/") + "/" + found_link
                    try:
                        r_alt = httpx.get(found_link, follow_redirects=True, headers=BROWSER_HEADERS, timeout=10.0)
                        if r_alt.status_code == 200:
                            p_alt = feedparser.parse(r_alt.content)
                            if p_alt.entries:
                                return p_alt, found_link
                    except Exception:
                        pass
    except Exception as e:
        print(f"[rss.py fetch note for {clean_url}]: {e}")

    # 2. Fallback to feedparser built-in HTTP fetcher
    try:
        parsed = feedparser.parse(clean_url, agent=BROWSER_HEADERS["User-Agent"])
        if parsed.entries:
            return parsed, clean_url
    except Exception as e:
        print(f"[feedparser fallback note for {clean_url}]: {e}")

    # 3. Fallback to alternate RSS URL paths (/feed, /rss, ?format=rss/news)
    if not (clean_url.endswith('/feed') or clean_url.endswith('/rss') or clean_url.endswith('.xml') or 'format=rss' in clean_url):
        for alt in [
            clean_url.rstrip('/') + '/toute-info/?format=rss/news',
            clean_url.rstrip('/') + '/feed',
            clean_url.rstrip('/') + '/rss',
            clean_url.rstrip('/') + '/rss.xml'
        ]:
            try:
                r = httpx.get(alt, follow_redirects=True, headers=BROWSER_HEADERS, timeout=10.0)
                if r.status_code == 200:
                    parsed = feedparser.parse(r.content)
                    if parsed.entries:
                        return parsed, alt
            except Exception:
                pass

    # Final attempt
    parsed = feedparser.parse(clean_url)
    return parsed, clean_url

def extract_main_image_url(entry, content: str) -> str:
    if "media_content" in entry and len(entry.media_content) > 0:
        for media in entry.media_content:
            if media.get("url"):
                return media["url"]

    if "media_thumbnail" in entry and len(entry.media_thumbnail) > 0:
        for media in entry.media_thumbnail:
            if media.get("url"):
                return media["url"]

    if "enclosures" in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/") and enc.get("href"):
                return enc["href"]

    if content:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if match:
            img_src = match.group(1)
            if img_src.startswith("http"):
                return img_src

    return None

def extract_full_article_content(article_url: str, fallback_content: str) -> str:
    clean_fallback = re.sub(r'<[^>]+>', ' ', fallback_content or '').strip()
    if len(clean_fallback) >= 450:
        return fallback_content

    try:
        res = httpx.get(
            article_url, 
            follow_redirects=True, 
            timeout=8.0, 
            headers=BROWSER_HEADERS
        )
        if res.status_code == 200:
            html = res.text
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
            clean_paragraphs = []
            for p in paragraphs:
                txt = re.sub(r'<[^>]+>', '', p).strip()
                if len(txt) > 40 and not any(skip in txt.lower() for skip in ["cookie", "privacy", "subscribe", "newsletter", "s'abonner"]):
                    clean_paragraphs.append(txt)

            if len(clean_paragraphs) >= 2:
                scraped_text = "\n\n".join(clean_paragraphs)
                if len(scraped_text) > len(clean_fallback):
                    return scraped_text
    except Exception as e:
        print(f"[Scraper Fallback Note] Could not fetch full page for {article_url}: {e}")

    return fallback_content

def parse_and_save_feed(url: str, category: str = "Général", language: str = None, is_full_text: bool = None):
    feed_data, working_url = robust_parse_feed(url)

    if feed_data.bozo and not feed_data.entries:
        raise ValueError("Impossible de lire le flux RSS (Format invalide ou URL incorrecte).")

    feed_title = feed_data.feed.get("title", working_url)

    if language is None or is_full_text is None:
        try:
            analysis = analyze_feed_completeness(working_url)
            if language is None:
                language = analysis["language"]
            if is_full_text is None:
                is_full_text = analysis["is_full_text"]
        except Exception:
            if language is None:
                language = "fr"
            if is_full_text is None:
                is_full_text = True

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO feeds (url, title, category, language, is_full_text) VALUES (?, ?, ?, ?, ?)",
            (working_url, feed_title, category, language, 1 if is_full_text else 0)
        )
        feed_id = cursor.lastrowid
    except Exception:
        cursor.execute("SELECT id FROM feeds WHERE url = ?", (working_url,))
        row = cursor.fetchone()
        if row:
            feed_id = row["id"]
            cursor.execute(
                "UPDATE feeds SET category = ?, language = ?, is_full_text = ? WHERE id = ?",
                (category, language, 1 if is_full_text else 0, feed_id)
            )
        else:
            conn.close()
            raise ValueError("Erreur lors de l'enregistrement du flux.")

    articles_added = 0
    for entry in feed_data.entries[:20]:
        article_title = entry.get("title", "Sans titre")
        article_url = entry.get("link", "")
        if not article_url:
            continue

        raw_content = entry.get("summary") or entry.get("description") or ""
        if "content" in entry and len(entry.content) > 0:
            raw_content = entry.content[0].get("value", raw_content)

        full_content = extract_full_article_content(article_url, raw_content)
        image_url = extract_main_image_url(entry, full_content)

        pub_date_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub_date_struct:
            pub_date = datetime.fromtimestamp(time.mktime(pub_date_struct)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            pub_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        art_lang = language or detect_language_from_text(article_title + " " + (full_content[:200] if full_content else ""))

        try:
            cursor.execute(
                """
                INSERT INTO articles (feed_id, title, content, url, published_date, image_url, language, is_full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feed_id, article_title, full_content, article_url, pub_date, image_url, art_lang, 1)
            )
            articles_added += 1
        except Exception:
            pass

    conn.commit()
    conn.close()

    return {
        "feed_id": feed_id,
        "title": feed_title,
        "url": working_url,
        "category": category,
        "language": language,
        "is_full_text": is_full_text,
        "articles_added": articles_added
    }

def get_all_feeds():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, title, category, language, is_full_text, created_at FROM feeds ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_feed(feed_id: int, title: str, category: str, language: str = "fr", is_full_text: bool = True):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE feeds SET title = ?, category = ?, language = ?, is_full_text = ? WHERE id = ?",
        (title, category, language, 1 if is_full_text else 0, feed_id)
    )
    cursor.execute(
        "UPDATE articles SET language = ? WHERE feed_id = ?",
        (language, feed_id)
    )
    conn.commit()
    conn.close()
    return {"id": feed_id, "title": title, "category": category, "language": language, "is_full_text": is_full_text}

def delete_feed(feed_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM article_embeddings 
        WHERE article_id IN (SELECT id FROM articles WHERE feed_id = ?)
    """, (feed_id,))

    cursor.execute("DELETE FROM articles WHERE feed_id = ?", (feed_id,))
    cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))

    conn.commit()
    conn.close()
    return {"status": "success", "feed_id": feed_id}

def generate_opml_export() -> str:
    feeds = get_all_feeds()
    categories = {}
    for f in feeds:
        cat = f.get("category") or "Général"
        categories.setdefault(cat, []).append(f)

    outlines_xml = []
    for cat_name, cat_feeds in categories.items():
        cat_title_esc = xml_escape(cat_name)
        feed_outlines = []
        for f in cat_feeds:
            f_title = xml_escape(f.get("title") or f["url"])
            f_url = xml_escape(f["url"])
            f_lang = f.get("language") or "fr"
            feed_outlines.append(
                f'      <outline type="rss" text="{f_title}" title="{f_title}" xmlUrl="{f_url}" htmlUrl="{f_url}" language="{f_lang}" />'
            )
        feeds_str = "\n".join(feed_outlines)
        outlines_xml.append(f'    <outline text="{cat_title_esc}" title="{cat_title_esc}">\n{feeds_str}\n    </outline>')

    body_content = "\n".join(outlines_xml)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Vos - Export des Abonnements RSS</title>
    <dateCreated>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")}</dateCreated>
  </head>
  <body>
{body_content}
  </body>
</opml>"""

def import_feeds_from_content(raw_content: str) -> dict:
    imported = []
    skipped = 0
    failed = 0

    try:
        json_data = json.loads(raw_content)
        if isinstance(json_data, list):
            for item in json_data:
                u = item.get("url") or item.get("xmlUrl")
                c = item.get("category") or item.get("folder") or "Général"
                l = item.get("language") or "fr"
                if u:
                    try:
                        res = parse_and_save_feed(u, c, l)
                        imported.append(res)
                    except Exception:
                        skipped += 1
            return {"status": "success", "imported_count": len(imported), "skipped_count": skipped, "failed_count": failed}
    except Exception:
        pass

    try:
        root = ET.fromstring(raw_content)
        for parent_outline in root.findall(".//outline"):
            cat_name = parent_outline.attrib.get("title") or parent_outline.attrib.get("text") or "Général"
            
            xml_url = parent_outline.attrib.get("xmlUrl") or parent_outline.attrib.get("url")
            if xml_url:
                try:
                    res = parse_and_save_feed(xml_url, "Général")
                    imported.append(res)
                except Exception:
                    skipped += 1
                continue

            for child in parent_outline.findall("outline"):
                child_url = child.attrib.get("xmlUrl") or child.attrib.get("url")
                if child_url:
                    try:
                        res = parse_and_save_feed(child_url, cat_name)
                        imported.append(res)
                    except Exception:
                        skipped += 1

    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier OPML / JSON (Format XML invalide) : {e}")

    return {
        "status": "success",
        "imported_count": len(imported),
        "skipped_count": skipped,
        "failed_count": failed,
        "imported_feeds": imported
    }

async def refresh_all_feeds_and_vectorize(api_key: str = None):
    feeds = get_all_feeds()
    results = []
    for f in feeds:
        try:
            res = parse_and_save_feed(f["url"], f["category"], f.get("language"), bool(f.get("is_full_text")))
            results.append(res)
        except Exception as e:
            print(f"Erreur rafraîchissement flux {f['url']}: {e}")

    key = api_key or settings.mistral_api_key
    vectorized_count = 0
    if key:
        try:
            from app.services.embeddings import vectorize_all_pending
            from app.services.clustering import precompute_and_cache_clusters

            vec_res = await vectorize_all_pending(key, force_revectorize=False)
            vectorized_count = vec_res.get("processed_count", 0)

            await precompute_and_cache_clusters(key)
        except Exception as e:
            print(f"Erreur auto-vectorisation & pre-clustering: {e}")

    return {
        "feeds_processed": len(results),
        "vectorized_count": vectorized_count,
        "details": results
    }
