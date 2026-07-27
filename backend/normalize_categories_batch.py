import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "vos.db"

CATEGORY_MAP = {
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

def normalize_category_string(cat_str: str) -> str:
    if not cat_str:
        return 'Général'
    raw = cat_str.strip().lower()
    if raw in CATEGORY_MAP:
        return CATEGORY_MAP[raw]
    for key, val in CATEGORY_MAP.items():
        if key in raw:
            return val
    return 'Général'

def normalize_all_db_categories():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. Normalize catalog_feeds
        cursor.execute("SELECT id, category FROM catalog_feeds")
        catalog_rows = cursor.fetchall()
        for r in catalog_rows:
            new_cat = normalize_category_string(r['category'])
            cursor.execute("UPDATE catalog_feeds SET category = ? WHERE id = ?", (new_cat, r['id']))

        # 2. Normalize feeds
        cursor.execute("SELECT id, category FROM feeds")
        user_rows = cursor.fetchall()
        for r in user_rows:
            new_cat = normalize_category_string(r['category'])
            cursor.execute("UPDATE feeds SET category = ? WHERE id = ?", (new_cat, r['id']))

        conn.commit()
        print("Successfully normalized categories in catalog_feeds and feeds tables.")
    except Exception as e:
        print(f"Error normalizing categories: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    normalize_all_db_categories()
