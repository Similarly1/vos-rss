import json
import math
import httpx
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
            return json.loads(row["clusters_json"])
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

def compute_article_clusters(similarity_threshold: float = 0.91):
    """
    Reads all embeddings from DB, computes pairwise cosine similarities across all languages (FR, EN, DE, ES),
    and groups articles into clusters of related news.
    Always prioritizes a French article title as topic_title when available.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.article_id, e.embedding_json, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, f.title as feed_title, f.category
        FROM article_embeddings e
        JOIN articles a ON e.article_id = a.id
        JOIN feeds f ON a.feed_id = f.id
        ORDER BY a.published_date DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    articles = []
    for row in rows:
        try:
            vector = json.loads(row["embedding_json"])
            articles.append({
                "id": row["article_id"],
                "title": row["title"],
                "content": row["content"],
                "url": row["url"],
                "feed_title": row["feed_title"],
                "category": row["category"],
                "published_date": row["published_date"],
                "image_url": row["image_url"],
                "language": row["language"] or "fr",
                "is_full_text": bool(row["is_full_text"]),
                "vector": vector
            })
        except Exception:
            pass

    clusters = []
    visited = set()
    is_strict_mode = similarity_threshold >= 0.86

    for i in range(len(articles)):
        art_i = articles[i]
        if art_i["id"] in visited:
            continue

        cluster_items = [art_i]
        visited.add(art_i["id"])

        for j in range(i + 1, len(articles)):
            art_j = articles[j]
            if art_j["id"] in visited:
                continue

            sims = [cosine_similarity(art_j["vector"], item["vector"]) for item in cluster_items]

            if is_strict_mode:
                is_match = min(sims) >= similarity_threshold
            else:
                is_match = (sum(sims) / len(sims)) >= similarity_threshold

            if is_match:
                cluster_items.append(art_j)
                visited.add(art_j["id"])

        distinct_feeds = list(set(a["feed_title"] for a in cluster_items))

        # Prioritize a French article title if present in the cluster
        french_arts = [a for a in cluster_items if a.get("language", "fr").lower() == "fr"]
        if french_arts:
            main_topic = french_arts[0]["title"]
        else:
            main_topic = cluster_items[0]["title"]

        clusters.append({
            "cluster_id": f"cluster_{art_i['id']}",
            "topic_title": main_topic,
            "category": cluster_items[0].get("category") or "Général",
            "article_count": len(cluster_items),
            "distinct_feed_count": len(distinct_feeds),
            "distinct_feeds": distinct_feeds,
            "articles": [{
                "id": a["id"],
                "title": a["title"],
                "content": a["content"],
                "feed_title": a["feed_title"],
                "url": a["url"],
                "published_date": a["published_date"],
                "image_url": a["image_url"],
                "language": a["language"],
                "is_full_text": a["is_full_text"]
            } for a in cluster_items]
        })

    # Sort clusters: prioritize clusters with higher distinct feed count
    clusters.sort(key=lambda c: (c["distinct_feed_count"] > 1, c["distinct_feed_count"], c["article_count"]), reverse=True)
    return clusters

async def synthesize_cluster(cluster_articles: list[dict], api_key: str, model: str = "mistral-small-latest"):
    """
    Uses Mistral AI to create a unified cross-referenced news summary from multiple articles in different languages.
    Always generates both the title and summary strictly in French.
    """
    key = api_key or settings.mistral_api_key
    if not key:
        raise ValueError("Clé API Mistral requise.")

    articles_text = "\n\n".join([
        f"--- Source : {a.get('feed_title', 'RSS')} (Langue d'origine: {a.get('language', 'fr').upper()}) ---\nTitre d'origine: {a.get('title')}\nContenu complet: {(a.get('content') or '')[:2500]}"
        for a in cluster_articles
    ])

    system_prompt = (
        "Tu es un journaliste et analyste d'actualités internationales pour l'application 'Vos'. "
        "Ton objectif est de croiser les informations issues de médias rédigés en différentes langues "
        "qui traitent du MÊME sujet ou événement précis pour rédiger une synthèse globale unifiée, neutre, captivante, complète et sans doublons. "
        "CONSIGNE CAPITALE : Rédige IMPÉRATIVEMENT le titre (synthesis_title) ET la synthèse (summary) STRICTEMENT EN FRANÇAIS."
    )

    user_prompt = f"""
    Voici les articles recensés sur ce sujet en plusieurs langues :
    {articles_text}

    Rédige une synthèse croisée précise au format JSON suivant :
    {{
      "synthesis_title": "Titre d'actualité captivant et précis rédigé EN FRANÇAIS",
      "summary": "Résumé croisé fluide en 2 à 3 paragraphes rédigé EN FRANÇAIS combinant les faits de toutes les sources.",
      "key_takeaways": ["Point fort 1 en français", "Point fort 2 en français", "Point fort 3 en français"],
      "sources_count": {len(cluster_articles)}
    }}
    Réponds uniquement au format JSON valide.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=35.0
        )

        if response.status_code != 200:
            raise ValueError(f"Erreur API Mistral: {response.text}")

        res_data = response.json()
        ai_content = res_data["choices"][0]["message"]["content"]
        return json.loads(ai_content)

async def precompute_and_cache_clusters(api_key: str = None):
    """
    Background worker function that pre-calculates clusters for both modes ('events' 0.91 & 'themes' 0.78),
    pre-generates French Mistral AI syntheses, and writes results to SQLite cluster_cache.
    This guarantees 0ms instant loading when the user opens Discover / Fil Perplexity!
    """
    key = api_key or settings.mistral_api_key
    results = {}

    for mode_key, thresh in [("events", 0.91), ("themes", 0.78)]:
        clusters = compute_article_clusters(similarity_threshold=thresh)

        # Pre-synthesize top clusters with Mistral AI if key is available
        if key and clusters:
            for cluster in clusters[:6]:
                try:
                    synth = await synthesize_cluster(cluster["articles"], api_key=key)
                    if synth and "synthesis_title" in synth:
                        cluster["precomputed_synthesis"] = synth
                        cluster["topic_title"] = synth["synthesis_title"]
                except Exception as e:
                    print(f"[Pre-synthesis note for cluster {cluster['cluster_id']}]: {e}")

        save_clusters_to_cache(f"threshold_{mode_key}", clusters)
        save_clusters_to_cache(f"threshold_{thresh}", clusters)
        results[mode_key] = len(clusters)

    return results
