import sqlite3
from pathlib import Path

db_path = Path("./vos.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE feeds SET category = 'Suisse' WHERE title LIKE '%Suisse%' OR title LIKE '%RTS%' OR title LIKE '%Le Temps%'")
    cursor.execute("UPDATE feeds SET category = 'Europe' WHERE (title LIKE '%Monde%' OR title LIKE '%Mediapart%' OR title LIKE '%Spiegel%' OR title LIKE '%Tagesschau%' OR title LIKE '%País%') AND category != 'Suisse'")
    cursor.execute("UPDATE feeds SET category = 'Monde' WHERE title LIKE '%BBC%' OR title LIKE '%Guardian%'")
    cursor.execute("UPDATE feeds SET category = 'Monde' WHERE category = 'Presse'")
    conn.commit()
    
    rows = cursor.execute("SELECT id, title, category FROM feeds").fetchall()
    print("Mise à jour des catégories terminée :")
    for r in rows:
        print(f"  [{r[0]}] {r[1]} -> {r[2]}")
    conn.close()
