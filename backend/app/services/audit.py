import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List
from difflib import SequenceMatcher

def get_similar_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def run_feed_health_audit(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    
    # 1. Inactive feeds (no publication since 60 days)
    sixty_days_ago = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        SELECT f.id, f.title, f.url, MAX(a.published_date) as last_pub
        FROM feeds f
        LEFT JOIN articles a ON a.feed_id = f.id
        GROUP BY f.id
        HAVING last_pub < ? OR last_pub IS NULL
    """, (sixty_days_ago,))
    inactive_rows = cursor.fetchall()
    inactive_feeds = [{"id": r["id"], "title": r["title"], "last_pub": r["last_pub"]} for r in inactive_rows]
    
    # 2. 14-day activity
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT date(published_date) as pdate, COUNT(id) as count
        FROM articles
        WHERE published_date >= ?
        GROUP BY pdate
        ORDER BY pdate ASC
    """, (fourteen_days_ago,))
    activity_rows = cursor.fetchall()
    activity_14d = {r["pdate"]: r["count"] for r in activity_rows}
    
    # Fill missing days
    for i in range(15):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        if d not in activity_14d:
            activity_14d[d] = 0
    activity_14d = dict(sorted(activity_14d.items()))

    # 3. Category distribution (from catalog_feeds)
    cursor.execute("""
        SELECT category, COUNT(id) as count
        FROM catalog_feeds
        GROUP BY category
    """)
    cat_rows = cursor.fetchall()
    total_feeds = sum(r["count"] for r in cat_rows) or 1
    category_distribution = {r["category"]: round((r["count"] / total_feeds) * 100, 2) for r in cat_rows}

    # 4. Rule of 3 Sources Alert (analyzing user's active subscriptions)
    cursor.execute("""
        SELECT f.category, cf.media_type, COUNT(f.id) as count
        FROM feeds f
        LEFT JOIN catalog_feeds cf ON LOWER(f.url) = LOWER(cf.url) OR LOWER(f.url) = LOWER(cf.site_url)
        GROUP BY f.category, cf.media_type
    """)
    user_cat_type_rows = cursor.fetchall()
    
    cursor.execute("""
        SELECT category, COUNT(id) as total_count
        FROM feeds
        GROUP BY category
    """)
    cat_totals = {r["category"]: r["total_count"] for r in cursor.fetchall()}

    category_media_types = defaultdict(set)
    for r in user_cat_type_rows:
        cat = r["category"] or "Général"
        m_type = r["media_type"] or "Général"
        category_media_types[cat].add(m_type)

    alerts_rule_of_3 = []
    for cat, total in cat_totals.items():
        types = category_media_types.get(cat, set())
        if total < 3 or len(types) < 2:
            alerts_rule_of_3.append({
                "category": cat,
                "current_count": total,
                "current_types": list(types),
                "alert": f"Catégorie '{cat}' ({total} source{'s' if total>1 else ''}). Diversifiez en ajoutant une Agence ou de l'Analyse pour compléter la Triade."
            })

    # 5. Semantic duplicates
    # For each feed, get last 10 articles. If >80% are very similar to each other or to other feeds.
    # To keep it extremely fast, we'll just check title similarity within the same feed for repetitive dispatches,
    # or identical titles across feeds in the last 2 days.
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT feed_id, title 
        FROM articles 
        WHERE published_date >= ?
        ORDER BY published_date DESC
    """, (two_days_ago,))
    recent_articles = cursor.fetchall()
    
    title_counts = defaultdict(int)
    feed_title_counts = defaultdict(lambda: defaultdict(int))
    for r in recent_articles:
        t = r["title"].strip().lower()
        title_counts[t] += 1
        feed_title_counts[r["feed_id"]][t] += 1
        
    semantic_duplicates = []
    for feed_id, titles in feed_title_counts.items():
        dupes = sum(1 for t, c in titles.items() if c > 1 or title_counts[t] > 2)
        if dupes >= 8: # If 8+ recent articles are highly duplicated
            semantic_duplicates.append({
                "feed_id": feed_id,
                "duplicate_count": dupes,
                "warning": ">80% de dépêches identiques ou très similaires récemment."
            })

    # Calculate Global Hygiene Score
    cursor.execute("SELECT COUNT(id) FROM feeds")
    total_active_feeds = cursor.fetchone()[0]
    
    penalty = 0
    if total_active_feeds > 0:
        penalty += (len(inactive_feeds) / total_active_feeds) * 30 # Up to 30 points penalty for inactive
        penalty += (len(semantic_duplicates) / total_active_feeds) * 40 # Up to 40 points for duplicates
    penalty += len(alerts_rule_of_3) * 5 # 5 points per alert
    
    score = max(0, min(100, 100 - penalty))

    return {
        "global_hygiene_score": round(score, 1),
        "inactive_feeds": inactive_feeds,
        "semantic_duplicates": semantic_duplicates,
        "alerts_rule_of_3": alerts_rule_of_3,
        "activity_14_days": activity_14d,
        "category_distribution": category_distribution
    }

def clean_inactive_feeds(conn: sqlite3.Connection, feed_ids: List[int]):
    cursor = conn.cursor()
    if not feed_ids:
        return 0
    
    placeholders = ",".join("?" * len(feed_ids))
    # Delete articles
    cursor.execute(f"DELETE FROM articles WHERE feed_id IN ({placeholders})", feed_ids)
    # Delete feeds
    cursor.execute(f"DELETE FROM feeds WHERE id IN ({placeholders})", feed_ids)
    
    conn.commit()
    return cursor.rowcount
