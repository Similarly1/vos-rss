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
                        "response_format": "mp3",
                        "stream": True
                    },
                    headers={
                        "Authorization": f"Bearer {payload.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'error': f'Mistral API Error: {response.status_code}'})}\n\n"
                        return

                    async for chunk in response.aiter_lines():
                        if chunk.startswith("data: "):
                            data_str = chunk[6:].strip()
                            if data_str == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                data = json.loads(data_str)
                                # Extraire l'audio base64 pour renvoyer au client
                                audio_b64 = None
                                if "delta" in data and "audio" in data["delta"]:
                                    audio_b64 = data["delta"]["audio"]
                                elif "audio_data" in data:
                                    audio_b64 = data["audio_data"]
                                
                                if audio_b64:
                                    yield f"data: {json.dumps({'audio': audio_b64})}\n\n"
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")
