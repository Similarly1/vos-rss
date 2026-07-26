import sqlite3

conn = sqlite3.connect('vos.db')
cursor = conn.cursor()

cursor.execute("SELECT id, title, category, description, enriched_description FROM catalog_feeds")
rows = cursor.fetchall()

generic_count = 0
rich_count = 0

for r in rows:
    fid, title, cat, desc, enriched = r
    d = (enriched or desc or '').strip()
    if 'Publication spécialisée' in d or "Source d'information" in d:
        generic_count += 1
    else:
        rich_count += 1

print(f"Total feeds: {len(rows)}")
print(f"Rich custom descriptions: {rich_count}")
print(f"Generic fallback descriptions: {generic_count}")

print("\n--- Exemples de 5 flux avec description générique ---")
ex_g = [r for r in rows if 'Publication spécialisée' in (r[4] or r[3] or '') or "Source d'information" in (r[4] or r[3] or '')][:5]
for r in ex_g:
    print(f"[{r[0]}] {r[1]} -> DESC: {(r[3] or '')[:80]} | ENRICHED: {(r[4] or '')[:80]}")

print("\n--- Exemples de 5 flux avec description riche ---")
ex_r = [r for r in rows if 'Publication spécialisée' not in (r[4] or r[3] or '') and "Source d'information" not in (r[4] or r[3] or '')][:5]
for r in ex_r:
    print(f"[{r[0]}] {r[1]} -> DESC: {(r[3] or '')[:80]} | ENRICHED: {(r[4] or '')[:80]}")

conn.close()
