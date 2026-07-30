import sqlite3
import json
import os

# 1. Connexion à la base de données
conn = sqlite3.connect('vos.db')
cursor = conn.cursor()

# 2. Récupération des données (avec l'URL ajoutée)
cursor.execute("SELECT id, title, url, category, description, enriched_description FROM catalog_feeds")
rows = cursor.fetchall()

feeds_to_enrich = []

# 3. Tri des flux
for r in rows:
    fid, title, url, cat, desc, enriched = r
    d = (enriched or desc or '').strip()
    
    # Ta logique pour repérer les descriptions génériques ou vides
    if not d or 'Publication spécialisée' in d or "Source d'information" in d:
        feeds_to_enrich.append({
            "id": fid,
            "title": title,
            "url": url,
            "category": cat,
            "current_description": d
        })

conn.close()

# 4. Création du dossier pour les lots
os.makedirs("batches", exist_ok=True)

# 5. Découpage par lots de 30 flux
batch_size = 30
for i in range(0, len(feeds_to_enrich), batch_size):
    batch = feeds_to_enrich[i:i + batch_size]
    batch_num = (i // batch_size) + 1
    filename = f"batches/batch_{batch_num:02d}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

print(f"✅ {len(feeds_to_enrich)} flux à enrichir exportés !")
print(f"📁 {(len(feeds_to_enrich) // batch_size) + 1} fichiers créés dans le dossier 'batches/'")