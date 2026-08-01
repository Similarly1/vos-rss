import asyncio
import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from datetime import datetime, timedelta
import time
import httpx
import re
from pathlib import Path

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

from app.database import get_db_connection
from app.config import settings
from app.services.feed_analyzer import analyze_feed_completeness, detect_language_from_text

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

from app.services.paywall import get_media_cookie, detect_paywall
from urllib.parse import urlparse


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

def extract_meta_image_from_html(html_text: str, base_url: str = None) -> str:
    if not html_text:
        return None
    # 1. og:image or twitter:image
    match = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', html_text, re.IGNORECASE)
    
    if match:
        img_url = match.group(1).strip()
        if img_url:
            if img_url.startswith("//"):
                return "https:" + img_url
            if img_url.startswith("http"):
                return img_url
            if base_url and img_url.startswith("/"):
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{img_url}"
            return img_url

    # 2. link rel="image_src"
    match_link = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if match_link:
        img_url = match_link.group(1).strip()
        if img_url:
            if img_url.startswith("//"):
                return "https:" + img_url
            if img_url.startswith("http"):
                return img_url
            if base_url and img_url.startswith("/"):
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{img_url}"
            return img_url

    # 3. img tag in article/body
    match_img = re.search(r'<article[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE | re.DOTALL)
    if not match_img:
        match_img = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if match_img:
        img_url = match_img.group(1).strip()
        if img_url and not any(skip in img_url.lower() for skip in ['logo', 'icon', 'pixel', 'avatar', 'banner', 'ad-']):
            if img_url.startswith("//"):
                return "https:" + img_url
            if img_url.startswith("http"):
                return img_url
            if base_url and img_url.startswith("/"):
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{img_url}"
            return img_url

    return None

def extract_main_image_url(entry, content: str = "", html_page: str = None, article_url: str = None) -> str:
    if entry:
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

    if html_page:
        meta_img = extract_meta_image_from_html(html_page, article_url)
        if meta_img:
            return meta_img

    return None

def clean_html_boilerplate(html_str: str) -> str:
    if not html_str:
        return ""
    # Strip script, style, header, nav, footer, form, svg tags and their content
    text = re.sub(r'<(script|style|header|nav|footer|form|svg)[^>]*>.*?</\1>', ' ', html_str, flags=re.DOTALL | re.IGNORECASE)
    # Strip header navigation noise strings like 'BBC HomepageSkip to content...'
    text = re.sub(r'(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu).*?(?:News|Sport|Weather|Sounds)', ' ', text, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse whitespace
    return re.sub(r'\s+', ' ', text).strip()

def extract_full_article_content(article_url: str, fallback_content: str) -> tuple[str, bool, bool]:
    clean_fallback = clean_html_boilerplate(fallback_content)
    
    is_paywalled = False
    is_full_text_available = True

    # CSS selectors for known media (requires BeautifulSoup)
    SITE_SELECTORS = {
        'lemonde.fr':               ['article.article__content p', 'div.article__body p', '.article__paragraph', 'section[data-component="ArticleBody"] p'],
        'mediapart.fr':             ['div.content-article p', '.article-content p', 'div.text-article p'],
        'lefigaro.fr':              ['div.fig-content-body p', '.article__text p'],
        'lesechos.fr':              ['div.content-article p', '.article-body p'],
        'wsj.com':                  ['div.article-content p', 'section.article__content p'],
        'nytimes.com':              ['section[name="articleBody"] p', 'div.StoryBodyCompanionColumn p'],
        'francetvinfo.fr':          ['section.body p', 'article p', '.c-body p', 'div.text p', '.content p'],
        'rts.ch':                   ['.article-body p', 'article p', '.content p'],
        'ouest-france.fr':          ['article p', '.article-body p', '.content-body p', 'main p', '.text p'],
        'rfi.fr':                   ['.t-content__body p', 'article p', '.c-article-content p', '.m-article-text p'],
        'ladepeche.fr':             ['.article-full__body p', 'article p', '.article__content p'],
        'letelegramme.fr':          ['.article-body p', 'article p', '.content p'],
        'courrierinternational.com':['.article-text p', 'article p', '.content p'],
        'slate.fr':                 ['.article-body p', 'article p', '.content p'],
        'theconversation.com':      ['.grid-ten p', 'article p', '.content-body p'],
        'liberation.fr':            ['.article-body p', 'article p', '.story-body p'],
        'leparisien.fr':            ['.article-section p', 'article p', '.content p'],
        '20minutes.fr':             ['.content p', 'article p', '.text p'],
        'bfmtv.com':                ['.article-body p', 'article p', '.content p'],
        'huffingtonpost.fr':        ['.entry-body p', 'article p', '.content p'],
    }

    try:
        domain = urlparse(article_url).netloc
        domain = domain.replace("www.", "")
        
        cookie_str = get_media_cookie(domain)
        headers = BROWSER_HEADERS.copy()
        if cookie_str:
            headers["Cookie"] = cookie_str
        # Richer referer to avoid bot detection
        headers["Referer"] = f"https://{domain}/"
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        headers["Accept-Language"] = "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"

        html_text = ""
        if curl_requests:
            try:
                r_curl = curl_requests.get(article_url, impersonate="chrome", timeout=10.0, headers=headers)
                if r_curl.status_code == 200:
                    html_text = r_curl.text
            except Exception:
                pass

        if not html_text:
            res = httpx.get(
                article_url, 
                follow_redirects=True, 
                timeout=12.0, 
                headers=headers
            )
            if res.status_code == 200:
                html_text = res.text

        if html_text:
            html_text = html_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            scraped_text = ""

            # Try domain-specific CSS selectors first (requires BeautifulSoup)
            if BeautifulSoup:
                soup = BeautifulSoup(html_text, 'html.parser')
                # Remove unwanted elements (scripts, styles, nav, header, footer, ads)
                for s in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe', 'noscript']):
                    s.decompose()

                selectors = []
                for site_key, site_selectors in SITE_SELECTORS.items():
                    if site_key in domain:
                        selectors = site_selectors
                        break

                if selectors:
                    for sel in selectors:
                        parts = [el.get_text(separator=' ', strip=True)
                                 for el in soup.select(sel)
                                 if len(el.get_text(strip=True)) > 25]
                        if parts:
                            scraped_text = "\n\n".join(parts)
                            break

                # Universal Container Search if domain selector didn't return text
                if not scraped_text:
                    candidate = (
                        soup.find('article') or 
                        soup.find('main') or 
                        soup.select_one('div[class*="article-body"], div[class*="article-content"], div[class*="entry-content"], div[class*="story-body"], div[class*="content-body"], div[class*="post-content"], section[class*="article"]')
                    )
                    
                    if not candidate:
                        containers = soup.select('div[class*="content"], div[class*="body"], div[class*="story"], div[class*="text"], section')
                        best_score = 0
                        for c in containers:
                            txt_len = len(c.get_text(strip=True))
                            if txt_len > best_score:
                                best_score = txt_len
                                candidate = c

                    target = candidate or soup.body or soup
                    
                    raw_paragraphs = [el.get_text(separator=' ', strip=True) for el in target.find_all(['p', 'h2', 'h3', 'li'])]
                    clean_parts = []
                    for txt in raw_paragraphs:
                        txt_clean = re.sub(r'\s+', ' ', txt).strip()
                        if len(txt_clean) > 25 and not any(skip in txt_clean.lower() for skip in ["cookie", "privacy", "subscribe", "newsletter", "s'abonner", "droits réservés", "tous droits", "mentions légales"]):
                            clean_parts.append(txt_clean)

                    if clean_parts and sum(len(p) for p in clean_parts) >= 90:
                        scraped_text = "\n\n".join(clean_parts)
                    else:
                        direct_text = target.get_text(separator='\n', strip=True)
                        lines = [line.strip() for line in direct_text.split('\n') if len(line.strip()) > 30 and not any(skip in line.lower() for skip in ["cookie", "privacy", "subscribe", "newsletter", "s'abonner"])]
                        if lines and sum(len(l) for l in lines) >= 90:
                            scraped_text = "\n\n".join(lines)

            # Generic fallback: regex paragraph extraction if BeautifulSoup is not available or returned nothing
            if not scraped_text:
                paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html_text, re.DOTALL | re.IGNORECASE)
                clean_paragraphs = []
                for p in paragraphs:
                    txt = re.sub(r'<[^>]+>', '', p).strip()
                    import html
                    txt = html.unescape(txt)
                    if len(txt) > 30 and not any(skip in txt.lower() for skip in ["cookie", "privacy", "subscribe", "newsletter", "s'abonner"]):
                        clean_paragraphs.append(txt)
                if clean_paragraphs and sum(len(p) for p in clean_paragraphs) >= 100:
                    scraped_text = "\n\n".join(clean_paragraphs)
                
            is_paywalled = detect_paywall(html_text, scraped_text)
            
            final_text = scraped_text if len(scraped_text) > len(clean_fallback) else fallback_content
            if is_paywalled:
                is_full_text_available = False
            return final_text, is_paywalled, is_full_text_available, html_text
    except Exception as e:
        print(f"[Scraper Fallback Note] Could not fetch full page for {article_url}: {e}")

    # If we didn't scrape anything better, use fallback content
    return fallback_content, is_paywalled, is_full_text_available, ""

def rescrape_short_articles_in_db(limit: int = 60):
    """
    Background worker function that rescrapes existing articles in the database that have short excerpts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, title, url, content FROM articles WHERE LENGTH(content) < 400 AND url LIKE 'http%' LIMIT ?", (limit,))
        rows = cursor.fetchall()
        articles_to_process = [{"id": r["id"], "url": r["url"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"[Auto-Rescraper note] {e}")
        return
    finally:
        conn.close()

    if not articles_to_process:
        return

    updated_count = 0
    for r in articles_to_process:
        try:
            res_ex = extract_full_article_content(r["url"], r["content"] or "")
            full_text, is_pw, is_ft = res_ex[0], res_ex[1], res_ex[2]
            if full_text and len(full_text) > len(r["content"] or ""):
                conn_update = get_db_connection()
                try:
                    conn_update.execute(
                        "UPDATE articles SET content = ?, is_paywalled = ?, is_full_text_available = ? WHERE id = ?",
                        (full_text, 1 if is_pw else 0, 1 if is_ft else 0, r["id"])
                    )
                    conn_update.commit()
                    updated_count += 1
                finally:
                    conn_update.close()
        except Exception:
            pass

    if updated_count > 0:
        print(f"[Auto-Rescraper] {updated_count} articles ré-enrichis en texte intégral.")

def enrich_missing_article_images(limit: int = 60):
    """
    Background worker function that fetches OpenGraph/meta images for database articles missing image_url.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, url, content FROM articles WHERE (image_url IS NULL OR image_url = '') AND url LIKE 'http%' LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        # Convert sqlite3.Row to dict so we can safely close the connection
        articles_to_process = [{"id": r["id"], "url": r["url"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"[Auto-Image-Enricher note] {e}")
        return
    finally:
        conn.close()

    if not articles_to_process:
        return

    updated_count = 0
    for r in articles_to_process:
        try:
            res_ex = extract_full_article_content(r["url"], r["content"] or "")
            html_text = res_ex[3] if len(res_ex) > 3 else ""
            img = extract_meta_image_from_html(html_text, r["url"])
            if img:
                conn_update = get_db_connection()
                try:
                    conn_update.execute("UPDATE articles SET image_url = ? WHERE id = ?", (img, r["id"]))
                    conn_update.commit()
                    updated_count += 1
                finally:
                    conn_update.close()
        except Exception:
            pass

    if updated_count > 0:
        print(f"[Auto-Image-Enricher] {updated_count} articles enrichis avec une image de couverture.")

def clean_old_articles(retention_days: int = 14) -> dict:
    """
    Deletes articles older than retention_days along with their vector embeddings and clears cluster cache.
    If retention_days <= 0, cleaning is disabled.
    """
    if retention_days is None or retention_days <= 0:
        return {"deleted_articles": 0, "status": "disabled"}

    cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete embeddings of articles older than cutoff_date
        cursor.execute("""
            DELETE FROM article_embeddings 
            WHERE article_id IN (SELECT id FROM articles WHERE published_date < ?)
        """, (cutoff_date,))

        # Delete articles older than cutoff_date
        cursor.execute("DELETE FROM articles WHERE published_date < ?", (cutoff_date,))
        deleted_count = cursor.rowcount

        if deleted_count > 0:
            cursor.execute("DELETE FROM cluster_cache")

        conn.commit()
        conn.close()
        return {
            "deleted_articles": deleted_count,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date
        }
    except Exception as e:
        conn.close()
        print(f"[clean_old_articles error]: {e}")
        return {"deleted_articles": 0, "error": str(e)}

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

    # 1. Mise à jour de la table feeds rapidement (sans bloquer la BDD)
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
    conn.commit()
    conn.close()

    # 2. Scraping HTTP et insertion article par article sans bloquer la base globalement
    articles_added = 0
    for entry in feed_data.entries[:20]:
        article_title = entry.get("title", "Sans titre")
        article_url = entry.get("link", "")
        if not article_url:
            continue

        raw_content = entry.get("summary") or entry.get("description") or ""
        if "content" in entry and len(entry.content) > 0:
            raw_content = entry.content[0].get("value", raw_content)

        res_extract = extract_full_article_content(article_url, raw_content)
        full_content, is_paywalled, is_full_text_available = res_extract[0], res_extract[1], res_extract[2]
        html_page = res_extract[3] if len(res_extract) > 3 else ""
        image_url = extract_main_image_url(entry, full_content, html_page=html_page, article_url=article_url)

        pub_date_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub_date_struct:
            pub_date = datetime.fromtimestamp(time.mktime(pub_date_struct)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            pub_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        art_lang = language or detect_language_from_text(article_title + " " + (full_content[:200] if full_content else ""))

        conn_art = get_db_connection()
        try:
            conn_art.execute(
                """
                INSERT INTO articles (feed_id, title, content, url, published_date, image_url, language, is_full_text, is_paywalled, is_full_text_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feed_id, article_title, full_content, article_url, pub_date, image_url, art_lang, 1, 1 if is_paywalled else 0, 1 if is_full_text_available else 0)
            )
            conn_art.commit()
            articles_added += 1
        except Exception:
            pass
        finally:
            conn_art.close()

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
    from urllib.parse import urlparse

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, title, category, language, is_full_text, created_at FROM feeds ORDER BY id DESC")
    rows = cursor.fetchall()

    # Build domain -> trust metadata lookup from catalog_feeds
    catalog_trust = {}
    try:
        cat_rows = cursor.execute(
            "SELECT url, site_url, is_jti_certified, factuality_rating, bias_rating, media_type FROM catalog_feeds"
        ).fetchall()
        for cr in cat_rows:
            for col in ['url', 'site_url']:
                raw = cr[col]
                if raw:
                    try:
                        domain = urlparse(raw).netloc.lower().replace('www.', '')
                        if domain and domain not in catalog_trust:
                            catalog_trust[domain] = {
                                'is_jti_certified': bool(cr['is_jti_certified']),
                                'factuality_rating': cr['factuality_rating'],
                                'bias_rating': cr['bias_rating'],
                                'media_type': cr['media_type'],
                            }
                    except Exception:
                        pass
    except Exception:
        pass

    conn.close()

    result = []
    for row in rows:
        feed = dict(row)
        # Look up trust data by feed domain
        try:
            domain = urlparse(feed['url']).netloc.lower().replace('www.', '')
            trust = catalog_trust.get(domain, {})
        except Exception:
            trust = {}
        feed['is_jti_certified'] = trust.get('is_jti_certified', False)
        feed['factuality_rating'] = trust.get('factuality_rating')
        feed['bias_rating'] = trust.get('bias_rating')
        feed['media_type'] = trust.get('media_type')
        result.append(feed)

    return result

def update_feed(feed_id: int, title: str, category: str, language: str = "fr", is_full_text: bool = True):
    from app.services.catalog import normalize_category
    norm_cat = normalize_category(category)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE feeds SET title = ?, category = ?, language = ?, is_full_text = ? WHERE id = ?",
        (title, norm_cat, language, 1 if is_full_text else 0, feed_id)
    )
    cursor.execute(
        "UPDATE articles SET language = ? WHERE feed_id = ?",
        (language, feed_id)
    )
    conn.commit()
    conn.close()
    return {"id": feed_id, "title": title, "category": norm_cat, "language": language, "is_full_text": is_full_text}

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
    # 1. Clean old expired articles based on retention settings
    clean_res = await asyncio.to_thread(clean_old_articles)

    # 2. Fetch fresh articles from all RSS feeds asynchronously in worker thread pool
    feeds = await asyncio.to_thread(get_all_feeds)
    results = []
    for f in feeds:
        try:
            res = await asyncio.to_thread(parse_and_save_feed, f["url"], f["category"], f.get("language"), bool(f.get("is_full_text")))
            results.append(res)
        except Exception as e:
            print(f"Erreur rafraîchissement flux {f['url']}: {e}")

    try:
        await asyncio.to_thread(enrich_missing_article_images)
    except Exception as e:
        print(f"Erreur enrichissement des images: {e}")

    # Use mistral key for retrocompatibility, but we should rely on settings
    m_key = api_key or settings.mistral_api_key
    g_key = settings.gemini_api_key
    
    # Read provider preferences from somewhere, for now we will pass default values
    # In a full app, these might be passed via the request or stored in DB
    vectorized_count = 0
    if m_key or g_key:
        try:
            from app.services.embeddings import vectorize_all_pending
            from app.services.clustering import precompute_and_cache_clusters

            vec_res = await vectorize_all_pending(
                mistral_key=m_key, 
                gemini_key=g_key, 
                provider=settings.vectorization_provider,
                fallback_provider=settings.vectorization_fallback_provider,
                mistral_model=settings.mistral_embed_model,
                gemini_model=settings.gemini_embed_model,
                force_revectorize=False
            )
            vectorized_count = vec_res.get("processed_count", 0)

            await precompute_and_cache_clusters(mistral_key=m_key, gemini_key=g_key)
        except Exception as e:
            print(f"Erreur auto-vectorisation & pre-clustering: {e}")

    return {
        "feeds_processed": len(results),
        "vectorized_count": vectorized_count,
        "cleaned_articles": clean_res.get("deleted_articles", 0),
        "details": results
    }
