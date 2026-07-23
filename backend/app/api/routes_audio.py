import traceback
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from app.services.audio import generate_podcast_audio, fetch_mistral_voices, AUDIO_DIR
from app.config import settings

router = APIRouter(prefix="/api/audio", tags=["Audio"])

class AudioGenerateRequest(BaseModel):
    text: str
    voice: Optional[str] = "marie"
    api_key: Optional[str] = None

@router.get("/voices")
async def list_voices(api_key: Optional[str] = Query(None)):
    key = api_key or settings.mistral_api_key
    voices = await fetch_mistral_voices(key)
    return {"voices": voices}

@router.post("/generate")
async def create_audio(payload: AudioGenerateRequest, request: Request):
    try:
        api_key = payload.api_key or settings.mistral_api_key
        filename = await generate_podcast_audio(payload.text, voice_key=payload.voice or "marie", api_key=api_key)
        
        # Build base URL dynamically from request headers or settings for VPS compatibility
        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/api/audio/stream/{filename}"
        
        return {
            "status": "success",
            "filename": filename,
            "audio_url": audio_url
        }
    except Exception as e:
        print("[Audio Generation Error Traceback]:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stream/{filename}")
def stream_audio(filename: str):
    filepath = AUDIO_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Fichier audio introuvable")
    return FileResponse(filepath, media_type="audio/mpeg", filename=filename)
