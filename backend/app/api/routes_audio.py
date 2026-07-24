import traceback
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from app.services.audio import generate_podcast_audio, fetch_mistral_voices, AUDIO_DIR
from app.services.podcast import get_or_create_podcast_feed_token, sanitize_base_url
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
        
        base_url = sanitize_base_url(str(request.base_url))
        token = get_or_create_podcast_feed_token()
        token_param = f"?token={token}" if token else ""
        audio_url = f"{base_url}/api/audio/stream/{filename}{token_param}"
        
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
def stream_audio(filename: str, token: Optional[str] = Query(None)):
    expected_token = get_or_create_podcast_feed_token()
    if expected_token and token and token.strip() != expected_token.strip():
        raise HTTPException(status_code=401, detail="Token d'accès audio invalide")

    # Search candidate paths for backward compatibility with previously generated files
    candidate_paths = [
        AUDIO_DIR / filename,
        Path("./audio_cache") / filename,
        Path("../audio_cache") / filename,
        Path(__file__).resolve().parent.parent.parent / "audio_cache" / filename,
    ]

    target_filepath = None
    for p in candidate_paths:
        if p.exists():
            target_filepath = p
            break

    if not target_filepath:
        raise HTTPException(status_code=404, detail="Fichier audio introuvable")

    return FileResponse(
        target_filepath,
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=31536000"
        }
    )
