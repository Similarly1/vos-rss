import sqlite3
import json
from collections import defaultdict
from typing import Dict, Any, List
from pathlib import Path

db_path = Path(__file__).parent.parent / "vos.db"

def get_db_connection():
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def run_feed_health_audit() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total feeds followed
    cursor.execute("SELECT id, title, url, category, created_at FROM feeds")
    active_feeds = [dict(r) for r in cursor.fetchall()]
    total_active_feeds = len(active_feeds)

    # Ignored categories for audit
    ignored_categories = set()
    try:
        cursor.execute("SELECT value FROM app_settings WHERE key = 'ignored_audit_categories'")
        row = cursor.fetchone()
        if row and row["value"]:
            ignored_categories = set(json.loads(row["value"]))
    except Exception:
        ignored_categories = set()

    # 2. Inactive feeds (no published articles in last 60 days)
    cursor.execute("""
        SELECT f.id, f.title, f.url, MAX(a.published_date) as last_article_date
        FROM feeds f
        LEFT JOIN articles a ON f.id = a.feed_id
        GROUP BY f.id
        HAVING last_article_date IS NULL OR last_article_date < datetime('now', '-60 days')
    """)
    inactive_feeds = [dict(r) for r in cursor.fetchall()]

    # 3. Category distribution from user active feeds
    cursor.execute("""
        SELECT category, COUNT(id) as count
        FROM feeds
        GROUP BY category
    """)
    cat_rows = cursor.fetchall()
    total_user_feeds = sum(r["count"] for r in cat_rows) or 1
    category_distribution = { (r["category"] or "Général"): round((r["count"] / total_user_feeds) * 100, 2) for r in cat_rows }

    # 4. Rule of 3 Sources Alert (Analyzing user active subscriptions)
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
    cat_totals = { (r["category"] or "Général"): r["total_count"] for r in cursor.fetchall() }

    category_media_types = defaultdict(set)
    for r in user_cat_type_rows:
        cat = r["category"] or "Général"
        m_type = r["media_type"] or "Général"
        category_media_types[cat].add(m_type)

    alerts_rule_of_3 = []
    for cat, total in cat_totals.items():
        if cat in ignored_categories:
            continue
        if total < 3:
            missing = 3 - total
            alerts_rule_of_3.append({
                "category": cat,
                "current_count": total,
                "missing_count": missing,
                "alert": f"Catégorie '{cat}' ({total}/3 sources). Il manque {missing} source{'s' if missing > 1 else ''} pour équilibrer la Triade."
            })

    # 5. Semantic duplicates (identical dispatches or duplicate URLs)
    cursor.execute("""
        SELECT f1.id as feed1_id, f1.title as title1, f2.id as feed2_id, f2.title as title2
        FROM feeds f1
        JOIN feeds f2 ON LOWER(f1.url) = LOWER(f2.url) AND f1.id < f2.id
    """)
    semantic_duplicates = [{"feed_id": r["feed2_id"], "title": r["title2"], "duplicate_of": r["title1"]} for r in cursor.fetchall()]

    # 6. Activity over last 14 days
    cursor.execute("""
        SELECT strftime('%Y-%m-%d', published_date) as day, COUNT(id) as count
        FROM articles
        WHERE published_date >= datetime('now', '-14 days')
        GROUP BY day
        ORDER BY day ASC
    """)
    activity_14d = [dict(r) for r in cursor.fetchall()]

    # Calculate Overall Health Score (0-100)
    # Deductions:
    # - Inactive feeds: -15 per feed (max 40)
    # - Semantic duplicates: -10 per dup (max 30)
    # - Rule of 3 sources incomplete categories: -10 per incomplete cat (max 30)
    deductions = 0
    deductions += min(40, len(inactive_feeds) * 15)
    deductions += min(30, len(semantic_duplicates) * 10)
    deductions += min(30, len(alerts_rule_of_3) * 10)

    health_score = max(0, 100 - deductions)

    status_label = "Excellente" if health_score >= 85 else ("Bonne" if health_score >= 65 else "À améliorer")

    conn.close()

    return {
        "health_score": health_score,
        "status_label": status_label,
        "total_active_feeds": total_active_feeds,
        "inactive_feeds_count": len(inactive_feeds),
        "inactive_feeds": inactive_feeds,
        "semantic_duplicates_count": len(semantic_duplicates),
        "semantic_duplicates": semantic_duplicates,
        "rule_of_3_alerts": alerts_rule_of_3,
        "category_distribution": category_distribution,
        "activity_14d": activity_14d
    }

def get_categories_balance_audit() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ignored categories
    ignored = set()
    try:
        cursor.execute("SELECT value FROM app_settings WHERE key = 'ignored_audit_categories'")
        row = cursor.fetchone()
        if row and row["value"]:
            ignored = set(json.loads(row["value"]))
    except Exception:
        ignored = set()

    # User active feeds count by category
    cursor.execute("""
        SELECT category, COUNT(id) as count
        FROM feeds
        GROUP BY category
    """)
    user_cats = { (r["category"] or "Général"): r["count"] for r in cursor.fetchall() }

    # Available categories from catalog
    cursor.execute("""
        SELECT DISTINCT category FROM catalog_feeds WHERE category IS NOT NULL AND category != ''
    """)
    catalog_cats = { (r["category"] or "Général") for r in cursor.fetchall() }

    all_cats = sorted(list(set(list(user_cats.keys()) + list(catalog_cats))))
    categories_result = []

    for cat in all_cats:
        count = user_cats.get(cat, 0)
        is_ignored = cat in ignored
        missing_count = max(0, 3 - count)
        status = "balanced" if count >= 3 else ("incomplete" if count > 0 else "missing")

        categories_result.append({
            "category": cat,
            "count": count,
            "status": status,
            "missing_count": missing_count,
            "is_ignored": is_ignored
        })

    conn.close()

    return {
        "categories": categories_result,
        "total_followed": len(user_cats),
        "total_balanced": sum(1 for c in categories_result if c["status"] == "balanced"),
        "total_incomplete": sum(1 for c in categories_result if c["status"] == "incomplete" and not c["is_ignored"])
    }

def toggle_ignore_audit_category(category: str, ignore: bool) -> List[str]:
    conn = get_db_connection()
    cursor = conn.cursor()

    ignored = set()
    try:
        cursor.execute("SELECT value FROM app_settings WHERE key = 'ignored_audit_categories'")
        row = cursor.fetchone()
        if row and row["value"]:
            ignored = set(json.loads(row["value"]))
    except Exception:
        ignored = set()

    if ignore:
        ignored.add(category)
    else:
        ignored.discard(category)

    val_json = json.dumps(list(ignored))
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('ignored_audit_categories', ?)", (val_json,))
    conn.commit()
    conn.close()

    return list(ignored)

def clean_inactive_feeds(feed_ids: list) -> int:
    if not feed_ids:
        return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(feed_ids))
    cursor.execute(f"DELETE FROM articles WHERE feed_id IN ({placeholders})", feed_ids)
    cursor.execute(f"DELETE FROM feeds WHERE id IN ({placeholders})", feed_ids)
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count
