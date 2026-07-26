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
               GROUP_CONCAT(t.name) as tags
        FROM catalog_feeds cf
        LEFT JOIN catalog_feed_tags cft ON cf.id = cft.catalog_feed_id
        LEFT JOIN tags t ON cft.tag_id = t.id
        GROUP BY cf.id
    """
    catalog_rows = cursor.execute(catalog_query).fetchall()
    
    if not user_feeds:
        # Default recommendations
        recs = []
        for row in catalog_rows:
            if row['is_verified']:
                rec = dict(row)
                rec['explanation'] = "Recommandation populaire"
                rec['tags'] = rec['tags'].split(',') if rec['tags'] else []
                recs.append(rec)
                if len(recs) == limit:
                    break
        conn.close()
        return recs
    
    user_urls = {f['url'] for f in user_feeds}
    
    # Analyze user profile
    user_tokens = set()
    user_categories = {}
    user_tags = {}
    
    # Map catalog info for user feeds
    catalog_by_url = {row['url']: row for row in catalog_rows}
    
    for f in user_feeds:
        user_tokens.update(tokenize(f['title']))
        cat = f['category']
        if cat:
            user_categories[cat] = user_categories.get(cat, 0) + 1
            
        c_row = catalog_by_url.get(f['url'])
        if c_row and c_row['tags']:
            for t in c_row['tags'].split(','):
                user_tags[t] = user_tags.get(t, 0) + 1
                
    top_user_category = max(user_categories.keys(), key=lambda k: user_categories[k]) if user_categories else "Général"
    top_user_tag = max(user_tags.keys(), key=lambda k: user_tags[k]) if user_tags else None
    
    # Candidate scoring
    candidates = []
    for row in catalog_rows:
        if row['url'] in user_urls:
            continue
            
        cat = row['category']
        tags_list = row['tags'].split(',') if row['tags'] else []
        c_tags = set(tags_list)
        c_tokens = tokenize(row['title']) | tokenize(row['description'])
        
        # Semantic/Content score (0 to 60)
        token_overlap = len(c_tokens & user_tokens)
        token_score = min(token_overlap * 10, 40) # max 40 points for tokens
        cat_score = 20 if cat in user_categories else 0
        content_score = token_score + cat_score
        
        # Tags overlap score (0 to 40)
        tag_overlap = len(c_tags & set(user_tags.keys()))
        tag_score = min(tag_overlap * 20, 40)
        
        total_score = content_score + tag_score
        
        if total_score > 0:
            rec = dict(row)
            rec['tags'] = tags_list
            rec['score'] = total_score
            
            # Generate explanation
            if tag_overlap > 0 and top_user_tag in c_tags:
                rec['explanation'] = f"{int((total_score / 100) * 99 + 1)}% de pertinence avec vos lectures '{top_user_tag.capitalize()}'"
            elif cat_score > 0:
                rec['explanation'] = f"Basé sur votre intérêt pour la catégorie {cat}"
            else:
                user_feed_names = [f['title'] for f in user_feeds[:2]]
                rec['explanation'] = f"Basé sur vos abonnements {', '.join(user_feed_names)}"
                
            candidates.append(rec)
            
    # Sort and take top N
    candidates.sort(key=lambda x: x['score'], reverse=True)
    best = candidates[:limit]
    
    # Fallback if not enough candidates
    if len(best) < limit:
        for row in catalog_rows:
            if row['url'] not in user_urls and row['url'] not in [b['url'] for b in best]:
                rec = dict(row)
                rec['tags'] = row['tags'].split(',') if row['tags'] else []
                rec['explanation'] = "Recommandation découverte"
                best.append(rec)
                if len(best) == limit:
                    break
                    
    # Clean up response payload (remove score for API if we want, or keep it)
    for b in best:
        if 'score' in b:
            del b['score']
            
    conn.close()
    return best
