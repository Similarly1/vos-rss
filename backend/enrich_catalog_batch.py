import asyncio
import sqlite3
from pathlib import Path
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db_connection
from app.services.catalog import enrich_feed_description

async def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category FROM catalog_feeds WHERE description IS NULL OR description = '' OR enriched_description IS NULL OR enriched_description = ''")
    rows = cursor.fetchall()
    conn.close()

    print(f"Lancement de l'enrichissement des descriptions pour {len(rows)} flux...")
    
    for idx, r in enumerate(rows, 1):
        feed_id, title, cat = r['id'], r['title'], r['category']
        print(f"[{idx}/{len(rows)}] Traitement de '{title}' (ID {feed_id})...")
        try:
            res = await enrich_feed_description(feed_id)
            desc_preview = res.get('description', '')[:80]
            print(f"   -> Description : {desc_preview}...")
        except Exception as e:
            print(f"   Note : {e}")

    print("Enrichissement du catalogue termine avec succes !")

if __name__ == "__main__":
    asyncio.run(main())
