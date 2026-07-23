import os
import hashlib
import httpx
import re
import base64
from pathlib import Path
from app.config import settings

AUDIO_DIR = Path("./audio_cache")
AUDIO_DIR.mkdir(exist_ok=True)

def sanitize_text_for_speech(text: str) -> str:
    """
    Strips all URLs, domains, HTML tags, and RSS link noise before feeding to TTS engine.
    """
    if not text:
        return ""

    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'https?://[^\s>]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'www\.[^\s>]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b[a-zA-Z0-9.-]+\.(?:com|ch|fr|net|org|html|php)\b[^\s]*', '', clean, flags=re.IGNORECASE)

    prefixes = [
        r"^Suisse\s*-\s*Radio\s*Télévision\s*Suisse\s*:\s*",
        r"^Le\s*Temps\s*:\s*",
        r"^Le\s*Monde\s*:\s*"
    ]
    for p in prefixes:
        clean = re.sub(p, "", clean, flags=re.IGNORECASE).strip()

    clean = re.sub(r'[*_#`~\[\]]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:1500]

OFFICIAL_MARIE_EMOTIONS = [
    {"id": "Marie - Dynamic", "name": "🎭 Marie - Dynamic Multi-Émotions (Adaptation automatique)"},
    {"id": "Marie - Excited", "name": "⚡ Marie - Excited (Enthousiaste / Excité)"},
    {"id": "Marie - Neutral", "name": "🧘 Marie - Neutral (Calme & Neutre)"},
    {"id": "Marie - Happy", "name": "😊 Marie - Happy (Joyeuse)"},
    {"id": "Marie - Sad", "name": "💬 Marie - Sad (Triste / Grave)"},
    {"id": "Marie - Curious", "name": "🔍 Marie - Curious (Curieuse)"},
    {"id": "Marie - Angry", "name": "📢 Marie - Angry (Indignée / Fermée)"},
]

async def fetch_mistral_voices(api_key: str = None) -> list:
    """
    Fetches available voices from Mistral Studio API (GET /v1/audio/voices).
    """
    key = (api_key or settings.mistral_api_key or "").strip()
    if not key:
        return OFFICIAL_MARIE_EMOTIONS

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.mistral.ai/v1/audio/voices?limit=50",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0
            )
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", [])
                if items:
                    return [
                        {
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "languages": item.get("languages", ["fr"])
                        }
                        for item in items
                    ]
    except Exception as e:
        print(f"[Mistral Voices fetch note]: {e}")

    return OFFICIAL_MARIE_EMOTIONS

async def generate_audio_bytes_for_voice(text: str, voice_key: str = "Marie - Neutral", api_key: str = None) -> bytes:
    """
    Generates MP3 audio bytes using Mistral Voxtral Speech API.
    """
    clean_text = sanitize_text_for_speech(text)
    if not clean_text:
        clean_text = "Synthèse d'actualité."

    key = (api_key or settings.mistral_api_key or "").strip()
    if not key:
        raise ValueError("Clé API Mistral introuvable. Veuillez renseigner votre clé API Mistral dans les Paramètres (icône ⚙️).")

    v_requested = voice_key.strip() if voice_key else "Marie - Neutral"
    target_voice_id = None

    voices_list = await fetch_mistral_voices(key)

    if re.match(r'^[0-9a-fA-F-]{32,36}$', v_requested):
        target_voice_id = v_requested
    else:
        for v in voices_list:
            if v["name"].strip().lower() == v_requested.strip().lower():
                target_voice_id = v["id"]
                break

        if not target_voice_id:
            req_lower = v_requested.lower()
            for v in voices_list:
                v_name_lower = v["name"].lower()
                if ("excited" in req_lower or "excite" in req_lower) and "excited" in v_name_lower:
                    target_voice_id = v["id"]
                    break
                elif ("happy" in req_lower or "joyeuse" in req_lower) and "happy" in v_name_lower:
                    target_voice_id = v["id"]
                    break
                elif ("sad" in req_lower or "triste" in req_lower) and "sad" in v_name_lower:
                    target_voice_id = v["id"]
                    break
                elif ("curious" in req_lower or "curieuse" in req_lower) and "curious" in v_name_lower:
                    target_voice_id = v["id"]
                    break
                elif ("angry" in req_lower) and "angry" in v_name_lower:
                    target_voice_id = v["id"]
                    break
                elif ("neutral" in req_lower or "neutre" in req_lower) and "neutral" in v_name_lower:
                    target_voice_id = v["id"]
                    break

        if not target_voice_id:
            for v in voices_list:
                if "marie" in v["name"].lower():
                    target_voice_id = v["id"]
                    break
            if not target_voice_id and voices_list:
                target_voice_id = voices_list[0]["id"]

    if not target_voice_id:
        target_voice_id = "marie"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mistral.ai/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "voxtral-mini-tts-2603",
                "input": clean_text,
                "voice_id": target_voice_id,
                "response_format": "mp3"
            },
            timeout=40.0
        )
        
        if response.status_code == 200:
            res_json = response.json()
            audio_b64 = res_json.get("audio_data")
            if not audio_b64:
                raise ValueError("Format de réponse Mistral Audio inattendu (pas d'audio_data).")
            return base64.b64decode(audio_b64)
        elif response.status_code == 401:
            raise ValueError("Clé API Mistral non valide (401 Unauthorized).")
        else:
            raise ValueError(f"Erreur API Mistral Voxtral ({response.status_code}): {response.text}")

async def generate_podcast_audio(text: str, voice_key: str = "Marie - Neutral", api_key: str = None) -> str:
    """
    Generates high quality MP3 audio and saves to file cache.
    """
    clean_text = sanitize_text_for_speech(text)
    if not clean_text:
        clean_text = "Synthèse d'actualité."

    v_requested = voice_key.strip() if voice_key else "Marie - Neutral"
    text_hash = hashlib.md5(f"{clean_text}_{v_requested}".encode('utf-8')).hexdigest()
    filename = f"voxtral_{text_hash}.mp3"
    filepath = AUDIO_DIR / filename

    if filepath.exists():
        return filename

    audio_bytes = await generate_audio_bytes_for_voice(clean_text, voice_key=v_requested, api_key=api_key)
    with open(filepath, "wb") as f:
        f.write(audio_bytes)
    return filename

def combine_audio_chunks(audio_chunks: list[bytes]) -> str:
    """
    Concatenates multiple MP3 byte streams into a single combined MP3 file.
    """
    combined_bytes = b"".join(audio_chunks)
    combined_hash = hashlib.md5(combined_bytes).hexdigest()
    filename = f"voxtral_multi_{combined_hash}.mp3"
    filepath = AUDIO_DIR / filename

    with open(filepath, "wb") as f:
        f.write(combined_bytes)

    return filename

def get_available_voices():
    return OFFICIAL_MARIE_EMOTIONS
