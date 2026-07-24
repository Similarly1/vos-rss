import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.rss import parse_and_save_feed, get_all_feeds, update_feed, delete_feed, refresh_all_feeds_and_vectorize, generate_opml_export, import_feeds_from_content, clean_old_articles
from app.services.feed_analyzer import analyze_feed_completeness
from app.services.podcast import set_app_setting
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

class SaveEnvKeyRequest(BaseModel):
    api_key: str

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

@router.get("/env-key")
def get_env_key():
    key = get_vps_api_key()
    has_key = bool(key)
    masked = (key[:4] + "..." + key[-4:]) if len(key) >= 8 else ""
    return {"status": "success", "has_key": has_key, "key": key, "masked": masked}

@router.post("/save-env-key")
def save_env_key(payload: SaveEnvKeyRequest):
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="La clé API ne peut pas être vide.")

    env_path = Path("./.env")
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    key_updated = False
    new_lines = []
    for line in lines:
        if line.startswith("MISTRAL_API_KEY="):
            new_lines.append(f"MISTRAL_API_KEY={key}\n")
            key_updated = True
        else:
            new_lines.append(line)

    if not key_updated:
        new_lines.append(f"MISTRAL_API_KEY={key}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    settings.mistral_api_key = key
    return {"status": "success", "message": "Clé API enregistrée dans le fichier .env du serveur VPS !", "key": key}

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
