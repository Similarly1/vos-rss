import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.rss import parse_and_save_feed, get_all_feeds, update_feed, delete_feed, refresh_all_feeds_and_vectorize, generate_opml_export, import_feeds_from_content
from app.services.feed_analyzer import analyze_feed_completeness
from app.config import settings

router = APIRouter(prefix="/api/feeds", tags=["Feeds"])

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
    return {"status": "success", "message": "Clé API enregistrée dans le fichier .env du serveur VPS !"}

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

@router.post("/refresh")
async def trigger_refresh_all(background_tasks: BackgroundTasks, payload: Optional[RefreshRequest] = None):
    try:
        api_key = (payload.api_key if payload else None) or settings.mistral_api_key
        # Execute refresh and vectorization asynchronously in BackgroundTasks
        background_tasks.add_task(refresh_all_feeds_and_vectorize, api_key)
        return {
            "status": "success",
            "message": "Rafraîchissement de tous les flux RSS démarré en arrière-plan !"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
