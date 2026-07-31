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

async def generate_mistral_embedding(text: str, api_key: str, model: str = "mistral-embed") -> list[float]:
    """
    Calls Mistral AI Embeddings API and returns a vector.
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
                "model": model,
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

async def generate_gemini_embedding(text: str, api_key: str, model: str = "text-embedding-004", output_dimensionality: int = None) -> list[float]:
    """
    Calls Google Gemini API. Returns a vector (default 768-dim).
    Using outputDimensionality parameter if provided (but it can only truncate, not expand beyond 768).
    """
    if not api_key:
        raise ValueError("Clé API Gemini requise pour générer l'embedding.")

    clean_text = text[:2500].strip()
    if not clean_text:
        clean_text = "Article sans contenu"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model}",
        "content": {
            "parts": [{"text": clean_text}]
        }
    }
    if output_dimensionality:
        payload["outputDimensionality"] = output_dimensionality

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30.0
        )

        if response.status_code != 200:
            err_data = response.json()
            raise ValueError(f"Erreur API Gemini Embeddings: {err_data.get('error', {}).get('message', response.text)}")

        res_data = response.json()
        embedding = res_data["embedding"]["values"]
        return embedding

async def vectorize_article(article_id: int, mistral_key: str = "", gemini_key: str = "", provider: str = "mistral", fallback_provider: str = "gemini", mistral_model: str = "mistral-embed", gemini_model: str = "text-embedding-004"):
    """
    Fetches article text, cleans site boilerplate, generates embedding (with primary/fallback logic),
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

    embedding = None
    
    async def try_provider(p_name: str):
        if p_name == "mistral":
            return await generate_mistral_embedding(text_to_embed, mistral_key, model=mistral_model)
        elif p_name == "gemini":
            return await generate_gemini_embedding(text_to_embed, gemini_key, model=gemini_model)
        else:
            raise ValueError("Fournisseur inconnu.")

    provider_used = provider
    try:
        embedding = await try_provider(provider)
    except Exception as e:
        print(f"Erreur embedding {provider} pour article {article_id}: {e}")
        if fallback_provider and fallback_provider != "aucun":
            print(f"Fallback activé : tentative avec {fallback_provider}...")
            provider_used = fallback_provider
            embedding = await try_provider(fallback_provider)
        else:
            raise e
    embedding_json = json.dumps(embedding)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO article_embeddings (article_id, provider, embedding_json) VALUES (?, ?, ?)",
        (article_id, provider_used, embedding_json)
    )

    if HAS_SQLITE_VEC:
        try:
            serialized = sqlite_vec.serialize_float_vector(embedding)
            if provider_used == "mistral":
                cursor.execute(
                    "INSERT OR REPLACE INTO vec_articles_mistral (article_id, embedding) VALUES (?, ?)",
                    (article_id, serialized)
                )
            elif provider_used == "gemini":
                cursor.execute(
                    "INSERT OR REPLACE INTO vec_articles_gemini (article_id, embedding) VALUES (?, ?)",
                    (article_id, serialized)
                )
        except Exception as e:
            print(f"[sqlite-vec note] Insertion dans vec_articles: {e}")

    conn.commit()
    conn.close()
    return {"article_id": article_id, "vector_dim": len(embedding)}

async def vectorize_all_pending(mistral_key: str = "", gemini_key: str = "", provider: str = "mistral", fallback_provider: str = "gemini", mistral_model: str = "mistral-embed", gemini_model: str = "text-embedding-004", force_revectorize: bool = False):
    """
    Vectorizes articles. If force_revectorize is True, clears existing embeddings
    and re-computes vectors for all articles with clean text.
    Uses asyncio concurrency (Semaphore = 10) to process hundreds of articles in seconds.
    """
    import asyncio

    conn = get_db_connection()
    cursor = conn.cursor()

    if force_revectorize:
        cursor.execute(f"DELETE FROM article_embeddings WHERE provider = '{provider}'")
        if HAS_SQLITE_VEC:
            try:
                if provider == "mistral":
                    cursor.execute("DELETE FROM vec_articles_mistral")
                elif provider == "gemini":
                    cursor.execute("DELETE FROM vec_articles_gemini")
            except Exception:
                pass
        conn.commit()

    cursor.execute("""
        SELECT a.id, a.title 
        FROM articles a 
        LEFT JOIN article_embeddings e ON a.id = e.article_id AND e.provider = ?
        WHERE e.article_id IS NULL
    """, (provider,))
    pending_articles = cursor.fetchall()
    conn.close()

    if not pending_articles:
        return {"processed_count": 0, "articles": [], "errors": []}

    results = []
    errors = []

    for art in pending_articles:
        try:
            res = await vectorize_article(art["id"], mistral_key, gemini_key, provider, fallback_provider, mistral_model, gemini_model)
            results.append(res)
            # Respect Mistral rate limit quota (1.00 req/sec max)
            await asyncio.sleep(1.05)
        except Exception as e:
            err_msg = str(e)
            print(f"Erreur vectorisation article {art['id']}: {err_msg}")
            errors.append(err_msg)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                # Pause longer if rate limited
                await asyncio.sleep(3.0)

    return {
        "processed_count": len(results),
        "articles": results,
        "errors": errors
    }
