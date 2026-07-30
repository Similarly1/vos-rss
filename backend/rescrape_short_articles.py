import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import sqlite3
from app.services.rss import extract_full_article_content

def rescrape_all():
    conn = sqlite3.connect('backend/vos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    short_arts = cursor.execute("SELECT id, title, url, content FROM articles WHERE LENGTH(content) < 400 AND url LIKE 'http%'").fetchall()
    print(f"[Re-scraper] Trouvé {len(short_arts)} articles avec contenu court à ré-extraire.")

    updated_count = 0
    for a in short_arts:
        try:
            full_text, is_pw, is_ft = extract_full_article_content(a['url'], a['content'])
            if len(full_text) > len(a['content']):
                cursor.execute(
                    "UPDATE articles SET content = ?, is_paywalled = ?, is_full_text_available = ? WHERE id = ?",
                    (full_text, 1 if is_pw else 0, 1 if is_ft else 0, a['id'])
                )
                updated_count += 1
                print(f"  ✓ [{a['id']}] Mis à jour ({len(a['content'])} -> {len(full_text)} caractères) : {a['title'][:50]}")
        except Exception as e:
            print(f"  ✗ Erreur pour {a['id']} : {e}")

    conn.commit()
    conn.close()
    print(f"[Re-scraper] Terminé : {updated_count}/{len(short_arts)} articles ré-enrichis en texte intégral.")

if __name__ == '__main__':
    rescrape_all()
