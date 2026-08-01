import json
import math
import re
import html
import httpx
import asyncio
from datetime import datetime
from app.database import get_db_connection
from app.config import settings

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Computes cosine similarity between two float vectors.
    """
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

def compute_centroid(vectors: list[list[float]]) -> list[float]:
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for vec in vectors:
        for k in range(dim):
            centroid[k] += vec[k]
    count = float(len(vectors))
    return [val / count for val in centroid]

def parse_article_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now()
    try:
        return datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return datetime.now()

def get_cached_clusters(threshold_key: str) -> list:
    """
    Retrieves pre-computed clusters from SQLite cluster_cache.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clusters_json FROM cluster_cache WHERE threshold_key = ?", (threshold_key,))
    row = cursor.fetchone()
    conn.close()

    if row and row["clusters_json"]:
        try:
            res = json.loads(row["clusters_json"])
            if isinstance(res, list) and len(res) > 0:
                return res
        except Exception:
            pass
    return None

def save_clusters_to_cache(threshold_key: str, clusters: list):
    """
    Saves pre-computed clusters to SQLite cluster_cache.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    clusters_json = json.dumps(clusters)
    cursor.execute(
        "INSERT OR REPLACE INTO cluster_cache (threshold_key, clusters_json, updated_at) VALUES (?, ?, ?)",
        (threshold_key, clusters_json, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()

def update_cached_cluster_synthesis(articles: list, synthesis: dict):
    """
    Persists newly generated synthesis into existing cached clusters in SQLite cluster_cache.
    """
    if not articles or not synthesis or synthesis.get("is_fallback") or synthesis.get("status") == "pending":
        return
    first_url = articles[0].get("url")
    if not first_url:
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT threshold_key, clusters_json FROM cluster_cache")
        rows = cursor.fetchall()
        
        for row in rows:
            t_key = row["threshold_key"]
            if not row["clusters_json"]:
                continue
            try:
                clusters = json.loads(row["clusters_json"])
                updated = False
                for c in clusters:
                    c_urls = [a.get("url") for a in c.get("articles", []) if a.get("url")]
                    if first_url in c_urls:
                        c["precomputed_synthesis"] = synthesis
                        updated = True
                        break
                if updated:
                    cursor.execute(
                        "UPDATE cluster_cache SET clusters_json = ?, updated_at = ? WHERE threshold_key = ?",
                        (json.dumps(clusters), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), t_key)
                    )
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur update_cached_cluster_synthesis: {e}")

def compute_article_clusters(similarity_threshold: float = 0.85, max_time_diff_hours: float = None, exclude_culture: bool = False) -> list[dict]:
    """
    Reads all embeddings from DB, computes pairwise cosine similarities across all languages (FR, EN, DE, ES),
    and groups articles into clusters of related news with Centroid Matching & strict temporal proximity.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        where_clause = "WHERE 1=1"
        if exclude_culture:
            where_clause += " AND (f.category IS NULL OR f.category != 'Étagère Culture')"

        cursor.execute(f"""
            SELECT e.article_id, e.embedding_json, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, f.title as feed_title, f.url as feed_url, f.category
            FROM article_embeddings e
            JOIN articles a ON e.article_id = a.id
            LEFT JOIN feeds f ON a.feed_id = f.id
            {where_clause}
            ORDER BY a.published_date DESC
            LIMIT 350
        """)
        rows = cursor.fetchall()
        conn.close()

        articles = []
        if rows:
            for row in rows:
                try:
                    raw_emb = row["embedding_json"]
                    if isinstance(raw_emb, bytes):
                        raw_emb = raw_emb.decode('utf-8')
                    vector = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
                    if not isinstance(vector, list) or len(vector) == 0:
                        continue
                    pub_dt = parse_article_date(row["published_date"])
                    articles.append({
                        "id": row["article_id"],
                        "title": row["title"] or "",
                        "content": row["content"] or "",
                        "url": row["url"] or "",
                        "feed_title": row["feed_title"] or "RSS",
                        "feed_url": row["feed_url"] or "",
                        "category": row["category"] or "Général",
                        "published_date": row["published_date"],
                        "published_dt": pub_dt,
                        "image_url": row["image_url"],
                        "language": row["language"] or "fr",
                        "is_full_text": bool(row["is_full_text"]),
                        "vector": vector
                    })
                except Exception:
                    pass

        if not articles:
            # Fallback: fetch recent raw articles as basic clusters
            conn = get_db_connection()
            cursor = conn.cursor()
            raw_where = "WHERE (f.category IS NULL OR f.category != 'Étagère Culture')" if exclude_culture else ""
            cursor.execute(f"""
                SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, f.title as feed_title, f.url as feed_url, f.category
                FROM articles a
                LEFT JOIN feeds f ON a.feed_id = f.id
                {raw_where}
                ORDER BY a.id DESC
                LIMIT 100
            """)
            raw_rows = cursor.fetchall()
            conn.close()

            fallback_clusters = []
            for r in raw_rows:
                pub_date = r["published_date"] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                fallback_clusters.append({
                    "cluster_id": f"cluster_raw_{r['id']}",
                    "topic_title": r["title"] or "Événement d'actualité",
                    "category": r["category"] or "Général",
                    "article_count": 1,
                    "distinct_feed_count": 1,
                    "distinct_feeds": [r["feed_title"] or "RSS"],
                    "latest_published_date": pub_date,
                    "articles": [{
                        "id": r["id"],
                        "title": r["title"] or "",
                        "content": r["content"] or "",
                        "feed_title": r["feed_title"] or "RSS",
                        "feed_url": r["feed_url"] or "",
                        "url": r["url"] or "",
                        "published_date": pub_date,
                        "image_url": r["image_url"],
                        "language": r["language"] or "fr",
                        "is_full_text": bool(r["is_full_text"])
                    }]
                })
            return fallback_clusters

        clusters = []
        visited = set()
        is_strict_mode = similarity_threshold >= 0.84

        if max_time_diff_hours is None:
            max_allowed_hours = 48.0 if is_strict_mode else 72.0
        else:
            max_allowed_hours = float(max_time_diff_hours)

        for i in range(len(articles)):
            art_i = articles[i]
            if art_i["id"] in visited:
                continue

            cluster_items = [art_i]
            visited.add(art_i["id"])
            current_centroid = art_i["vector"]

            for j in range(i + 1, len(articles)):
                art_j = articles[j]
                if art_j["id"] in visited:
                    continue

                time_diff_hours = abs((art_i["published_dt"] - art_j["published_dt"]).total_seconds()) / 3600.0
                if time_diff_hours > max_allowed_hours:
                    continue

                decay_factor = max(0.85, 1.0 - (0.15 * (time_diff_hours / max_allowed_hours)))

                sim_seed = cosine_similarity(art_j["vector"], art_i["vector"]) * decay_factor
                sim_centroid = cosine_similarity(art_j["vector"], current_centroid) * decay_factor

                if sim_seed >= similarity_threshold and sim_centroid >= similarity_threshold:
                    cluster_items.append(art_j)
                    visited.add(art_j["id"])
                    current_centroid = compute_centroid([item["vector"] for item in cluster_items])

                if len(cluster_items) >= 20:
                    break

            distinct_feeds = list(set(a["feed_title"] for a in cluster_items if a.get("feed_title")))
            if not distinct_feeds:
                distinct_feeds = ["RSS"]

            french_arts = [a for a in cluster_items if (a.get("language") or "fr").lower() == "fr"]
            if french_arts and french_arts[0].get("title"):
                main_topic = french_arts[0]["title"]
            else:
                main_topic = cluster_items[0].get("title") or "Événement d'actualité"

            valid_dates = [a["published_date"] for a in cluster_items if a.get("published_date")]
            most_recent_date = max(valid_dates) if valid_dates else datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cluster_image_url = None
            for a in cluster_items:
                if a.get("image_url"):
                    cluster_image_url = a["image_url"]
                    break

            clusters.append({
                "cluster_id": f"cluster_{art_i['id']}",
                "topic_title": main_topic,
                "category": cluster_items[0].get("category") or "Général",
                "image_url": cluster_image_url,
                "article_count": len(cluster_items),
                "distinct_feed_count": len(distinct_feeds),
                "distinct_feeds": distinct_feeds,
                "latest_published_date": most_recent_date,
                "articles": [{
                    "id": a["id"],
                    "title": a.get("title") or "",
                    "content": a.get("content") or "",
                    "feed_title": a.get("feed_title") or "RSS",
                    "feed_url": a.get("feed_url") or "",
                    "url": a.get("url") or "",
                    "published_date": a.get("published_date") or most_recent_date,
                    "image_url": a.get("image_url"),
                    "language": a.get("language") or "fr",
                    "is_full_text": bool(a.get("is_full_text"))
                } for a in cluster_items]
            })

        clusters.sort(key=lambda c: (c.get("distinct_feed_count", 1) > 1, c.get("latest_published_date") or "", c.get("distinct_feed_count", 1), c.get("article_count", 1)), reverse=True)
        return clusters

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erreur compute_article_clusters: {e}")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, f.title as feed_title, f.url as feed_url, f.category
                FROM articles a
                LEFT JOIN feeds f ON a.feed_id = f.id
                ORDER BY a.id DESC
                LIMIT 60
            """)
            raw_rows = cursor.fetchall()
            conn.close()
            fallback_clusters = []
            for r in raw_rows:
                pub_date = r["published_date"] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                fallback_clusters.append({
                    "cluster_id": f"cluster_raw_{r['id']}",
                    "topic_title": r["title"] or "Événement d'actualité",
                    "category": r["category"] or "Général",
                    "article_count": 1,
                    "distinct_feed_count": 1,
                    "distinct_feeds": [r["feed_title"] or "RSS"],
                    "latest_published_date": pub_date,
                    "articles": [{
                        "id": r["id"],
                        "title": r["title"] or "",
                        "content": r["content"] or "",
                        "feed_title": r["feed_title"] or "RSS",
                        "feed_url": r["feed_url"] or "",
                        "url": r["url"] or "",
                        "published_date": pub_date,
                        "image_url": r["image_url"],
                        "language": r["language"] or "fr",
                        "is_full_text": bool(r["is_full_text"])
                    }]
                })
            return fallback_clusters
        except Exception as e2:
            print(f"Erreur fallback compute_article_clusters: {e2}")
            return []

def clean_html_tags(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = str(raw_html)
    # Decode HTML entities first so &apos;, &rsquo;, &#39; are restored to real apostrophes before stripping
    text = html.unescape(text)
    text = text.replace("&apos;", "'").replace("&rsquo;", "'").replace("&#39;", "'").replace("’", "'")
    # Strip script, style, svg, header, nav, footer tags
    text = re.sub(r'<(script|style|header|nav|footer|form|svg|img|code)[^>]*>[\s\S]*?<\/\1>', ' ', text, flags=re.IGNORECASE)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Strip Javascript/Swiper/UI boilerplate leakage
    text = re.sub(r'(?:publish\s*[\'"][^\'"]+[\'"]|data-sara-[a-zA-Z-]+|swiper\.[a-zA-Z.]+|x-swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup\.escape|window\.dispatchEvent|POLYGON\s+DOM|HEADER\s+READY|EILMELDUNG\s+proto|headline|Zur\s+Merkliste|Teilen\s+X\.com|Facebook\s+E-Mail|Link\s+kopieren|Bild\s+vergrößern|Digital-Abo)[^\n.!?]*', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:publish|data-sara-[a-zA-Z-]+|swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup|dispatchEvent|POLYGON|DOM|HEADER|READY|EILMELDUNG|proto|headline|Merkliste|Facebook|WhatsApp|Link\s+kopieren|Optionen|Teilen|Abo|Digital-Abo)', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\$[a-zA-Z0-9_.]+\([^)]*\)', ' ', text)
    text = re.sub(r'(?:data-[a-zA-Z0-9_-]+|:[a-zA-Z0-9_-]+|x-[a-zA-Z0-9_-]+|@[a-zA-Z0-9_-]+)=["\'][^"\']*["\']', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9àâáäãåçéèêëìíîïñòóôöõøùúûüýÿÀÂÁÄÃÅÇÉÈÊËÌÍÎÏÑÒÓÔÖÕØÙÚÛÜÝŸæÆœŒ\s.,!?\'"’–-]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

async def synthesize_cluster(cluster_articles: list[dict], mistral_key: str = "", gemini_key: str = "", provider: str = "mistral", fallback_enabled: bool = True, mistral_model: str = None, gemini_model: str = None):
    """
    Uses Mistral AI or Gemini to create a unified cross-referenced news summary from multiple articles in different languages.
    """
    from app.config import settings
    m_key = (mistral_key or settings.mistral_api_key or "").strip()
    g_key = (gemini_key or settings.gemini_api_key or "").strip()

    m_model = mistral_model or settings.mistral_discover_model or settings.mistral_model or "mistral-small-latest"
    if not m_model or "gemini" in m_model.lower() or "medium" in m_model or "tiny" in m_model:
        m_model = "mistral-small-latest"

    g_model = gemini_model or settings.gemini_discover_model or settings.gemini_model or "gemini-1.5-flash"
    if not g_model or "mistral" in g_model.lower():
        g_model = "gemini-1.5-flash"

    articles_text_parts = []
    for a in cluster_articles[:6]:
        raw_text = a.get('content') or a.get('description') or a.get('title') or ''
        clean_text = clean_html_tags(raw_text)[:1500]
        articles_text_parts.append(
            f"--- Source : {a.get('feed_title', 'RSS')} (Langue d'origine: {a.get('language', 'fr').upper()}) ---\n"
            f"Titre: {clean_html_tags(a.get('title') or '')}\n"
            f"Contenu: {clean_text}"
        )

    articles_text = "\n\n".join(articles_text_parts)

    system_prompt = (
        "Tu es un grand journaliste et analyste d'actualités internationales pour l'application francophone 'Vos'. "
        "Ton objectif est de croiser les informations issues de médias rédigés en n'importe quelle langue (anglais, allemand, espagnol, français, etc.) "
        "qui traitent du MÊME sujet ou événement précis pour rédiger une synthèse globale unifiée, neutre, captivante, complète et sans doublons.\n\n"
        "CONSIGNES STRICTES :\n"
        "1. TRADUCTION OBLIGATOIRE EN FRANÇAIS : Tu dois TOUJOURS traduire et rédiger IMPÉRATIVEMENT le titre (synthesis_title), le résumé (summary) ET les points clés (key_takeaways) STRICTEMENT ET 100% EN FRANÇAIS, quelle que soit la langue des articles sources (même s'ils sont en anglais). IL EST STRICTEMENT INTERDIT D'UTILISER UNE AUTRE LANGUE QUE LE FRANÇAIS.\n"
        "2. DÉVELOPPEMENT DU RÉSUMÉ : Le résumé (summary) doit être riche, bien développé et complet (2 à 3 paragraphes détaillés expliquant les faits, les causes et le contexte), et JAMAIS une simple phrase courte.\n"
        "3. TEXTE PUR SANS BALISES HTML : Ne mets aucune balise HTML (pas de <p>, <img>, <div>). Rédige uniquement du texte brut avec des retours à la ligne naturels.\n"
        "4. GÉOLOCALISATION : Si l'événement possède un ancrage géographique très strict et précis (une ville, un pays précis, une région spécifique, par ex: 'Genève', 'Ukraine', 'Tokyo', 'Paris'), fournis `location_name`, `latitude` et `longitude`. Si l'événement est abstrait ou sans ancrage précis, retourne null pour ces 3 champs.\n"
        "5. CATÉGORISATION CINÉMA & SÉRIES : Si le contenu relève de la classification 'Cinéma et séries', restreins cette catégorie STRICTEMENT aux œuvres scénarisées (films, séries fictions). Exclus formellement les sports, les JT, la téléréalité, et les émissions TV classiques."
    )

    user_prompt = f"""
    Voici les articles recensés sur cet événement en différentes langues :

    {articles_text}

    Rédige une synthèse croisée complète entièrement traduite et structurée en français au format JSON suivant :
    {{
      "synthesis_title": "Titre synthétique, captivant et 100% en français résumant l'événement",
      "summary": "Résumé journalistique bien développé (2 à 3 paragraphes complets en français)...",
      "key_takeaways": [
        "Point clé 1 en français...",
        "Point clé 2 en français...",
        "Point clé 3 en français..."
      ],
      "location_name": "Nom du lieu précis (ex: 'Genève') ou null",
      "latitude": 46.2044,
      "longitude": 6.1432
    }}
    Remarque: latitude et longitude doivent être des float (ex: 46.2044) ou null.
    Réponds uniquement au format JSON valide.
    """

    async def call_mistral():
        if not m_key:
            raise ValueError("Clé API Mistral manquante dans la configuration.")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {m_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": m_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 1500
                },
                timeout=55.0
            )
            if res.status_code != 200:
                raise ValueError(f"Erreur API Mistral ({res.status_code}): {res.text}")
            raw_data = res.json()["choices"][0]["message"]["content"]
            cleaned = re.sub(r"^```json\s*", "", raw_data.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            return json.loads(cleaned)

    async def call_gemini():
        if not g_key:
            raise ValueError("Clé API Gemini manquante dans la configuration.")
        
        target_model = g_model if (g_model and "gemini" in g_model.lower()) else "gemini-3.6-flash"
        
        # Test endpoints and multiple models in case of 404 (model restricted/unavailable for this key)
        api_urls = [
            f"https://generativelanguage.googleapis.com/v1/models/{target_model}:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={g_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={g_key}"
        ]
        
        last_err = ""
        async with httpx.AsyncClient() as client:
            for url in api_urls:
                try:
                    res = await client.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json={
                            "system_instruction": {
                                "parts": [{"text": system_prompt}]
                            },
                            "contents": [{
                                "parts": [{"text": user_prompt}]
                            }],
                            "generationConfig": {
                                "responseMimeType": "application/json"
                            }
                        },
                        timeout=55.0
                    )
                    if res.status_code == 200:
                        raw_data = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned = re.sub(r"^```json\s*", "", raw_data.strip(), flags=re.IGNORECASE)
                        cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
                        return json.loads(cleaned)
                    last_err = f"Erreur API Gemini ({res.status_code}): {res.text}"
                except Exception as ex:
                    last_err = str(ex)
            raise ValueError(last_err)

    async def try_provider(p_name: str):
        if p_name == "mistral":
            return await call_mistral()
        elif p_name == "gemini":
            return await call_gemini()
        else:
            raise ValueError(f"Fournisseur IA inconnu ({p_name}).")

    try:
        return await try_provider(provider)
    except Exception as e:
        print(f"Erreur synthèse avec {provider} : {e}")
        if fallback_enabled:
            fallback_provider = "gemini" if provider == "mistral" else "mistral"
            has_fb_key = bool(g_key) if fallback_provider == "gemini" else bool(m_key)
            if has_fb_key:
                print(f"Fallback activé : tentative avec {fallback_provider}...")
                try:
                    return await try_provider(fallback_provider)
                except Exception as e2:
                    print(f"Erreur Fallback {fallback_provider} : {e2}")
        
        main_art = cluster_articles[0] if cluster_articles else {}
        clean_title = clean_html_tags(main_art.get("title") or "Événement d'actualité")
        
        return {
            "synthesis_title": clean_title,
            "summary": "Synthèse IA en cours de préparation...",
            "key_takeaways": [],
            "status": "pending",
            "is_fallback": True
        }

def clear_cluster_cache():
    """
    Clears all cached cluster syntheses from SQLite cluster_cache table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cluster_cache")
    conn.commit()
    conn.close()

