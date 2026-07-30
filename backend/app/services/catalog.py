import re
import sqlite3
import datetime
import httpx
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from typing import List, Dict, Any, Optional
from app.database import get_db_connection

CATEGORY_FR_MAP = {
    'presse': 'Actualités & Presse',
    'actualités': 'Actualités & Presse',
    'actualites': 'Actualités & Presse',
    'news': 'Actualités & Presse',
    'une': 'Actualités & Presse',

    'technologie': 'Technologie & Cyber',
    'technology': 'Technologie & Cyber',
    'tech': 'Technologie & Cyber',
    'cybersecurite': 'Technologie & Cyber',
    'cyber': 'Technologie & Cyber',

    'business & economy': 'Économie & Business',
    'business': 'Économie & Business',
    'économie': 'Économie & Business',
    'economie': 'Économie & Business',
    'finance': 'Économie & Business',

    'suisse': 'Suisse & Régional',
    'régional': 'Suisse & Régional',
    'regional': 'Suisse & Régional',
    'local': 'Suisse & Régional',

    'monde': 'International & Monde',
    'world': 'International & Monde',
    'international': 'International & Monde',

    'science': 'Science & Climat',
    'environnement': 'Science & Climat',
    'climat': 'Science & Climat',
    'space': 'Science & Climat',

    'culture': 'Culture & Société',
    'art': 'Culture & Société',
    'société': 'Culture & Société',
    'societe': 'Culture & Société',

    'chrétien': 'Foi & Spiritualité',
    'chretien': 'Foi & Spiritualité',
    'religion': 'Foi & Spiritualité',
    'foi': 'Foi & Spiritualité',

    'général': 'Général',
    'general': 'Général',
}

CANONICAL_CATEGORIES = [
    'Actualités & Presse',
    'Technologie & Cyber',
    'Économie & Business',
    'Suisse & Régional',
    'International & Monde',
    'Science & Climat',
    'Culture & Société',
    'Foi & Spiritualité',
    'Général'
]

def normalize_category(cat: Optional[str]) -> str:
    if not cat:
        return 'Général'
    raw = cat.strip().lower()
    if raw in CATEGORY_FR_MAP:
        return CATEGORY_FR_MAP[raw]
    for key, val in CATEGORY_FR_MAP.items():
        if key in raw:
            return val
    return 'Général'

