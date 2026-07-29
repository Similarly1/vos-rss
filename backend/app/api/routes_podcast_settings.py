from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
from pathlib import Path
from app.services.podcast import get_app_setting, set_app_setting, DEFAULT_SYSTEM_PROMPT
from app.services.audio import AUDIO_DIR

router = APIRouter(prefix="/api/podcast/settings", tags=["Podcast Settings"])

class SettingsUpdate(BaseModel):
    podcast_system_prompt: str | None = None
    podcast_jingle_filename: str | None = None

@router.get("/")
def get_settings():
    prompt = get_app_setting("podcast_system_prompt", DEFAULT_SYSTEM_PROMPT)
    if not prompt or not prompt.strip():
        prompt = DEFAULT_SYSTEM_PROMPT
    jingle = get_app_setting("podcast_jingle_filename", "whoosh_default.mp3")
    return {
        "podcast_system_prompt": prompt,
        "podcast_jingle_filename": jingle
    }

@router.put("/")
def update_settings(payload: SettingsUpdate):
    if payload.podcast_system_prompt is not None:
        set_app_setting("podcast_system_prompt", payload.podcast_system_prompt)
    if payload.podcast_jingle_filename is not None:
        set_app_setting("podcast_jingle_filename", payload.podcast_jingle_filename)
    return {"status": "success"}

@router.post("/reset-prompt")
def reset_prompt():
    set_app_setting("podcast_system_prompt", "")
    return {"status": "success"}

@router.post("/reset-jingle")
def reset_jingle():
    set_app_setting("podcast_jingle_filename", "whoosh_default.mp3")
    return {"status": "success"}

@router.post("/upload-jingle")
async def upload_jingle(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers MP3 sont autorisés.")
    
    # Save to audio_cache as whoosh_custom.mp3
    filename = "whoosh_custom.mp3"
    dest_path = AUDIO_DIR / filename
    
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        set_app_setting("podcast_jingle_filename", filename)
        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'écriture du fichier : {e}")