async def precompute_and_cache_clusters(mistral_key: str = "", gemini_key: str = "", provider: str = "mistral", fallback_enabled: bool = True):
    """
    Background job to pre-compute clusters for strict event mode (0.86) and thematic mode (0.78),
    and pre-synthesize top event clusters.
    """
    from app.config import settings
    m_key = mistral_key or settings.mistral_api_key
    g_key = gemini_key or settings.gemini_api_key

    clear_cluster_cache()

    # 1. Event Mode (0.86 with Centroid Matching & 48h Window)
    event_clusters = compute_article_clusters(similarity_threshold=0.86, max_time_diff_hours=48.0)

    # Pre-synthesize ALL event clusters in batches if API keys available
    if (m_key or g_key) and event_clusters:
        async def synth_worker(c):
            try:
                synth = await synthesize_cluster(
                    c["articles"], 
                    mistral_key=m_key, 
                    gemini_key=g_key, 
                    provider=provider, 
                    fallback_enabled=fallback_enabled,
                    mistral_model=settings.mistral_discover_model,
                    gemini_model=settings.gemini_discover_model
                )
                if synth and not synth.get("is_fallback") and synth.get("status") != "pending" and len(synth.get("summary", "")) >= 120 and "Synthèse IA en cours" not in synth.get("summary", ""):
                    c["precomputed_synthesis"] = synth
            except Exception as e:
                print(f"[Pre-synthesis note for {c['cluster_id']}]: {e}")

        batch_size = 5
        for b in range(0, len(event_clusters), batch_size):
            batch = event_clusters[b:b+batch_size]
            await asyncio.gather(*(synth_worker(c) for c in batch))

    save_clusters_to_cache("threshold_events", event_clusters)
    save_clusters_to_cache("threshold_0.91", event_clusters)
    save_clusters_to_cache("threshold_0.86", event_clusters)
    save_clusters_to_cache("threshold_0.85", event_clusters)

    # 2. Digest Mode (0.78)
    digest_clusters = compute_article_clusters(similarity_threshold=0.78, max_time_diff_hours=72.0)
    save_clusters_to_cache("threshold_themes", digest_clusters)
    save_clusters_to_cache("threshold_0.78", digest_clusters)

    return {
        "event_clusters_count": len(event_clusters),
        "digest_clusters_count": len(digest_clusters)
    }
