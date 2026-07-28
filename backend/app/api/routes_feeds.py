import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.rss import parse_and_save_feed, get_all_feeds, update_feed, delete_feed, refresh_all_feeds_and_vectorize, generate_opml_export, import_feeds_from_content, clean_old_articles
from app.services.feed_analyzer import analyze_feed_completeness
from app.services.podcast import set_app_setting, get_app_setting
from app.config import settings

router = APIRouter(prefix="/api/feeds", tags=["Feeds"])

def get_vps_api_key(provided_key: str = None) -> str:
    """
    Robustly resolves the Mistral API Key from payload, settings object, or .env file.
    """
    if provided_key and provided_key.strip():
        return provided_key.strip()

    if settings.mistral_api_key and settings.mistral_api_key.strip():
        return settings.mistral_api_key.strip()

    env_path = Path("./.env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MISTRAL_API_KEY="):
                        k = line.split("=", 1)[1].strip()
                        if k:
                            settings.mistral_api_key = k
                            return k
        except Exception:
            pass
    return ""

def get_vps_gemini_key(provided_key: str = None) -> str:
    if provided_key and provided_key.strip():
        return provided_key.strip()
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        return settings.gemini_api_key.strip()

    env_path = Path("./.env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        k = line.split("=", 1)[1].strip()
                        if k:
                            settings.gemini_api_key = k
                            return k
        except Exception:
            pass
    return ""

def get_vps_langsearch_key(provided_key: str = None) -> str:
    if provided_key and provided_key.strip():
        return provided_key.strip()
    if settings.langsearch_api_key and settings.langsearch_api_key.strip():
        return settings.langsearch_api_key.strip()

    env_path = Path("./.env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("LANGSEARCH_API_KEY="):
                        k = line.split("=", 1)[1].strip()
                        if k:
                            settings.langsearch_api_key = k
                            return k
        except Exception:
            pass
    return ""

class FeedInput(BaseModel):
    url: str
    category: Optional[str] = "Général"
    language: Optional[str] = None
    is_full_text: Optional[bool] = None

class FeedUpdateInput(BaseModel):
    title: str
    category: Optional[str] = "Général"
    language: Optional[str] = "fr"
    is_full_text: Optional[bool] = True

class RefreshRequest(BaseModel):
    api_key: Optional[str] = None

class CleanupRequest(BaseModel):
    retention_days: int

class AnalyzeRequest(BaseModel):
    url: str

class ImportOpmlRequest(BaseModel):
    content: str

class AppSettingsRequest(BaseModel):
    mistral_key: Optional[str] = None
    gemini_key: Optional[str] = None
    langsearch_key: Optional[str] = None
    synthesis_provider: Optional[str] = None
    vectorization_provider: Optional[str] = None
    mistral_model: Optional[str] = None
    gemini_model: Optional[str] = None
    mistral_article_model: Optional[str] = None
    gemini_article_model: Optional[str] = None
    mistral_discover_model: Optional[str] = None
    gemini_discover_model: Optional[str] = None
    mistral_podcast_model: Optional[str] = None
    gemini_podcast_model: Optional[str] = None
    synthesis_fallback_provider: Optional[str] = None
    vectorization_fallback_provider: Optional[str] = None
    mistral_embed_model: Optional[str] = None
    gemini_embed_model: Optional[str] = None
    refresh_interval_minutes: Optional[int] = None
    article_retention_days: Optional[int] = None
    article_language: Optional[str] = None
    full_text_only: Optional[bool] = None
    nav_tabs_order: Optional[str] = None
    default_landing_tab: Optional[str] = None
    webhook_model: Optional[str] = None

@router.get("")
@router.get("/")
def list_feeds():
    return get_all_feeds()

@router.get("/export/opml")
def export_opml():
    try:
        opml_xml = generate_opml_export()
        return Response(
            content=opml_xml,
            media_type="text/x-opml",
            headers={"Content-Disposition": "attachment; filename=vos_abonnements_rss.opml"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/opml")
def import_opml(payload: ImportOpmlRequest):
    try:
        res = import_feeds_from_content(payload.content)
        return res
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/settings")
def get_settings():
    return {
        "status": "success",
        "data": {
            "mistral_key": settings.mistral_api_key or get_vps_api_key(),
            "gemini_key": settings.gemini_api_key or get_vps_gemini_key(),
            "langsearch_key": settings.langsearch_api_key or get_vps_langsearch_key(),
            "synthesis_provider": settings.synthesis_provider,
            "vectorization_provider": settings.vectorization_provider,
            "mistral_model": settings.mistral_model,
            "gemini_model": settings.gemini_model,
            "mistral_article_model": settings.mistral_article_model,
            "gemini_article_model": settings.gemini_article_model,
            "mistral_discover_model": settings.mistral_discover_model,
            "gemini_discover_model": settings.gemini_discover_model,
            "mistral_podcast_model": settings.mistral_podcast_model,
            "gemini_podcast_model": settings.gemini_podcast_model,
            "synthesis_fallback_provider": settings.synthesis_fallback_provider,
            "vectorization_fallback_provider": settings.vectorization_fallback_provider,
            "mistral_embed_model": settings.mistral_embed_model,
            "gemini_embed_model": settings.gemini_embed_model,
            "refresh_interval_minutes": settings.refresh_interval_minutes,
            "article_retention_days": settings.article_retention_days,
            "article_language": settings.article_language,
            "full_text_only": settings.full_text_only,
            "nav_tabs_order": get_app_setting("nav_tabs_order", ""),
            "default_landing_tab": get_app_setting("default_landing_tab", "articles"),
            "webhook_model": get_app_setting("webhook_model", ""),
        }
    }

@router.post("/settings")
def save_settings(payload: AppSettingsRequest):
    env_path = Path("./.env")
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Define the variables to update
    updates = {
        "MISTRAL_API_KEY": payload.mistral_key if payload.mistral_key is not None else settings.mistral_api_key,
        "GEMINI_API_KEY": payload.gemini_key if payload.gemini_key is not None else settings.gemini_api_key,
        "LANGSEARCH_API_KEY": payload.langsearch_key if payload.langsearch_key is not None else settings.langsearch_api_key,
        "SYNTHESIS_PROVIDER": payload.synthesis_provider if payload.synthesis_provider is not None else settings.synthesis_provider,
        "VECTORIZATION_PROVIDER": payload.vectorization_provider if payload.vectorization_provider is not None else settings.vectorization_provider,
        "MISTRAL_MODEL": payload.mistral_model if payload.mistral_model is not None else settings.mistral_model,
        "GEMINI_MODEL": payload.gemini_model if payload.gemini_model is not None else settings.gemini_model,
        "MISTRAL_ARTICLE_MODEL": payload.mistral_article_model if payload.mistral_article_model is not None else settings.mistral_article_model,
        "GEMINI_ARTICLE_MODEL": payload.gemini_article_model if payload.gemini_article_model is not None else settings.gemini_article_model,
        "MISTRAL_DISCOVER_MODEL": payload.mistral_discover_model if payload.mistral_discover_model is not None else settings.mistral_discover_model,
        "GEMINI_DISCOVER_MODEL": payload.gemini_discover_model if payload.gemini_discover_model is not None else settings.gemini_discover_model,
        "MISTRAL_PODCAST_MODEL": payload.mistral_podcast_model if payload.mistral_podcast_model is not None else settings.mistral_podcast_model,
        "GEMINI_PODCAST_MODEL": payload.gemini_podcast_model if payload.gemini_podcast_model is not None else settings.gemini_podcast_model,
        "SYNTHESIS_FALLBACK_PROVIDER": payload.synthesis_fallback_provider if payload.synthesis_fallback_provider is not None else settings.synthesis_fallback_provider,
        "VECTORIZATION_FALLBACK_PROVIDER": payload.vectorization_fallback_provider if payload.vectorization_fallback_provider is not None else settings.vectorization_fallback_provider,
        "MISTRAL_EMBED_MODEL": payload.mistral_embed_model if payload.mistral_embed_model is not None else settings.mistral_embed_model,
        "GEMINI_EMBED_MODEL": payload.gemini_embed_model if payload.gemini_embed_model is not None else settings.gemini_embed_model,
        "REFRESH_INTERVAL_MINUTES": str(payload.refresh_interval_minutes) if payload.refresh_interval_minutes is not None else str(settings.refresh_interval_minutes),
        "ARTICLE_RETENTION_DAYS": str(payload.article_retention_days) if payload.article_retention_days is not None else str(settings.article_retention_days),
        "ARTICLE_LANGUAGE": payload.article_language if payload.article_language is not None else settings.article_language,
        "FULL_TEXT_ONLY": str(payload.full_text_only).lower() if payload.full_text_only is not None else str(settings.full_text_only).lower(),
    }

    new_lines = []
    updated_keys = set()
    
    for line in lines:
        updated = False
        for k, v in updates.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                updated_keys.add(k)
                updated = True
                break
        if not updated:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Update global settings in memory
    if payload.mistral_key is not None: settings.mistral_api_key = payload.mistral_key
    if payload.gemini_key is not None: settings.gemini_api_key = payload.gemini_key
    if payload.langsearch_key is not None: settings.langsearch_api_key = payload.langsearch_key
    if payload.synthesis_provider is not None: settings.synthesis_provider = payload.synthesis_provider
    if payload.vectorization_provider is not None: settings.vectorization_provider = payload.vectorization_provider
    if payload.mistral_model is not None: settings.mistral_model = payload.mistral_model
    if payload.gemini_model is not None: settings.gemini_model = payload.gemini_model
    if payload.mistral_article_model is not None: settings.mistral_article_model = payload.mistral_article_model
    if payload.gemini_article_model is not None: settings.gemini_article_model = payload.gemini_article_model
    if payload.mistral_discover_model is not None: settings.mistral_discover_model = payload.mistral_discover_model
    if payload.gemini_discover_model is not None: settings.gemini_discover_model = payload.gemini_discover_model
    if payload.mistral_podcast_model is not None: settings.mistral_podcast_model = payload.mistral_podcast_model
    if payload.gemini_podcast_model is not None: settings.gemini_podcast_model = payload.gemini_podcast_model
    if payload.synthesis_fallback_provider is not None: settings.synthesis_fallback_provider = payload.synthesis_fallback_provider
    if payload.vectorization_fallback_provider is not None: settings.vectorization_fallback_provider = payload.vectorization_fallback_provider
    if payload.mistral_embed_model is not None: settings.mistral_embed_model = payload.mistral_embed_model
    if payload.gemini_embed_model is not None: settings.gemini_embed_model = payload.gemini_embed_model
    if payload.refresh_interval_minutes is not None: settings.refresh_interval_minutes = payload.refresh_interval_minutes
    if payload.article_retention_days is not None: settings.article_retention_days = payload.article_retention_days
    if payload.article_language is not None: settings.article_language = payload.article_language
    if payload.full_text_only is not None: settings.full_text_only = payload.full_text_only

    if payload.nav_tabs_order is not None:
        set_app_setting("nav_tabs_order", payload.nav_tabs_order)
    if payload.default_landing_tab is not None:
        set_app_setting("default_landing_tab", payload.default_landing_tab)
    if payload.webhook_model is not None:
        set_app_setting("webhook_model", payload.webhook_model)
        
    return {"status": "success", "message": "Paramètres enregistrés dans le fichier .env et en base !"}

class KeyTestRequest(BaseModel):
    key: Optional[str] = None

@router.post("/test-mistral")
async def test_mistral_key(payload: KeyTestRequest):
    import httpx
    key = payload.key or settings.mistral_api_key or get_vps_api_key()
    if not key:
        return {"status": "error", "message": "Clé API Mistral manquante."}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0
            )
            if res.status_code == 200:
                return {"status": "success", "message": "Connexion réussie à l'API Mistral AI !"}
            err_msg = res.json().get("message", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
            return {"status": "error", "message": f"Erreur Mistral ({res.status_code}) : {err_msg}"}
    except Exception as e:
        return {"status": "error", "message": f"Erreur de connexion Mistral : {str(e)}"}

@router.post("/test-gemini")
async def test_gemini_key(payload: KeyTestRequest):
    import httpx
    key = payload.key or settings.gemini_api_key or get_vps_gemini_key()
    if not key:
        return {"status": "error", "message": "Clé API Gemini manquante."}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                timeout=10.0
            )
            if res.status_code == 200:
                return {"status": "success", "message": "Connexion réussie à l'API Google Gemini !"}
            
            err_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            detail = err_data.get("error", {}).get("message", res.text)
            if "invalid authentication credentials" in detail.lower() or res.status_code == 401:
                detail = f"{detail} (Note : Utilisez une clé API Google AI Studio ex: AIzaSy... créée sur https://aistudio.google.com/app/apikey)"
            return {"status": "error", "message": f"Erreur Gemini ({res.status_code}) : {detail}"}
    except Exception as e:
        return {"status": "error", "message": f"Erreur de connexion Gemini : {str(e)}"}

@router.post("/test-langsearch")
async def test_langsearch_key(payload: KeyTestRequest):
    import httpx
    key = payload.key or settings.langsearch_api_key or get_vps_langsearch_key()
    if not key:
        return {"status": "error", "message": "Clé API LangSearch manquante."}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.langsearch.com/v1/web-search",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"query": "test actualites", "summary": False, "count": 1},
                timeout=10.0
            )
            if res.status_code == 200:
                return {"status": "success", "message": "Connexion réussie à l'API LangSearch !"}
            err_msg = res.json().get("message", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
            return {"status": "error", "message": f"Erreur LangSearch ({res.status_code}) : {err_msg}"}
    except Exception as e:
        return {"status": "error", "message": f"Erreur de connexion LangSearch : {str(e)}"}

@router.post("")
@router.post("/")
def add_feed(payload: FeedInput):
    try:
        result = parse_and_save_feed(
            payload.url, 
            payload.category or "Général",
            language=payload.language,
            is_full_text=payload.is_full_text
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze")
def analyze_feed(payload: AnalyzeRequest):
    try:
        res = analyze_feed_completeness(payload.url)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{feed_id}")
def edit_feed(feed_id: int, payload: FeedUpdateInput):
    try:
        res = update_feed(
            feed_id, 
            payload.title, 
            payload.category or "Général",
            language=payload.language or "fr",
            is_full_text=payload.is_full_text if payload.is_full_text is not None else True
        )
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{feed_id}")
def remove_feed(feed_id: int):
    try:
        res = delete_feed(feed_id)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cleanup")
def cleanup_articles(payload: CleanupRequest):
    try:
        set_app_setting("article_retention_days", str(payload.retention_days))
        res = clean_old_articles(payload.retention_days)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refresh")
async def trigger_refresh_all(background_tasks: BackgroundTasks, payload: Optional[RefreshRequest] = None):
    try:
        api_key = get_vps_api_key(payload.api_key if payload else None)
        background_tasks.add_task(refresh_all_feeds_and_vectorize, api_key)
        return {
            "status": "success",
            "message": "Rafraîchissement de tous les flux RSS démarré en arrière-plan !"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
