import re
from typing import List, Dict, Any
from app.database import get_db_connection

def tokenize(text: str) -> set:
    if not text:
        return set()
    return set(re.findall(r'\b\w{4,}\b', text.lower()))

def get_smart_feed_recommendations(limit: int = 6) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch user feeds
    user_feeds = cursor.execute("SELECT id, url, title, category FROM feeds").fetchall()
    
    # 2. Fetch all catalog feeds with tags
    catalog_query = """
        SELECT cf.id, cf.url, cf.site_url, cf.title, cf.description, cf.icon_url, cf.category, cf.is_verified,
               cf.is_full_text, cf.is_jti_certified, cf.factuality_rating, cf.bias_rating, cf.media_type,
               GROUP_CONCAT(t.name) as tags
        FROM catalog_feeds cf
        LEFT JOIN catalog_feed_tags cft ON cf.id = cft.catalog_feed_id
        LEFT JOIN tags t ON cft.tag_id = t.id
        GROUP BY cf.id
    """
    catalog_rows = [dict(r) for r in cursor.execute(catalog_query).fetchall()]
    
    # Fetch active user media credentials
    user_cred_domains = set()
    try:
        cred_rows = cursor.execute("SELECT domain FROM media_credentials").fetchall()
        for c in cred_rows:
            if c['domain']:
                user_cred_domains.add(c['domain'].lower().replace('www.', ''))
    except Exception:
        pass

    PAYWALLED_DOMAINS = {
        'nzz.ch', 'letemps.ch', 'lemonde.fr', 'mediapart.fr', 'nature.com', 
        'lqj.ch', 'wsj.com', 'nytimes.com', 'ft.com', 'economist.com',
        'lefigaro.fr', 'lesechos.fr'
    }

    def is_feed_paywalled(url: str, site_url: str, is_full_text: int = 1) -> bool:
        combined = f"{url or ''} {site_url or ''}".lower()
        if is_full_text == 0 or is_full_text is False:
            if any(u_dom in combined for u_dom in user_cred_domains):
                return False
            return True
        if 'next.ink/feed/feed' in combined or 'next.ink/feed/' in combined:
            if 'next.ink/feed/free' not in combined:
                return True
        for p_dom in PAYWALLED_DOMAINS:
            if p_dom in combined:
                if not any(u_dom in combined for u_dom in user_cred_domains):
                    return True
        return False

    user_urls = {f['url'] for f in user_feeds if f['url']}
    user_cats = {f['category'] for f in user_feeds if f['category']}
    
    user_tokens = set()
    user_tags = set()
    for f in user_feeds:
        user_tokens.update(tokenize(f['title']))
        if f['category']:
            user_tags.add(f['category'].lower())
            
    candidates = []
    
    for row in catalog_rows:
        if row['url'] in user_urls:
            continue
            
        if is_feed_paywalled(row['url'], row['site_url'], row.get('is_full_text', 1)):
            continue
            
        cat = row['category']
        c_tags = set(row['tags'].split(',')) if row['tags'] else set()
        c_tokens = tokenize(row['title']) | tokenize(row['description'])
        
        cat_score = 40 if cat and cat in user_cats else 0
        tag_overlap = len(user_tags.intersection({t.lower() for t in c_tags}))
        tag_score = min(30, tag_overlap * 10)
        token_overlap = len(user_tokens.intersection(c_tokens))
        token_score = min(30, token_overlap * 5)
        
        total_score = cat_score + tag_score + token_score
        
        if total_score > 0:
            rec = dict(row)
            rec['tags'] = list(c_tags)
            rec['score'] = total_score
            rec['explanation'] = f"Recommandé à {int(total_score)}% pour équilibrer vos abonnements"
            candidates.append(rec)
            
    candidates.sort(key=lambda x: x['score'], reverse=True)
    best = candidates[:limit]
    
    if len(best) < limit:
        for row in catalog_rows:
            if row['url'] not in user_urls and row['url'] not in [b['url'] for b in best]:
                if not is_feed_paywalled(row['url'], row['site_url'], row.get('is_full_text', 1)):
                    rec = dict(row)
                    rec['tags'] = row['tags'].split(',') if row['tags'] else []
                    rec['explanation'] = "Recommandation découverte (Accès Libre)"
                    best.append(rec)
                    if len(best) == limit:
                        break
                    
    for b in best:
        if 'score' in b:
            del b['score']
            
    conn.close()
    return best

def get_triad_pack_for_category(category: str) -> Dict[str, Any]:
    """
    Selects 3 distinct, complementary high-quality feeds for `category`
    forming a balanced triad (1 Agence/Factuel, 1 Analyse, 1 Général/Régional).
    """
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

    query = """
        SELECT cf.*
        FROM catalog_feeds cf
        WHERE LOWER(cf.category) = LOWER(?)
        ORDER BY cf.is_verified DESC, cf.is_jti_certified DESC
    """
    rows = [dict(r) for r in cursor.execute(query, (category,)).fetchall()]

    if not rows:
        query_fallback = "SELECT cf.* FROM catalog_feeds cf ORDER BY cf.is_verified DESC, cf.is_jti_certified DESC LIMIT 10"
        rows = [dict(r) for r in cursor.execute(query_fallback).fetchall()]

    valid_rows = []
    for r in rows:
        combined = f"{r.get('url', '')} {r.get('site_url', '')}".lower().replace('www.', '')
        is_pw = any(p_dom in combined for p_dom in PAYWALLED_DOMAINS) or r.get('is_full_text') == 0
        has_cookie = any(c_dom in combined for c_dom in user_cred_domains)
        if is_pw and not has_cookie:
            continue
        valid_rows.append(r)

    rows = valid_rows

    agencies = [r for r in rows if r.get('media_type') == 'Agence' or r.get('is_jti_certified')]
    analysis = [r for r in rows if r.get('media_type') == 'Analyse']
    
    pack = []
    if agencies:
        pack.append(agencies[0])
    if analysis and not any(p['id'] == analysis[0]['id'] for p in pack):
        pack.append(analysis[0])
    
    for r in rows:
        if len(pack) >= 3:
            break
        if not any(p['id'] == r['id'] for p in pack):
            pack.append(r)

    conn.close()

    return {
        "category": category,
        "pack_feeds": pack
    }
