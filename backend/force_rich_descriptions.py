import asyncio
import sqlite3
import httpx
import feedparser
import re
from pathlib import Path
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db_connection
from app.config import settings

# Custom curated descriptions for well-known catalog feeds to ensure top quality
CURATED_DESCRIPTIONS = {
    'Human Nature': "Blog scientifique d'environnment et de biologie explorant les interactions entre la nature, l'écologie et la biodiversité.",
    'r/space': "Communauté et fil d'actualité dédié à l'astronomie, à l'exploration spatiale, aux lancements de fusées et aux découvertes de la NASA.",
    '60-Second Science': "Podcast et articles courts de Scientific American décryptant en une minute les dernières avancées et curiosités scientifiques.",
    'BBC News': "Le fil officiel de la BBC couvrant l'actualité mondiale, les découvertes scientifiques, la santé et l'exploration spatiale.",
    'Bionic Planet': "Podcast axé sur les solutions écologiques et la restauration de la nature pour lutter contre le changement climatique.",
    'Conservation International': "Articles et reportages d'experts dédiés à la protection de la biodiversité mondiale et des écosystèmes menacés.",
    'Tages-Anzeiger': "Grand quotidien suisse d'information générale proposant des enquêtes, des analyses politiques et l'actualité en direct.",
    'World News': "Synthèse des grands événements internationaux, des enjeux géopolitiques et de l'actualité mondiale en continu.",
    'ReadWrite': "Média référence sur l'innovation technologique, le Web3, l'intelligence artificielle et l'écosystème startup.",
    'Blackhat Library': "Ressources et recherches spécialisées en cybersécurité, analyse de vulnérabilités et techniques de piratage éthique.",
    'Technical Information Security': "Analyses approfondies et discussions d'experts sur la sécurité informatique, la cryptographie et la défense système.",
    'r/gaming': "Forums et fil d'actualité de la communauté Reddit autour des jeux vidéo, sorties majeures et tendances de l'industrie."
}

async def fetch_meta_description(target_url: str) -> str:
    if not target_url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                match = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
                if not match:
                    match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:og:)?description["\']', resp.text, re.IGNORECASE)
                if match:
                    clean = re.sub(r'\s+', ' ', match.group(1)).strip()
                    if len(clean) > 20:
                        return clean[:280]
    except Exception as e:
        pass
    return ""

async def generate_llm_description(title: str, category: str, articles: list, api_key: str) -> str:
    if not api_key or not articles:
        return ""
    context = "\n".join([f"- {a['title']} : {a['summary']}" for a in articles[:5]])
    prompt = f"Voici les 5 récents articles du média '{title}' (catégorie {category}) :\n{context}\n\nRédige une présentation en 1 ou 2 phrases précises et captivantes de ce média (sans utiliser les mots 'ce flux' ou 'cet article')."
    
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            res = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                json={
                    "model": "mistral-small-latest",
                    "messages": [{"role": "user", "content": prompt}]
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if res.status_code == 200:
                out = res.json()["choices"][0]["message"]["content"].strip()
                return out.replace('\n', ' ')
    except Exception as e:
        pass
    return ""

async def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url, site_url, category, description, enriched_description FROM catalog_feeds")
    rows = cursor.fetchall()

    print(f"Demarrage du nettoyage et de la generation de descriptions riches pour {len(rows)} flux...")
    
    updated_count = 0
    api_key = settings.mistral_api_key or ""

    for idx, r in enumerate(rows, 1):
        fid, title, url, site_url, category, desc, enriched = r
        
        # Check if curated
        curated_match = None
        for k, v in CURATED_DESCRIPTIONS.items():
            if k.lower() in title.lower():
                curated_match = v
                break

        current = (enriched or desc or "").strip()
        is_generic = "Publication spécialisée" in current or "Source d'information éditée par" in current or len(current) < 25

        if curated_match:
            new_desc = curated_match
        elif is_generic:
            # Try Step 1: Meta description
            target_url = site_url or url
            meta_desc = await fetch_meta_description(target_url)
            
            # Try Step 2: Parse RSS feed entries
            parsed_entries = []
            feed_chan_desc = ""
            try:
                parsed = feedparser.parse(url)
                if parsed and parsed.feed.get('description'):
                    raw_chan = re.sub(r'<[^>]+>', '', parsed.feed.get('description', '')).strip()
                    if len(raw_chan) > 20 and 'Publication spécialisée' not in raw_chan:
                        feed_chan_desc = raw_chan[:260]
                
                if parsed and parsed.entries:
                    for entry in parsed.entries[:5]:
                        t = entry.get('title', '')
                        s = entry.get('summary', entry.get('description', ''))
                        s_clean = re.sub(r'<[^>]+>', '', s)[:120]
                        if t:
                            parsed_entries.append({"title": t, "summary": s_clean})
            except Exception:
                pass

            # Try LLM synthesis
            llm_desc = await generate_llm_description(title, category, parsed_entries, api_key) if api_key else ""

            if llm_desc:
                new_desc = llm_desc
            elif meta_desc:
                new_desc = meta_desc
            elif feed_chan_desc:
                new_desc = feed_chan_desc
            elif parsed_entries:
                first_topic = parsed_entries[0]['title']
                new_desc = f"Média d'actualité {category} couvrant des thématiques d'actualité comme {first_topic}."
            else:
                new_desc = f"Fil d'actualité et de veille d'information couvrant les sujets majeurs en {category}."
        else:
            new_desc = current

        cursor.execute("UPDATE catalog_feeds SET description = ?, enriched_description = ? WHERE id = ?", (new_desc, new_desc, fid))
        updated_count += 1
        print(f"[{idx}/{len(rows)}] {title} -> {new_desc[:70]}...")

    conn.commit()
    conn.close()
    print(f"Termine ! {updated_count} flux mis a jour avec des descriptions uniques et riches.")

if __name__ == "__main__":
    asyncio.run(main())
