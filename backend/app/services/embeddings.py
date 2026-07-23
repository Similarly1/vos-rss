import httpx
import json
import re
import sqlite3
from app.database import get_db_connection, HAS_SQLITE_VEC

try:
    import sqlite_vec
except ImportError:
    pass

def clean_text_for_embedding(title: str, content: str) -> str:
    """
    Strips RSS channel prefixes, HTML tags, and site-wide boilerplate 
    to make embeddings highly discriminative for clustering.
    """
    clean_title = title or ""
    
    # Remove common site/channel prefixes that pollute embedding vectors
    prefixes = [
        r"^Suisse\s*-\s*Radio\s*Télévision\s*Suisse\s*",
        r"^International\s*:\s*Toute\s*l'actualité\s*sur\s*Le\s*Monde\.fr\s*",
        r"^Le\s*Temps\s*:\s*Suisse\s*",
        r"^Le\s*Temps\s*:\s*",
        r"^Le\s*Monde\s*:\s*",
        r"^Hacker\s*News\s*:\s*"
    ]
    for p in prefixes:
        clean_title = re.sub(p, "", clean_title, flags=re.IGNORECASE).strip()

    # Strip HTML tags
    clean_content = re.sub(r'<[^>]+>', ' ', content or '')
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    # Take first 250 words of clean content to focus on key facts
    words = clean_content.split()[:250]
    snippet = " ".join(words)

    return f"Titre: {clean_title}\nContenu: {snippet}"

async def generate_mistral_embedding(text: str, api_key: str) -> list[float]:
    """
    Calls Mistral AI Embeddings API (model: mistral-embed) and returns a 1024-dim vector.
    """
    if not api_key:
        raise ValueError("Clé API Mistral requise pour générer l'embedding.")

    clean_text = text[:2500].strip()
    if not clean_text:
        clean_text = "Article sans contenu"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mistral.ai/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-embed",
                "input": [clean_text]
            },
            timeout=30.0
        )

        if response.status_code != 200:
            err_data = response.json()
            raise ValueError(f"Erreur API Mistral Embeddings: {err_data.get('message', response.text)}")

        res_data = response.json()
        embedding = res_data["data"][0]["embedding"]
        return embedding

async def vectorize_article(article_id: int, api_key: str):
    """
    Fetches article text, cleans site boilerplate, generates embedding with Mistral AI,
    and stores it in article_embeddings.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT title, content FROM articles WHERE id = ?", (article_id,))
    article = cursor.fetchone()
    if not article:
        conn.close()
        raise ValueError(f"Article {article_id} introuvable.")

    text_to_embed = clean_text_for_embedding(article['title'], article['content'])
    conn.close()

    embedding = await generate_mistral_embedding(text_to_embed, api_key)
    embedding_json = json.dumps(embedding)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO article_embeddings (article_id, embedding_json) VALUES (?, ?)",
        (article_id, embedding_json)
    )

    if HAS_SQLITE_VEC:
        try:
            serialized = sqlite_vec.serialize_float_vector(embedding)
            cursor.execute(
                "INSERT OR REPLACE INTO vec_articles (article_id, embedding) VALUES (?, ?)",
                (article_id, serialized)
            )
        except Exception as e:
            print(f"[sqlite-vec note] Insertion dans vec_articles: {e}")

    conn.commit()
    conn.close()
    return {"article_id": article_id, "vector_dim": len(embedding)}

async def vectorize_all_pending(api_key: str, force_revectorize: bool = False):
    """
    Vectorizes articles. If force_revectorize is True, clears existing embeddings
    and re-computes vectors for all articles with clean text.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if force_revectorize:
        cursor.execute("DELETE FROM article_embeddings")
        if HAS_SQLITE_VEC:
            try:
                cursor.execute("DELETE FROM vec_articles")
            except Exception:
                pass
        conn.commit()

    cursor.execute("""
        SELECT a.id, a.title 
        FROM articles a 
        LEFT JOIN article_embeddings e ON a.id = e.article_id 
        WHERE e.article_id IS NULL
    """)
    pending_articles = cursor.fetchall()
    conn.close()

    results = []
    errors = []

    for art in pending_articles:
        try:
            res = await vectorize_article(art["id"], api_key)
            results.append(res)
        except Exception as e:
            print(f"Erreur vectorisation article {art['id']}: {e}")
            errors.append(str(e))

    if errors and len(results) == 0:
        raise ValueError(f"Échec de la vectorisation: {errors[0]}")

    return {
        "processed_count": len(results),
        "articles": results,
        "errors": errors
    }
