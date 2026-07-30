import sqlite3
import json
import glob

# 1. Connexion à ta base
conn = sqlite3.connect('vos.db')
cursor = conn.cursor()

# 2. Recherche de tous les fichiers terminés par "_done.json" dans le dossier batches
done_files = glob.glob("batches/*_done.json")
total_updated = 0

print(f"Fichiers trouvés pour l'import : {done_files}")

# 3. Mise à jour de la base de données
for file in done_files:
    with open(file, "r", encoding="utf-8") as f:
        updates = json.load(f)
        
    for item in updates:
        # On met à jour uniquement la colonne enriched_description
        cursor.execute("""
            UPDATE catalog_feeds 
            SET enriched_description = ? 
            WHERE id = ?
        """, (item['new_description'], item['id']))
        total_updated += 1

# 4. Sauvegarde (commit) et fermeture
conn.commit()
conn.close()

print(f"🎉 {total_updated} descriptions enrichies mises à jour avec succès dans vos.db !")