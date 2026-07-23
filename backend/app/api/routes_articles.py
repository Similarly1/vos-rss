from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
import httpx

from app.database import get_db_connection
from app.config import settings

router = APIRouter(prefix="/api/articles", tags=["Articles"])

class SummarizeRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = "mistral-small-latest"

@router.get("")
@router.get("/")
def get_articles(
    lang: Optional[str] = Query(None, description="Language filter (fr, en, de, es, all)"),
    full_text_only: Optional[bool] = Query(False, description="Show only full text articles")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, a.language, a.is_full_text, f.title as feed_title, f.category
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
        raise HTTPException(status_code=404, detail="Article introuvable")
    return dict(row)

@router.post("/{article_id}/summarize")
async def summarize_article(article_id: int, payload: SummarizeRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, url FROM articles WHERE id = ?", (article_id,))
    article = cursor.fetchone()
    conn.close()

    if not article:
        raise HTTPException(status_code=404, detail="Article introuvable")

    api_key = payload.api_key or settings.mistral_api_key
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API Mistral requise. Veuillez la renseigner dans les Paramètres de l'application."
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": payload.model or "mistral-small-latest",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )

        if response.status_code != 200:
            err_data = response.json()
            raise HTTPException(status_code=response.status_code, detail=err_data.get("message", "Erreur lors de l'appel Mistral AI."))

        res_data = response.json()
        ai_message = res_data["choices"][0]["message"]["content"]

        import json
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
