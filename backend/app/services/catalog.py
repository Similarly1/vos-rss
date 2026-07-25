import re
import sqlite3
from typing import List, Dict, Any, Optional
from app.database import get_db_connection

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
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search and filter catalog feeds.
    Returns list of dicts with feed details and associated tags list.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

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
        # Check if FTS is available
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
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        # Fallback query if FTS query syntax error
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
        rows = cursor.fetchall()

    results = []
    for row in rows:
        feed_dict = dict(row)
        feed_id = feed_dict['id']
        
        # Fetch tags for this feed
        cursor.execute("""
            SELECT t.name, t.slug 
            FROM tags t
            JOIN catalog_feed_tags cft ON t.id = cft.tag_id
            WHERE cft.catalog_feed_id = ?
        """, (feed_id,))
        tags_rows = cursor.fetchall()
        feed_dict['tags'] = [t['name'] for t in tags_rows]
        feed_dict['is_full_text'] = bool(feed_dict.get('is_full_text', 1))
        feed_dict['is_verified'] = bool(feed_dict.get('is_verified', 1))
        results.append(feed_dict)

    conn.close()
    return results

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