def slugify(text: str) -> str:
    """Converts string into clean URL-friendly slug, e.g. '#Cybersécurité' -> 'cybersecurite'."""
    text = text.lower().strip()
    text = re.sub(r'^[#\s]+', '', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[àâä]', 'a', text)
    text = re.sub(r'[îï]', 'i', text)
    text = re.sub(r'[ôö]', 'o', text)
    text = re.sub(r'[ùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9_-]', '_', text)
    return text

def add_or_update_catalog_feed(feed_data: Dict[str, Any], tags: List[str] = None) -> int:
    """
    Inserts or updates a catalog feed, assigns tags, and updates the FTS5 index.
    feed_data keys: url, site_url, title, description, icon_url, category, language, country, is_full_text, is_verified
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    url = feed_data['url'].strip()
    title = feed_data.get('title', '').strip() or url
    description = feed_data.get('description', '').strip()
    site_url = feed_data.get('site_url', '').strip()
    icon_url = feed_data.get('icon_url', '').strip()
    category = feed_data.get('category', 'Général').strip()
    language = feed_data.get('language', 'fr').strip()
    country = feed_data.get('country', '').strip()
    is_full_text = 1 if feed_data.get('is_full_text', True) else 0
    is_verified = 1 if feed_data.get('is_verified', True) else 0

    cursor.execute('''
        INSERT INTO catalog_feeds (url, site_url, title, description, icon_url, category, language, country, is_full_text, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            site_url = excluded.site_url,
            title = excluded.title,
            description = excluded.description,
            icon_url = COALESCE(NULLIF(excluded.icon_url, ''), catalog_feeds.icon_url),
            category = excluded.category,
            language = excluded.language,
            country = excluded.country,
            is_full_text = excluded.is_full_text,
            is_verified = excluded.is_verified
    ''', (url, site_url, title, description, icon_url, category, language, country, is_full_text, is_verified))
    
    cursor.execute('SELECT id FROM catalog_feeds WHERE url = ?', (url,))
    feed_row = cursor.fetchone()
    if not feed_row:
        conn.close()
        return 0
    feed_id = feed_row['id']

    # Update FTS5 index
    try:
        cursor.execute('DELETE FROM catalog_feeds_fts WHERE catalog_feed_id = ?', (feed_id,))
        cursor.execute('''
            INSERT INTO catalog_feeds_fts(catalog_feed_id, title, description, category)
            VALUES (?, ?, ?, ?)
        ''', (feed_id, title, description, category))
    except Exception as e:
        print(f"[Catalog FTS Note] {e}")

    # Handle Tags
    if tags:
        for tag_name in tags:
            tag_name_clean = tag_name.strip()
            if not tag_name_clean:
                continue
            if not tag_name_clean.startswith('#'):
                tag_name_clean = '#' + tag_name_clean.lstrip('#')
            
            tag_slug = slugify(tag_name_clean)
            
            cursor.execute('''
                INSERT INTO tags (name, slug) VALUES (?, ?)
                ON CONFLICT(slug) DO UPDATE SET name = excluded.name
            ''', (tag_name_clean, tag_slug))
            
            cursor.execute('SELECT id FROM tags WHERE slug = ?', (tag_slug,))
            tag_row = cursor.fetchone()
            if tag_row:
                tag_id = tag_row['id']
                cursor.execute('''
                    INSERT OR IGNORE INTO catalog_feed_tags (catalog_feed_id, tag_id)
                    VALUES (?, ?)
                ''', (feed_id, tag_id))

    conn.commit()
    conn.close()
    return feed_id

def search_catalog(
    query: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    language: Optional[str] = None,
    hide_paywalled: bool = False,
    limit: int = 30,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Search and filter catalog feeds with limit and offset pagination.
    Returns dict with feeds list, total count, and has_more flag.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    PAYWALLED_DOMAINS = {
        'nzz.ch', 'letemps.ch', 'lemonde.fr', 'mediapart.fr', 'nature.com', 
        'lqj.ch', 'wsj.com', 'nytimes.com', 'ft.com', 'economist.com',
        'lefigaro.fr', 'lesechos.fr'
    }

    user_cred_domains = set()
    if not hide_paywalled:
        try:
            row_set = cursor.execute("SELECT value FROM app_settings WHERE key = 'hide_paywalled_without_cookie'").fetchone()
            val = str(row_set['value']).lower() if row_set else 'true'
            if val == 'true':
                hide_paywalled = True
        except Exception:
            hide_paywalled = True
    try:
        cursor.execute("SELECT domain FROM media_credentials")
        user_cred_domains = {r["domain"].lower() for r in cursor.fetchall()}
    except Exception:
        user_cred_domains = set()

    sql = """
        SELECT DISTINCT cf.*
        FROM catalog_feeds cf
    """
    params = []
    where_conditions = []

    # Tag filter
    if tag and tag != 'Tous':
        clean_tag_slug = slugify(tag)
        sql += """
            JOIN catalog_feed_tags cft ON cf.id = cft.catalog_feed_id
            JOIN tags t ON cft.tag_id = t.id
        """
        where_conditions.append("t.slug = ?")
        params.append(clean_tag_slug)

    # Search Query (FTS5 or LIKE)
    q = (query or '').strip()
    if q:
        use_fts = False
        try:
            fts_query = f'"{q}"*'
            sql += " JOIN catalog_feeds_fts fts ON cf.id = fts.catalog_feed_id "
            where_conditions.append("catalog_feeds_fts MATCH ?")
            params.append(fts_query)
            use_fts = True
        except Exception:
            use_fts = False

        if not use_fts:
            like_pattern = f"%{q}%"
            where_conditions.append("(cf.title LIKE ? OR cf.description LIKE ? OR cf.url LIKE ?)")
            params.extend([like_pattern, like_pattern, like_pattern])

    # Category filter
    if category and category != 'Tous':
        where_conditions.append("LOWER(cf.category) = LOWER(?)")
        params.append(category)

    # Language filter
    if language and language != 'Tous':
        where_conditions.append("LOWER(cf.language) = LOWER(?)")
        params.append(language)

    if where_conditions:
        sql += " WHERE " + " AND ".join(where_conditions)

    sql += " ORDER BY cf.is_verified DESC, cf.title ASC"

    try:
        cursor.execute(sql, params)
        all_rows = cursor.fetchall()
    except sqlite3.OperationalError:
        sql_fallback = "SELECT DISTINCT cf.* FROM catalog_feeds cf WHERE 1=1"
        fallback_params = []
        if category and category != 'Tous':
            sql_fallback += " AND LOWER(cf.category) = LOWER(?)"
            fallback_params.append(category)
        if language and language != 'Tous':
            sql_fallback += " AND LOWER(cf.language) = LOWER(?)"
            fallback_params.append(language)
        if q:
            sql_fallback += " AND (cf.title LIKE ? OR cf.description LIKE ? OR cf.url LIKE ?)"
            like_p = f"%{q}%"
            fallback_params.extend([like_p, like_p, like_p])
        sql_fallback += " ORDER BY cf.is_verified DESC, cf.title ASC"
        cursor.execute(sql_fallback, fallback_params)
        all_rows = cursor.fetchall()

    filtered_rows = []
    for r in all_rows:
        row_dict = dict(r)
        url_text = f"{row_dict.get('url', '')} {row_dict.get('site_url', '')}".lower()
        # Normalize: strip www. for comparison
        url_text_norm = url_text.replace('www.', '')
        is_pw = any(p_dom in url_text_norm for p_dom in PAYWALLED_DOMAINS) or row_dict.get('is_full_text') == 0 or row_dict.get('is_full_text') is False
        norm_cred_domains = {d.replace('www.', '') for d in user_cred_domains}
        has_cookie = any(c_dom in url_text_norm for c_dom in norm_cred_domains)

        if hide_paywalled:
            if is_pw:
                row_dict['is_paid'] = True
                row_dict['has_cookie'] = has_cookie
                if not has_cookie:
                    continue
            else:
                row_dict['is_paid'] = False
                row_dict['has_cookie'] = False
        else:
            row_dict['is_paid'] = is_pw
            row_dict['has_cookie'] = is_pw and has_cookie
        filtered_rows.append(row_dict)

    total_count = len(filtered_rows)
    paged_rows = filtered_rows[offset:offset + limit]

    results = []
    for row in paged_rows:
        feed_dict = dict(row)
        feed_id = feed_dict['id']
        feed_dict['category'] = normalize_category(feed_dict.get('category'))
        
        desc = (feed_dict.get('enriched_description') or feed_dict.get('description') or '').strip()
        if not desc:
            cat = feed_dict['category'] or 'Général'
            title = feed_dict.get('title', 'Ce média')
            desc = f"Fil d'actualité et de veille d'information couvrant les sujets majeurs en {cat}."
        feed_dict['description'] = desc

        # Fetch tags for this feed
        cursor.execute("""
            SELECT t.name, t.slug 
            FROM tags t
            JOIN catalog_feed_tags cft ON t.id = cft.tag_id
            WHERE cft.catalog_feed_id = ?
        """, (feed_id,))
        tags_rows = cursor.fetchall()

        # Clean tags (strip leading # so UI controls hashtag formatting nicely)
        feed_dict['tags'] = [t['name'].lstrip('#') for t in tags_rows if t['name'].lstrip('#')]
        feed_dict['is_full_text'] = bool(feed_dict.get('is_full_text', 1))
        feed_dict['is_verified'] = bool(feed_dict.get('is_verified', 1))
        results.append(feed_dict)

    conn.close()
    return {
        "feeds": results,
        "total": total_count,
        "has_more": offset + limit < total_count
    }

def get_all_tags() -> List[Dict[str, Any]]:
    """Returns all tags with count of associated catalog feeds."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.name, t.slug, COUNT(cft.catalog_feed_id) as count
        FROM tags t
        JOIN catalog_feed_tags cft ON t.id = cft.tag_id
        GROUP BY t.id
        HAVING count > 0
        ORDER BY count DESC, t.name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_focus_of_the_day() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    PAYWALLED_DOMAINS = {
        'nzz.ch', 'letemps.ch', 'lemonde.fr', 'mediapart.fr', 'nature.com', 
        'lqj.ch', 'wsj.com', 'nytimes.com', 'ft.com', 'economist.com',
        'lefigaro.fr', 'lesechos.fr'
    }

    user_cred_domains = set()
    try:
        cred_rows = cursor.execute("SELECT domain FROM media_credentials").fetchall()
        for c in cred_rows:
            if c['domain']:
                user_cred_domains.add(c['domain'].lower().replace('www.', ''))
    except Exception:
        pass

    cursor.execute("SELECT * FROM catalog_feeds WHERE is_verified = 1 ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("SELECT * FROM catalog_feeds ORDER BY id")
        rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return None

    valid_rows = []
    for r in rows:
        row_dict = dict(r)
        url_text = f"{row_dict.get('url', '')} {row_dict.get('site_url', '')}".lower().replace('www.', '')
        is_pw = any(p_dom in url_text for p_dom in PAYWALLED_DOMAINS) or row_dict.get('is_full_text') == 0
        has_cookie = any(c_dom in url_text for c_dom in user_cred_domains)
        if is_pw and not has_cookie:
            continue
        valid_rows.append(row_dict)

    if not valid_rows:
        return None
        
    day_index = datetime.date.today().toordinal()
    selected = dict(valid_rows[day_index % len(valid_rows)])
    selected['category'] = normalize_category(selected.get('category'))
    selected['is_full_text'] = bool(selected.get('is_full_text', 1))
    selected['is_verified'] = bool(selected.get('is_verified', 1))
    return selected

async def enrich_feed_description(feed_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url, site_url, category, description, enriched_description FROM catalog_feeds WHERE id = ?", (feed_id,))
    feed = cursor.fetchone()
    
    if not feed:
        conn.close()
        return {"status": "error", "message": "Flux introuvable."}
        
    target_url = feed['site_url'] or feed['url']
    feed_title = feed['title'] or "Ce média"
    feed_cat = normalize_category(feed['category'])
    description = ""
    
    # ── Étape 1 : Scraping HTML Meta (description / og:description) ──
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                if BeautifulSoup:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    if meta_desc and meta_desc.get("content"):
                        description = meta_desc["content"].strip()
                    if not description:
                        og_desc = soup.find("meta", property="og:description")
                        if og_desc and og_desc.get("content"):
                            description = og_desc["content"].strip()
                else:
                    match = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
                    if not match:
                        match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:og:)?description["\']', resp.text, re.IGNORECASE)
                    if match:
                        description = match.group(1).strip()
    except Exception as e:
        print(f"[Enrichment Scrape Note] {e}")
        
    # ── Étape 2 : Parse RSS & Génération LLM (Mistral / Gemini) sur les 5 derniers articles ──
    import feedparser
    parsed = None
    try:
        parsed = feedparser.parse(feed['url'])
    except Exception as e:
        print(f"[Enrichment Feedparser Note] {e}")

    if not description and parsed and parsed.entries:
        articles_context = []
        for entry in parsed.entries[:5]:
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            clean_summary = re.sub(r'<[^>]+>', '', summary)[:120]
            if title:
                articles_context.append(f"- {title} : {clean_summary}")
            
        if articles_context:
            prompt = f"Voici les 5 derniers articles de {feed_title} (thème {feed_cat}) :\n" + "\n".join(articles_context) + "\n\nPrésente ce média en 2 phrases synthétiques et attrayantes (sans utiliser 'ce flux' ou 'ces articles')."
            
            from app.config import settings
            key = settings.mistral_api_key
            if key:
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        llm_res = await client.post(
                            "https://api.mistral.ai/v1/chat/completions",
                            json={
                                "model": "mistral-small-latest",
                                "messages": [{"role": "user", "content": prompt}]
                            },
                            headers={"Authorization": f"Bearer {key}"}
                        )
                        if llm_res.status_code == 200:
                            description = llm_res.json()["choices"][0]["message"]["content"].strip()
                except Exception as e:
                    print(f"[Enrichment LLM Note] {e}")

    # Fallback sur la description du canal RSS s'il en existe une propre
    if not description and parsed and parsed.feed.get('description'):
        raw_desc = re.sub(r'<[^>]+>', '', parsed.feed.get('description', '')).strip()
        if len(raw_desc) > 15:
            description = raw_desc[:250]

    # Fallback spécifique personnalisé
    if not description:
        description = f"Source d'information éditée par {feed_title}, proposant des reportages et analyses sur les thèmes {feed_cat}."

    if description:
        cursor.execute("UPDATE catalog_feeds SET description = ?, enriched_description = ? WHERE id = ?", (description, description, feed_id))
        conn.commit()
        
    conn.close()
    return {"status": "success", "description": description}
