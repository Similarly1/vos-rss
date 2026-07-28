from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
from app.services.audio import sanitize_text_for_speech

router = APIRouter(prefix="/api/audio", tags=["Audio Stream"])

class StreamRequest(BaseModel):
    text: str
    voice: str = "marie"
    api_key: str

@router.post("/stream-tts")
async def stream_tts(payload: StreamRequest):
    clean_text = sanitize_text_for_speech(payload.text)
    if not clean_text:
        raise HTTPException(status_code=400, detail="Texte vide après nettoyage.")
        
    async def event_generator():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    "https://api.mistral.ai/v1/audio/speech",
                    json={
                        "model": "voxtral-mini-tts-2603",
                        "input": clean_text,
                        "voice_id": payload.voice,
                        "response_format": "mp3"
                    },
                    headers={
                        "Authorization": f"Bearer {payload.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        return

                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        yield chunk
            except Exception as e:
                pass
                
    return StreamingResponse(event_generator(), media_type="audio/mpeg")
