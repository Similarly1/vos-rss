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

def compute_article_clusters(similarity_threshold: float = 0.86, max_time_diff_hours: float = None):
    """
    Reads all embeddings from DB, computes pairwise cosine similarities across all languages (FR, EN, DE, ES),
    and groups articles into clusters of related news with Centroid Matching & strict temporal proximity.
    
    Proximity & Centroid Rules:
    - Event Mode (similarity_threshold >= 0.84): max time gap = 48h (2 days). Uses Centroid Vector.
    - Thematic Mode (similarity_threshold < 0.84): max time gap = 72h (3 days).
    - Applies a temporal decay factor so closer articles match with higher confidence.
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
            pub_dt = parse_article_date(row["published_date"])
            articles.append({
                "id": row["article_id"],
                "title": row["title"],
                "content": row["content"],
                "url": row["url"],
                "feed_title": row["feed_title"],
                "category": row["category"],
                "published_date": row["published_date"],
                "published_dt": pub_dt,
                "image_url": row["image_url"],
                "language": row["language"] or "fr",
                "is_full_text": bool(row["is_full_text"]),
                "vector": vector
            })
        except Exception:
            pass

    clusters = []
    visited = set()
    is_strict_mode = similarity_threshold >= 0.84

    # Determine maximum time gap between articles in the same cluster
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

        for j in range(i + 1, len(articles)):
            art_j = articles[j]
            if art_j["id"] in visited:
                continue

            # Check temporal gap between art_j and art_i
            time_diff_hours = abs((art_i["published_dt"] - art_j["published_dt"]).total_seconds()) / 3600.0
            if time_diff_hours > max_allowed_hours:
                continue

            # Temporal decay penalty (mild reduction for articles further apart within window)
            decay_factor = max(0.85, 1.0 - (time_diff_hours / max_allowed_hours) * 0.15)

            # Centroid Vector Similarity
            centroid = compute_centroid([item["vector"] for item in cluster_items])
            sim = cosine_similarity(art_j["vector"], centroid) * decay_factor

            if sim >= similarity_threshold:
                cluster_items.append(art_j)
                visited.add(art_j["id"])

        distinct_feeds = list(set(a["feed_title"] for a in cluster_items))

        # Prioritize a French article title if present in the cluster
        french_arts = [a for a in cluster_items if a.get("language", "fr").lower() == "fr"]
        if french_arts:
            main_topic = french_arts[0]["title"]
        else:
            main_topic = cluster_items[0]["title"]

        most_recent_date = max(a["published_date"] for a in cluster_items)

        clusters.append({
            "cluster_id": f"cluster_{art_i['id']}",
            "topic_title": main_topic,
            "category": cluster_items[0].get("category") or "Général",
            "article_count": len(cluster_items),
            "distinct_feed_count": len(distinct_feeds),
            "distinct_feeds": distinct_feeds,
            "latest_published_date": most_recent_date,
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

    # Sort clusters: multi-source events first, then by latest publication date
    clusters.sort(key=lambda c: (c["distinct_feed_count"] > 1, c["latest_published_date"], c["distinct_feed_count"], c["article_count"]), reverse=True)
    return clusters

async def synthesize_cluster(cluster_articles: list[dict], api_key: str, model: str = "mistral-small-latest"):
    """
    Uses Mistral AI to create a unified cross-referenced news summary from multiple articles in different languages.
    Always generates both the title and summary strictly in French.
    """
    from app.api.routes_feeds import get_vps_api_key
    key = get_vps_api_key(api_key)
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
      "synthesis_title": "Titre synthétique, captivant et 100% en français résumant l'événement",
      "summary": "Résumé journalistique structuré et captivant de l'événement en français...",
      "key_takeaways": [
        "Point clé 1...",
        "Point clé 2...",
        "Point clé 3..."
      ]
    }}
    Réponds uniquement au format JSON valide.
    """

    async with httpx.AsyncClient() as client:
        res = await client.post(
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
            timeout=30.0
        )

        if res.status_code != 200:
            raise ValueError(f"Erreur de génération Mistral: {res.text}")

        data = res.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(data)
        except Exception:
            return {
                "synthesis_title": cluster_articles[0].get("title"),
                "summary": data,
                "key_takeaways": []
            }

async def precompute_and_cache_clusters(api_key: str = None):
    """
    Background job to pre-compute clusters for strict event mode (0.86) and thematic mode (0.78),
    and pre-synthesize top event clusters with Mistral AI so they load instantly (0ms) in Perplexity feed.
    """
    from app.api.routes_feeds import get_vps_api_key
    key = get_vps_api_key(api_key)

    # 1. Event Mode (0.86 with Centroid Matching & 48h Window)
    event_clusters = compute_article_clusters(similarity_threshold=0.86, max_time_diff_hours=48.0)

    # Pre-synthesize top 8 event clusters if API key available
    if key and event_clusters:
        for c in event_clusters[:8]:
            try:
                synth = await synthesize_cluster(c["articles"], api_key=key)
                c["precomputed_synthesis"] = synth
            except Exception as e:
                print(f"[Pre-synthesis note for {c['cluster_id']}]: {e}")

    save_clusters_to_cache("threshold_events", event_clusters)
    save_clusters_to_cache("threshold_0.91", event_clusters)
    save_clusters_to_cache("threshold_0.86", event_clusters)

    # 2. Digest Mode (0.78)
    digest_clusters = compute_article_clusters(similarity_threshold=0.78, max_time_diff_hours=72.0)
    save_clusters_to_cache("threshold_themes", digest_clusters)
    save_clusters_to_cache("threshold_0.78", digest_clusters)

    return {
        "event_clusters_count": len(event_clusters),
        "digest_clusters_count": len(digest_clusters)
    }
