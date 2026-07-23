import traceback
from fastapi import APIRouter, HTTPException, Response, Request, Query
from pydantic import BaseModel
from typing import Optional

from app.services.podcast import (
    generate_podcast_show,
    get_podcast_history,
    generate_podcast_rss_feed,
    get_or_create_podcast_feed_token
)
from app.services.scheduler import load_schedule_config, save_schedule_config
from app.database import get_db_connection
from app.config import settings

router = APIRouter(prefix="/api/podcast", tags=["Podcast Studio"])

class PodcastGenerateRequest(BaseModel):
    topics_count: Optional[int] = 5
    max_days: Optional[int] = 7
    only_verified: Optional[bool] = False
    tone: Optional[str] = "journal_matinal"
    voice: Optional[str] = "Marie - Dynamic"
    theme: Optional[str] = None
    api_key: Optional[str] = None

class ScheduleConfigRequest(BaseModel):
    enabled: bool
    frequency: Optional[str] = "daily"
    time: Optional[str] = "07:00"
    topics_count: Optional[int] = 5
    max_days: Optional[int] = 7
    only_verified: Optional[bool] = True
    tone: Optional[str] = "journal_matinal"
    voice: Optional[str] = "Marie - Dynamic"
    theme: Optional[str] = ""

@router.get("/feed-token")
def get_feed_token():
    token = get_or_create_podcast_feed_token()
    return {"token": token}

@router.post("/feed-token/regenerate")
def regenerate_feed_token():
    token = get_or_create_podcast_feed_token(force_regenerate=True)
    return {"token": token}

@router.get("/feed.xml")
def get_podcast_feed_xml(request: Request, token: Optional[str] = Query(None)):
    """
    Returns a 100% valid RSS 2.0 Podcast XML feed for AntennaPod, Apple Podcasts, Spotify, Pocket Casts.
    Validates feed token if token protection is active.
    """
    expected_token = get_or_create_podcast_feed_token()
    if expected_token and token != expected_token:
        raise HTTPException(status_code=401, detail="Token de flux RSS invalide ou manquant.")

    try:
        base_url = str(request.base_url).rstrip("/")
        xml_content = generate_podcast_rss_feed(base_url=base_url, token=token)
        return Response(content=xml_content, media_type="application/xml; charset=utf-8")
    except Exception as e:
        print("[Podcast Feed XML Error]:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule")
def get_schedule():
    return load_schedule_config()

@router.post("/schedule")
def update_schedule(payload: ScheduleConfigRequest):
    current = load_schedule_config()
    updated = {
        **current,
        "enabled": payload.enabled,
        "frequency": payload.frequency or "daily",
        "time": payload.time or "07:00",
        "topics_count": payload.topics_count or 5,
        "max_days": payload.max_days if payload.max_days is not None else 7,
        "only_verified": bool(payload.only_verified),
        "tone": payload.tone or "journal_matinal",
        "voice": payload.voice or "Marie - Dynamic",
        "theme": payload.theme or ""
    }
    save_schedule_config(updated)
    return {"status": "success", "schedule": updated}

@router.get("/history")
def list_podcast_history():
    try:
        podcasts = get_podcast_history()
        return {"status": "success", "podcasts": podcasts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def create_podcast(payload: PodcastGenerateRequest, request: Request):
    try:
        api_key = payload.api_key or settings.mistral_api_key
        base_url = str(request.base_url).rstrip("/")
        result = await generate_podcast_show(
            topics_count=payload.topics_count or 5,
            max_days=payload.max_days if payload.max_days is not None else 7,
            only_verified=bool(payload.only_verified),
            tone=payload.tone or "journal_matinal",
            voice_key=payload.voice or "Marie - Dynamic",
            theme=payload.theme,
            api_key=api_key,
            base_url=base_url
        )
        return {"status": "success", "podcast": result}
    except Exception as e:
        print("[Podcast Generation Error Traceback]:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{podcast_id}")
def delete_podcast(podcast_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM podcasts WHERE id = ?", (podcast_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "podcast_id": podcast_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
