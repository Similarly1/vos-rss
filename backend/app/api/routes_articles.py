from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
import httpx

from app.database import get_db_connection
from app.config import settings

router = APIRouter(prefix="/api/articles", tags=["Articles"])

class SummarizeRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None

@router.get("")
@router.get("/")
def get_articles(
    lang: Optional[str] = Query(None, description="Language filter (fr, en, de, es, all)"),
    full_text_only: Optional[bool] = Query(False, description="Show only full text articles"),
    hide_paywalled: Optional[bool] = Query(False, description="Hide paywalled articles")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, 
               COALESCE(a.is_paywalled, 0) as is_paywalled, COALESCE(a.is_full_text_available, 1) as is_full_text_available, 
               f.title as feed_title, f.category
        FROM articles a
        JOIN feeds f ON a.feed_id = f.id
        WHERE 1=1
    """
    params = []

    if lang and lang.lower() != "all":
        query += " AND (a.language = ? OR f.language = ?)"
        params.extend([lang.lower(), lang.lower()])

    if full_text_only:
        query += " AND (a.is_full_text = 1 OR f.is_full_text = 1)"

    if hide_paywalled:
        query += " AND (a.is_paywalled = 0 OR a.is_paywalled IS NULL)"

    query += " ORDER BY a.id DESC LIMIT 60"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@router.get("/{article_id}")
def get_article(article_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, a.language, f.title as feed_title
        FROM articles a
        JOIN feeds f ON a.feed_id = f.id
        WHERE a.id = ?
    """, (article_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Article non trouvé")
    return dict(row)

@router.post("/{article_id}/rescrape")
def rescrape_article(article_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url, content FROM articles WHERE id = ?", (article_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Article introuvable.")

    art = dict(row)
    from app.services.rss import extract_full_article_content
    scraped_text, is_pw, is_ft = extract_full_article_content(art["url"], art["content"] or "")
    
    if scraped_text:
        cursor.execute(
            "UPDATE articles SET content = ?, is_paywalled = ?, is_full_text_available = ? WHERE id = ?",
            (scraped_text, 1 if is_pw else 0, 1 if is_ft else 0, article_id)
        )
        conn.commit()

    conn.close()
    return {
        "status": "success",
        "article_id": article_id,
        "content": scraped_text or art["content"],
        "content_length": len(scraped_text or art["content"] or "")
    }

@router.post("/{article_id}/summarize")
async def summarize_article(article_id: int, payload: SummarizeRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, url FROM articles WHERE id = ?", (article_id,))
    article = cursor.fetchone()
    conn.close()

    if not article:
        raise HTTPException(status_code=404, detail="Article introuvable")

    provider = (payload.provider or settings.synthesis_provider or "mistral").lower()
    
    m_key = payload.api_key or (settings.gemini_api_key if provider == "gemini" else settings.mistral_api_key)
    if not m_key and provider != "gemini":
        m_key = settings.mistral_api_key or settings.gemini_api_key
        if settings.gemini_api_key and not settings.mistral_api_key:
            provider = "gemini"
            m_key = settings.gemini_api_key

    if not m_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API requise pour la synthèse. Veuillez la renseigner dans les Paramètres."
        )

    clean_content = article["content"] or article["title"]
    clean_content = clean_content[:4000]

    system_prompt = (
        "Tu es un éditeur et journaliste IA pour l'application de podcast 'Vos'. "
        "Ton rôle est de créer un résumé structuré et clair d'un article d'actualité en français."
    )
    user_prompt = f"""
    Titre de l'article : {article['title']}
    Contenu :
    {clean_content}

    Génère un résumé concis au format JSON suivant :
    {{
      "summary": "Résumé fluide en 2 à 3 phrases",
      "key_points": ["Point clé 1", "Point clé 2", "Point clé 3"],
      "topic": "Sujet principal"
    }}
    Réponds uniquement au format JSON valide.
    """

    try:
        import json
        if provider == "gemini":
            chosen_model = payload.model if payload.model and payload.model != "mistral-small-latest" else (settings.gemini_article_model or settings.gemini_model)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={m_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json"}
                    },
                    timeout=30.0
                )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Erreur Gemini: {response.text}")
            res_data = response.json()
            ai_message = res_data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            chosen_model = payload.model if payload.model and payload.model != "mistral-small-latest" else (settings.mistral_article_model or settings.mistral_model)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {m_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": chosen_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30.0
                )
            if response.status_code != 200:
                err_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                raise HTTPException(status_code=response.status_code, detail=err_data.get("message", f"Erreur Mistral: {response.text}"))
            res_data = response.json()
            ai_message = res_data["choices"][0]["message"]["content"]

        parsed_summary = json.loads(ai_message)
        return {"status": "success", "data": parsed_summary}

    except json.JSONDecodeError:
        return {
            "status": "success", 
            "data": {
                "summary": ai_message,
                "key_points": ["Analyse effectuée avec succès"],
                "topic": "Actualité"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
