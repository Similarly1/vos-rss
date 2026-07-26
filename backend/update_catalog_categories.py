import sqlite3
from pathlib import Path

db_path = Path("./vos.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE catalog_feeds SET category = 'Actualités' WHERE LOWER(category) IN ('news', 'actu', 'actualités', 'actualite')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Technologie' WHERE LOWER(category) IN ('tech', 'technology', 'technologie', 'cyber security', 'programming', 'web development', 'startups', 'gaming', 'jeux vidéo')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Économie' WHERE LOWER(category) IN ('business', 'economy', 'finance', 'économie', 'economie', 'business & economy')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Science' WHERE LOWER(category) IN ('science', 'space', 'environment', 'environnement')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Sport' WHERE LOWER(category) IN ('sports', 'sport')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Monde' WHERE LOWER(category) IN ('world', 'monde', 'europe')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Culture' WHERE LOWER(category) IN ('culture', 'entertainment', 'society', 'société')")
    cursor.execute("UPDATE catalog_feeds SET category = 'Santé' WHERE LOWER(category) IN ('health', 'santé')")
    cursor.execute("UPDATE tags SET name = '#' || LTRIM(name, '#')")
    conn.commit()
    
    rows = cursor.execute("SELECT category, COUNT(*) FROM catalog_feeds GROUP BY category").fetchall()
    print("Mise à jour des catégories du catalogue terminée :")
    for r in rows:
        print(f"  - Category '{r[0]}': {r[1]} flux")
    conn.close()
