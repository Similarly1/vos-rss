import traceback
from fastapi import APIRouter, HTTPException, Response, Request, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

from app.services.podcast import (
    generate_podcast_show,
    get_podcast_history,
    generate_podcast_rss_feed,
    get_or_create_podcast_feed_token
)
from app.services.scheduler import (
    load_schedules,
    save_schedules,
    add_schedule_program,
    update_schedule_program,
    toggle_schedule_program,
    delete_schedule_program
)
from app.api.routes_feeds import get_vps_api_key
from app.database import get_db_connection
from app.config import settings

router = APIRouter(prefix="/api/podcast", tags=["Podcast Studio"])

class PodcastGenerateRequest(BaseModel):
    topics_count: Optional[int] = 5
    max_days: Optional[int] = 7
    only_verified: Optional[bool] = False
    tone: Optional[str] = "journal_matinal"
    voice: Optional[str] = "Marie - Neutral"
    theme: Optional[str] = None
    api_key: Optional[str] = None

class ScheduleProgramInput(BaseModel):
    name: Optional[str] = "Nouveau Programme Radio"
    enabled: Optional[bool] = True
    frequency: Optional[str] = "daily"
    time: Optional[str] = "07:00"
    topics_count: Optional[int] = 5
    max_days: Optional[int] = 7
    only_verified: Optional[bool] = True
    tone: Optional[str] = "journal_matinal"
    voice: Optional[str] = "Marie - Neutral"
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

# --- MULTI-PROGRAM PODCAST DASHBOARD API ENDPOINTS ---

@router.get("/schedules")
@router.get("/schedule")
def list_schedules():
    try:
        programs = load_schedules()
        return {"status": "success", "schedules": programs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedules")
def create_schedule(payload: ScheduleProgramInput):
    try:
        new_prog = add_schedule_program(payload.dict())
        return {"status": "success", "program": new_prog}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/schedules/{program_id}")
def edit_schedule(program_id: str, payload: ScheduleProgramInput):
    try:
        updated = update_schedule_program(program_id, payload.dict())
        return {"status": "success", "program": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/schedules/{program_id}/toggle")
def toggle_schedule(program_id: str):
    try:
        updated = toggle_schedule_program(program_id)
        return {"status": "success", "program": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/schedules/{program_id}")
def remove_schedule(program_id: str):
    try:
        res = delete_schedule_program(program_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/schedules/{program_id}/run")
async def run_schedule_now(program_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    Triggers an instant run of a specific program in the background.
    """
    programs = load_schedules()
    target_prog = next((p for p in programs if p["id"] == program_id), None)
    if not target_prog:
        raise HTTPException(status_code=404, detail="Programme introuvable.")

    base_url = str(request.base_url).rstrip("/")
    key = get_vps_api_key()

    async def run_bg():
        try:
            await generate_podcast_show(
                topics_count=target_prog.get("topics_count", 5),
                max_days=target_prog.get("max_days", 7),
                only_verified=target_prog.get("only_verified", True),
                tone=target_prog.get("tone", "journal_matinal"),
                voice_key=target_prog.get("voice", "Marie - Neutral"),
                theme=target_prog.get("theme", ""),
                api_key=key,
                base_url=base_url
            )
        except Exception as e:
            print(f"[Run Schedule Now Error]: {e}")

    background_tasks.add_task(run_bg)
    return {"status": "success", "message": f"Émission '{target_prog.get('name')}' lancée en arrière-plan !"}

# --- PODCAST GENERATION & HISTORY ---

@router.get("/history")
def list_podcast_history(request: Request):
    try:
        base_url = str(request.base_url).rstrip("/")
        podcasts = get_podcast_history(base_url=base_url)
        return {"status": "success", "podcasts": podcasts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def create_podcast(payload: PodcastGenerateRequest, request: Request):
    try:
        api_key = get_vps_api_key(payload.api_key)
        base_url = str(request.base_url).rstrip("/")
        result = await generate_podcast_show(
            topics_count=payload.topics_count or 5,
            max_days=payload.max_days if payload.max_days is not None else 7,
            only_verified=bool(payload.only_verified),
            tone=payload.tone or "journal_matinal",
            voice_key=payload.voice or "Marie - Neutral",
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
