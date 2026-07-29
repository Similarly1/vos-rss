import json
import httpx
import re
import secrets
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse
from app.database import get_db_connection
from app.config import settings
from app.services.clustering import compute_article_clusters
from app.services.audio import (
    generate_podcast_audio,
    generate_audio_bytes_for_voice,
    combine_audio_chunks,
    split_script_into_emotion_segments,
    sanitize_text_for_speech,
    AUDIO_DIR
)

DEFAULT_PODCAST_COVER = "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=1000&h=1000&q=80"

def make_image_square(url: str) -> str:
    if not url:
        return DEFAULT_PODCAST_COVER
    if "unsplash.com" in url:
        # Strip existing sizing parameters and force square crop
        clean_url = re.sub(r'[?&](w|h|fit|rect|crop)=[^&]*', '', url)
        connector = "&" if "?" in clean_url else "?"
        return f"{clean_url}{connector}fit=crop&w=1000&h=1000&q=80"
    return url

DEFAULT_SYSTEM_PROMPT = (
    "Tu es un journaliste radio chevronné et le présentateur principal de l'émission d'actualités 'Vos'. "
    "Ton rôle est de rédiger un script d'émission d'actualités radio d'une qualité professionnelle irréprochable.\n\n"
    "CONSIGNES STRICTES POUR LA RÉDACTION ET LA SYNTHÈSE VOCALE (TTS) :\n"
    "1. INTERDICTION DE MENTIONNER L'HEURE DE LA JOURNÉE (ne jamais écrire 'il est 7h30', 'il est 8h' ou toute heure fixe).\n"
    "2. INTERDICTION ABSOLUE DE FAIRE UN SOMMAIRE OU UN RAPPEL DES TITRES EN INTRO. Après une phrase courte d'accroche (ex: 'Bonjour et bienvenue dans Vos, votre revue de presse quotidienne.'), entre directement dans le premier sujet d'actualité.\n"
    "3. INTERDICTION ABSOLUE des crochets et textes entre parenthèses dans le texte des sujets. Pas de [Votre Nom], [Musique], etc.\n"
    "4. Ne répète jamais le nom de l'émission de façon répétitive.\n"
    "5. Rédige un français naturel, captivant, vivant et dynamique.\n"
    "6. Cite clairement et naturellement les médias sources (ex: 'Selon Le Monde...', 'D'après TechCrunch...').\n"
    "7. Évite les phrases moralisatrices en conclusion."
)

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

def get_french_date_str() -> str:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    day_name = DAYS_FR[now.weekday()]
    month_name = MONTHS_FR[now.month - 1]
    return f"{day_name} {now.day} {month_name} {now.year}"

def format_script_html(script_text) -> str:
    if not script_text:
        return "<p>Aucune transcription disponible.</p>"
    
    if isinstance(script_text, dict):
        script_text = "\n\n".join([f"{k} : {v}" if isinstance(v, str) else str(v) for k, v in script_text.items()])
    elif isinstance(script_text, list):
        script_text = "\n\n".join([str(x) for x in script_text])
    elif not isinstance(script_text, str):
        script_text = str(script_text)

    lines = [line.strip() for line in script_text.split("\n") if line.strip()]
    html_parts = []
    
    for line in lines:
        if line.startswith("#") or line.startswith("---") or line.lower().startswith("sujet"):
            clean_title = re.sub(r"^[#\-\s]+", "", line)
            html_parts.append(f"<h4 style=\"color:#2563eb;margin-top:14px;margin-bottom:6px;\">📌 {xml_escape(clean_title)}</h4>")
        elif line.startswith("- ") or line.startswith("* "):
            html_parts.append(f"<li style=\"margin-bottom:4px;\">{xml_escape(line[2:].strip())}</li>")
        else:
            html_parts.append(f"<p style=\"margin-bottom:10px;\">{xml_escape(line)}</p>")
            
    return "\n".join(html_parts)

def sanitize_script_for_tts(text) -> str:
    if not text:
        return ""

    if isinstance(text, dict):
        text = "\n\n".join([f"{k} : {v}" if isinstance(v, str) else str(v) for k, v in text.items()])
    elif isinstance(text, list):
        text = "\n\n".join([str(x) for x in text])
    elif not isinstance(text, str):
        text = str(text)

    text = re.sub(r"\[([^\]]+)\]", "", text)
    text = re.sub(r"\((musique|rires|pause|transition|jingle|sourire|silence)[^\)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"revue\s+de\s+presse\s+Vos\s+Revue\s+de\s+Presse", "revue de presse Vos", text, flags=re.IGNORECASE)
    text = re.sub(r"revue\s+de\s+presse\s+Vos\s+Revue\s+de\s+presse", "revue de presse Vos", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,\.\?!;:])", r"\1", text)
    return text.strip()

def clean_podcast_title(raw_title) -> str:
    if not raw_title:
        return f"Vos : Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"

    if isinstance(raw_title, (dict, list)):
        raw_title = json.dumps(raw_title, ensure_ascii=False)
    elif not isinstance(raw_title, str):
        raw_title = str(raw_title)

    t = raw_title.strip().strip('"\'')
    t = re.sub(r"^\s*Vos\s+Revue\s+de\s+Presse\s*\(Revue\s+de\s+presse\)\s*-?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*Vos\s+Revue\s+de\s+Presse\s*-?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*Revue\s+de\s+presse\s*-?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\(Revue\s+de\s+presse\)\s*$", "", t, flags=re.IGNORECASE)
    t = t.strip(" :-")
    
    if not t:
        return f"Vos : Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"
    return f"Vos : {t}"

def get_app_setting(key: str, default: str = "") -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else default
    except Exception:
        return default

def set_app_setting(key: str, value: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[set_app_setting note]: {e}")

def get_or_create_podcast_feed_token(force_regenerate: bool = False) -> str:
    if settings.podcast_feed_token and not force_regenerate:
        return settings.podcast_feed_token.strip()
    
    if not force_regenerate:
        stored_token = get_app_setting("podcast_feed_token")
        if stored_token:
            return stored_token
    
    new_token = secrets.token_hex(16)
    set_app_setting("podcast_feed_token", new_token)
    return new_token

def extract_cover_image(selected_topics: list) -> str:
    if not selected_topics:
        return DEFAULT_PODCAST_COVER

    for t in selected_topics:
        articles = t.get("articles") or ([t] if isinstance(t, dict) and ("title" in t or "image_url" in t) else [])
        for a in articles:
            if isinstance(a, dict):
                img = a.get("image_url")
                if img and isinstance(img, str) and img.startswith("http"):
                    return make_image_square(img)
                content = a.get("content") or ""
                match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if match and match.group(1).startswith("http"):
                    return make_image_square(match.group(1))

        if isinstance(t, dict):
            img = t.get("image_url")
            if img and isinstance(img, str) and img.startswith("http"):
                return make_image_square(img)

    return DEFAULT_PODCAST_COVER

def sanitize_base_url(url: str) -> str:
    b_url = (url or settings.base_url or "").rstrip("/")
    if b_url.startswith("http://") and not b_url.startswith("http://127.0.0.1") and not b_url.startswith("http://localhost"):
        b_url = b_url.replace("http://", "https://")
    return b_url

def get_mp3_duration_seconds(filepath: Path) -> int:
    if not filepath.exists():
        return 180
    file_size = filepath.stat().st_size
    # Voxtral TTS is 48 kbps, which equates to 6000 bytes/second
    duration = int(file_size / 6000)
    return max(5, duration)

def format_duration_rss(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def clean_script_text_content(val) -> str:
    if not val:
        return ""
    if isinstance(val, dict):
        return str(val.get("content") or val.get("texte") or val.get("text") or " ".join(str(v) for v in val.values()))
    if isinstance(val, list):
        return "\n".join(clean_script_text_content(x) for x in val)
    s = str(val).strip()
    if s.startswith("{") and s.endswith("}"):
        try:
            import ast
            d = ast.literal_eval(s)
            if isinstance(d, dict):
                return str(d.get("content") or d.get("texte") or d.get("text") or " ".join(str(v) for v in d.values()))
        except Exception:
            pass
    s = re.sub(r"^\{['\"](?:intonation|emotion)['\"]\s*:\s*['\"][^'\"]*['\"]\s*,\s*['\"](?:texte|text|content)['\"]\s*:\s*['\"]", "", s)
    s = re.sub(r"['\"]\}\s*$", "", s)
    s = re.sub(r"\[Marie\s*-\s*[^\]]+\]", "", s)
    s = re.sub(r"\[[^\]]+\]", "", s)
    return s.strip()

async def generate_podcast_show(
    topics_count: int = 5,
    max_days: int = 7,
    only_verified: bool = False,
    tone: str = "journal_matinal",
    voice_key: str = "Marie - Dynamic",
    theme: str = None,
    api_key: str = None,
    mistral_key: str = "",
    gemini_key: str = "",
    provider: str = None,
    fallback_enabled: bool = True,
    mistral_model: str = None,
    gemini_model: str = None,
    base_url: str = None,
    log_callback = None
) -> dict:
    """
    Generates a full podcast episode with streaming logs callback support.
    """
    async def emit_log(msg: str):
        now_str = datetime.now(ZoneInfo("Europe/Paris")).strftime("%H:%M:%S")
        full_msg = f"[{now_str}] {msg}"
        print(f"[Podcast Log] {full_msg}")
        if log_callback:
            try:
                if asyncio.iscoroutinefunction(log_callback):
                    await log_callback(full_msg)
                else:
                    log_callback(full_msg)
            except Exception as e:
                print(f"[Log Callback Error]: {e}")

    await emit_log("🚀 Initialisation du générateur de podcast radio Vos...")

    m_key = mistral_key or api_key or settings.mistral_api_key
    g_key = gemini_key or settings.gemini_api_key
    
    if not m_key and not g_key:
        raise ValueError("Clé API Mistral ou Gemini requise pour générer l'émission de podcast.")

    prov = (provider or settings.synthesis_provider or ("mistral" if m_key else "gemini")).lower()
    m_model = mistral_model or settings.mistral_podcast_model or settings.mistral_model or "mistral-large-latest"
    g_model = gemini_model or settings.gemini_podcast_model or settings.gemini_model or "gemini-1.5-pro"

    await emit_log(f"🔑 Fournisseur d'IA actif : {prov.upper()} (Modèle : {m_model if prov == 'mistral' else g_model})")

    b_url = sanitize_base_url(base_url)
    feed_token = get_or_create_podcast_feed_token()
    token_param = f"?token={feed_token}" if feed_token else ""

    date_fr = get_french_date_str()
    await emit_log(f"📅 Date dynamique injectée dans le prompt : {date_fr}")
    await emit_log("📥 Analyse des clusters d'actualités récentes dans SQLite...")

    # Fetch recent clusters from SQLite (off-thread)
    try:
        clusters = await asyncio.to_thread(compute_article_clusters, 0.91)
    except Exception as e_clus:
        await emit_log(f"⚠️ Note sur les clusters vectoriels : {e_clus}")
        clusters = []

    # Fallback to direct recent articles query if no vector clusters exist
    if not clusters:
        await emit_log("ℹ️ Aucun cluster vectoriel pré-calculé. Récupération directe des articles récents en base...")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.title, a.content, a.url, a.published_date, a.image_url, f.title as feed_title, f.category
            FROM articles a
            JOIN feeds f ON a.feed_id = f.id
            ORDER BY a.published_date DESC
            LIMIT 30
        """)
        art_rows = cursor.fetchall()
        conn.close()

        if not art_rows:
            raise ValueError("Aucun article trouvé dans votre base. Veuillez ajouter des flux RSS.")

        cat_map = {}
        for r in art_rows:
            cat = r["category"] or "Général"
            if cat not in cat_map:
                cat_map[cat] = []
            cat_map[cat].append({
                "id": r["id"],
                "title": r["title"],
                "content": r["content"] or r["title"],
                "url": r["url"],
                "published_date": r["published_date"],
                "image_url": r["image_url"],
                "feed_title": r["feed_title"]
            })

        clusters = []
        for cat_name, items in cat_map.items():
            distinct_feeds = len(set(x["feed_title"] for x in items))
            clusters.append({
                "topic_title": f"{items[0]['title']}",
                "category": cat_name,
                "distinct_feed_count": distinct_feeds,
                "articles": items
            })

    filtered_clusters = []
    cutoff_date = datetime.now() - timedelta(days=max_days)

    for c in clusters:
        if only_verified and c.get("distinct_feed_count", 1) < 3:
            continue

    for c in clusters:
        if only_verified and c.get("distinct_feed_count", 1) < 3:
            continue

        if theme and theme.strip():
            clean_t = theme.strip().lower()
            theme_keywords = [clean_t]
            if clean_t in ["ia", "ai", "intelligence artificielle"]:
                theme_keywords.extend(["ia", "ai", "intelligence artificielle", "artificial intelligence", "tech", "technologie", "algorithme", "robot", "données"])
            
            match_found = False
            cat = (c.get("category") or "").lower()
            title = (c.get("topic_title") or "").lower()
            
            for kw in theme_keywords:
                if kw in cat or kw in title:
                    match_found = True
                    break
                for a in c.get("articles", []):
                    art_title = (a.get("title") or "").lower()
                    art_content = (a.get("content") or a.get("description") or "").lower()
                    if kw in art_title or kw in art_content:
                        match_found = True
                        break
                if match_found:
                    break

            if not match_found:
                continue

        first_art = c["articles"][0]
        pub_str = first_art.get("published_date") or ""
        try:
            art_date = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
            if art_date >= cutoff_date:
                filtered_clusters.append(c)
        except Exception:
            filtered_clusters.append(c)

    if not filtered_clusters:
        filtered_clusters = clusters[:topics_count]

    selected_topics = filtered_clusters[:topics_count]
    actual_topics_count = len(selected_topics)
    cover_image_url = extract_cover_image(selected_topics)

    await emit_log(f"📊 {actual_topics_count} sujet(s) sélectionné(s) pour l'édition :")
    for idx, top in enumerate(selected_topics, 1):
        sources = ", ".join(list(set(a["feed_title"] for a in top["articles"])))
        await emit_log(f"  • Sujet #{idx} : '{top['topic_title']}' ({top.get('distinct_feed_count', 1)} sources: {sources})")

    source_articles = []
    seen_urls = set()
    for t in selected_topics:
        for a in t.get("articles", []):
            u = a.get("url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                source_articles.append({
                    "title": a.get("title") or "Article",
                    "url": u,
                    "feed": a.get("feed_title") or "Source"
                })

    topics_summary_list = []
    for idx, topic in enumerate(selected_topics, 1):
        sources = ", ".join(list(set(a["feed_title"] for a in topic["articles"])))
        main_art = topic["articles"][0]
        snippet = (main_art.get("content") or main_art.get("title") or "")[:500]
        topics_summary_list.append(
            f"Sujet #{idx}: {topic['topic_title']}\nSources recoupées ({topic.get('distinct_feed_count', 1)}): {sources}\nRésumé/Extraits: {snippet}"
        )

    all_topics_text = "\n\n".join(topics_summary_list)

    tones_prompts = {
        "journal_matinal": "Un ton dynamique, chaleureux, professionnel et fluide de matinale radio. Présente les faits avec clarté et rythme.",
        "analyse_profonde": "Un ton posé, analytique, recherché et pédagogique de grand reportage. Explique le 'pourquoi' et les enjeux.",
        "express": "Un format ultra-rapide, incisif et percutant de 2 minutes. Va droit à l'essentiel sans fioritures.",
        "debat": "Un style vivant avec des nuances et du recul sur chaque actualité."
    }
    tone_instruction = tones_prompts.get(tone, tones_prompts["journal_matinal"])
    
    theme_note = ""
    if theme and theme.strip():
        theme_note = f"\n\nTHÈME OBLIGATOIRE DU PODCAST : L'utilisateur exige que l'émission soit axée sur le thème '{theme}'. Tu dois traiter chaque sujet sous l'angle de '{theme}' et faire ressortir cet enjeu thématique dans tes analyses !"

    is_dynamic_voice = "dynamic" in (voice_key or "").lower() or "auto" in (voice_key or "").lower()
    
    emotion_instruction = ""
    if is_dynamic_voice:
        emotion_instruction = (
            "\n\n8. MULTI-ÉMOTIONS DYNAMIQUE : Pour chaque sujet, spécifie l'intonation dans le champ 'emotion'.\n"
            "Valeurs autorisées : 'Marie - Neutral', 'Marie - Excited', 'Marie - Angry', 'Marie - Sad', 'Marie - Curious', 'Marie - Happy'."
        )

    custom_system_prompt = get_app_setting("podcast_system_prompt", DEFAULT_SYSTEM_PROMPT)
    if not custom_system_prompt or not custom_system_prompt.strip():
        custom_system_prompt = DEFAULT_SYSTEM_PROMPT

    system_prompt = (
        f"{custom_system_prompt.strip()}\n\n"
        f"Aujourd'hui nous sommes le {date_fr}.\n"
        f"Style d'antenne souhaité : {tone_instruction}"
        f"{theme_note}"
        f"{emotion_instruction}"
    )

    await emit_log("📜 Prompt Système assemblé avec les consignes strictes (Pas d'heure, pas de sommaire).")

    user_prompt = f"""
    Voici les actualités sélectionnées aujourd'hui ({date_fr}) :

    {all_topics_text}

    CONSIGNE NOMBRE DE SUJETS : Tu dois rédiger EXCLUSIVEMENT ET EXACTEMENT {topics_count} sujet(s) distincts dans le tableau 'script_topics' (de topic_index 1 à {topics_count}).

    Rédige l'émission sous forme d'un objet JSON strict avec la structure suivante :
    {{
      "show_title": "Titre clair et percutant résumant les sujets phares de l'édition",
      "key_points": [
        "1 phrase de résumé du sujet #1"
      ],
      "script_topics": [
        {{
          "topic_index": 1,
          "topic_title": "Titre du sujet 1",
          "emotion": "Marie - Neutral",
          "content": "Texte intégral du premier sujet..."
        }},
        {{
          "topic_index": {topics_count},
          "topic_title": "Titre du sujet {topics_count}",
          "emotion": "Marie - Curious",
          "content": "Texte intégral du dernier sujet..."
        }}
      ]
    }}
    Réponds uniquement au format JSON valide.
    """

    await emit_log(f"🤖 Envoi de la requête de rédaction au LLM ({prov.capitalize()} - {m_model if prov == 'mistral' else g_model})...")

    async def call_mistral():
        if not m_key:
            raise ValueError("Clé API Mistral manquante. Renseignez votre clé API Mistral dans les Paramètres (icône ⚙️).")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {m_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": m_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
            if res.status_code != 200:
                err_text = res.text
                try:
                    err_json = res.json()
                    err_text = err_json.get("message") or err_json.get("detail") or res.text
                except Exception:
                    pass
                raise ValueError(f"Erreur API Mistral ({res.status_code}) : {err_text}")
            
            res_data = res.json()
            raw_content = res_data["choices"][0]["message"]["content"]
            cleaned = re.sub(r"^```json\s*", "", raw_content.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            return json.loads(cleaned), res_data.get("usage", {}).get("total_tokens", 0)

    async def call_gemini():
        if not g_key:
            raise ValueError("Clé API Gemini manquante. Renseignez votre clé API Gemini dans les Paramètres (icône ⚙️).")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={g_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "system_instruction": {
                        "parts": [{"text": system_prompt}]
                    },
                    "contents": [{
                        "parts": [{"text": user_prompt}]
                    }],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                },
                timeout=60.0
            )
            if res.status_code != 200:
                err_text = res.text
                try:
                    err_json = res.json()
                    err_text = err_json.get("error", {}).get("message") or res.text
                except Exception:
                    pass
                raise ValueError(f"Erreur API Gemini ({res.status_code}) : {err_text}")
            
            res_data = res.json()
            raw_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = re.sub(r"^```json\s*", "", raw_content.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            return json.loads(cleaned), res_data.get("usageMetadata", {}).get("totalTokenCount", 0)

    async def try_provider(p_name: str):
        if p_name == "mistral":
            return await call_mistral()
        elif p_name == "gemini":
            return await call_gemini()
        else:
            raise ValueError(f"Fournisseur IA inconnu ({p_name}).")

    errors = []
    try:
        script_data, llm_tokens = await try_provider(prov)
    except Exception as e:
        err_msg = f"Erreur {prov} : {e}"
        await emit_log(f"⚠️ {err_msg}")
        errors.append(err_msg)
        if fallback_enabled:
            fallback_provider = "gemini" if prov == "mistral" else "mistral"
            has_fallback_key = bool(g_key) if fallback_provider == "gemini" else bool(m_key)
            if has_fallback_key:
                await emit_log(f"🔄 Secours automatique activé : tentative avec {fallback_provider}...")
                try:
                    script_data, llm_tokens = await try_provider(fallback_provider)
                except Exception as e2:
                    err_msg2 = f"Erreur fallback {fallback_provider} : {e2}"
                    errors.append(err_msg2)
                    raise ValueError(" ; ".join(errors))
            else:
                raise ValueError(f"{err_msg}. Pour activer le secours automatique, renseignez votre clé API de secours dans les Paramètres.")
        else:
            raise ValueError(err_msg)

    if isinstance(script_data, str):
        try:
            script_data = json.loads(script_data)
        except Exception:
            script_data = {"script": script_data}

    if not isinstance(script_data, dict):
        script_data = {"script": str(script_data)}

    await emit_log(f"✅ Réponse LLM reçue avec succès ({llm_tokens} tokens consommés).")

    raw_title = script_data.get("show_title") or f"Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"
    show_title = clean_podcast_title(raw_title)
    await emit_log(f"📌 Titre retenu pour l'émission : '{show_title}'")

    key_points = script_data.get("key_points") or []
    if isinstance(key_points, str):
        key_points = [key_points]
    elif isinstance(key_points, dict):
        key_points = [f"{k}: {v}" for k, v in key_points.items()]
    elif not isinstance(key_points, list):
        key_points = [str(key_points)]

    script_topics = script_data.get("script_topics") or []
    if not isinstance(script_topics, list) or len(script_topics) == 0:
        raw_script = script_data.get("script", "")
        if isinstance(raw_script, dict):
            raw_script = "\n\n".join([f"{k}: {v}" for k, v in raw_script.items()])
        elif isinstance(raw_script, list):
            raw_script = "\n\n".join([str(x) for x in raw_script])
        segments = split_script_into_emotion_segments(str(raw_script), default_voice=voice_key)
        script_topics = [
            {
                "topic_index": i + 1,
                "topic_title": f"Sujet #{i + 1}",
                "emotion": seg_voice,
                "content": seg_text
            }
            for i, (seg_voice, seg_text) in enumerate(segments)
        ]

    await emit_log(f"📑 {len(script_topics)} bloc(s) de sujet(s) structuré(s) prêt(s) pour la synthèse vocal Voxtral :")
    for idx, top in enumerate(script_topics, 1):
        top_title = top.get("topic_title") or f"Sujet #{idx}"
        top_emotion = top.get("emotion") or voice_key
        top_content = clean_script_text_content(top.get("content") or top.get("texte") or top.get("text") or top)
        await emit_log(f"  • Sujet [{idx}/{len(script_topics)}] : '{top_title}' | Intonation: [{top_emotion}] | Longueur: {len(top_content)} car.")

    audio_chunks = []
    full_script_parts = []
    jingle_filename = get_app_setting("podcast_jingle_filename", "whoosh_default.mp3")

    for idx, top in enumerate(script_topics, 1):
        top_title = top.get("topic_title") or f"Sujet #{idx}"
        top_emotion = top.get("emotion") or voice_key
        top_content = clean_script_text_content(top.get("content") or top.get("texte") or top.get("text") or top)
        clean_text = sanitize_script_for_tts(top_content)
        clean_text = sanitize_text_for_speech(clean_text)
        
        if not clean_text:
            continue

        full_script_parts.append(f"[{top_emotion}]\n{top_content}")

        await emit_log(f"🎙️ [Sujet {idx}/{len(script_topics)}] Génération audio Voxtral (Voix: [{top_emotion}])...")
        t_start = time.time()
        
        try:
            chunk_bytes = await generate_audio_bytes_for_voice(clean_text, voice_key=top_emotion, api_key=m_key)
            elapsed = round(time.time() - t_start, 1)
            audio_chunks.append(chunk_bytes)
            await emit_log(f"  ✓ Sujet {idx}/{len(script_topics)} synthétisé en {elapsed}s (Taille audio: {len(chunk_bytes)} octets)")
            
            if idx < len(script_topics):
                await emit_log(f"  🎵 Woosh de transition inséré entre le Sujet {idx} et le Sujet {idx + 1} ({jingle_filename})")
        except Exception as e:
            await emit_log(f"  ⚠️ Erreur TTS Sujet {idx} : {e}")

    if not audio_chunks:
        fallback_text = sanitize_text_for_speech(all_topics_text[:1000])
        audio_bytes = await generate_audio_bytes_for_voice(fallback_text, voice_key=voice_key, api_key=m_key)
        audio_chunks = [audio_bytes]

    await emit_log(f"🎧 Assemblage des {len(audio_chunks)} blocs audio MP3 avec le jingle '{jingle_filename}'...")
    audio_filename = combine_audio_chunks(audio_chunks)

    audio_url = f"{b_url}/api/audio/stream/{audio_filename}{token_param}"
    full_script = sanitize_script_for_tts("\n\n".join(full_script_parts))

    filepath = AUDIO_DIR / audio_filename
    duration_secs = get_mp3_duration_seconds(filepath)
    dur_formatted = format_duration_rss(duration_secs)
    file_size = filepath.stat().st_size if filepath.exists() else 0

    await emit_log(f"💾 Fichier audio généré : {audio_filename} (Durée : {dur_formatted}, Taille : {file_size} octets)")

    key_points_json = json.dumps(key_points, ensure_ascii=False)
    sources_json = json.dumps(source_articles, ensure_ascii=False)
    
    tts_chars = len(full_script)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://127.0.0.1:8000/api/stats/tokens",
                json={"llm_tokens": llm_tokens, "tts_chars": tts_chars},
                timeout=5.0
            )
    except Exception as e:
        print(f"[Stats Tracking Note]: {e}")

    # Save into SQLite database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO podcasts (title, script, audio_filename, audio_url, image_url, topics_count, max_days, only_verified, voice, key_points_json, sources_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (show_title, full_script, audio_filename, audio_url, cover_image_url, actual_topics_count, max_days, 1 if only_verified else 0, voice_key, key_points_json, sources_json))
    
    podcast_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await emit_log(f"🎉 Émission ID #{podcast_id} enregistrée en BDD et immédiatement disponible sur AntennaPod !")

    return {
        "id": podcast_id,
        "title": show_title,
        "script": full_script,
        "audio_filename": audio_filename,
        "audio_url": audio_url,
        "image_url": cover_image_url,
        "topics_count": actual_topics_count,
        "max_days": max_days,
        "only_verified": only_verified,
        "voice": voice_key,
        "theme": theme,
        "key_points": key_points,
        "sources": source_articles,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_podcast_history(base_url: str = None) -> list:
    b_url = sanitize_base_url(base_url)
    feed_token = get_or_create_podcast_feed_token()
    token_param = f"?token={feed_token}" if feed_token else ""

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, script, audio_filename, audio_url, image_url, topics_count, max_days, only_verified, voice, key_points_json, sources_json, created_at
        FROM podcasts
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    podcasts = []
    for r in rows:
        fn = r["audio_filename"]
        u = f"{b_url}/api/audio/stream/{fn}{token_param}" if fn else r["audio_url"]
        
        kp = []
        if r["key_points_json"]:
            try:
                kp = json.loads(r["key_points_json"])
            except Exception:
                pass

        srcs = []
        if r["sources_json"]:
            try:
                srcs = json.loads(r["sources_json"])
            except Exception:
                pass

        podcasts.append({
            "id": r["id"],
            "title": r["title"],
            "script": r["script"],
            "audio_filename": fn,
            "audio_url": u,
            "image_url": r["image_url"] or DEFAULT_PODCAST_COVER,
            "topics_count": r["topics_count"],
            "max_days": r["max_days"],
            "only_verified": bool(r["only_verified"]),
            "voice": r["voice"],
            "key_points": kp,
            "sources": srcs,
            "created_at": r["created_at"]
        })
    return podcasts

def generate_podcast_rss_feed(base_url: str = None, token: str = None) -> str:
    b_url = sanitize_base_url(base_url)
    feed_token = token or get_or_create_podcast_feed_token()
    token_param = f"?token={feed_token}" if feed_token else ""

    parsed = urlparse(b_url)
    domain_host = parsed.netloc.split(":")[0] if parsed.netloc else ""
    
    if domain_host and domain_host not in ("127.0.0.1", "localhost", ""):
        channel_title = f"Vos - Revue de Presse ({domain_host})"
        author_name = domain_host
    else:
        channel_title = "Vos - Revues de Presse Audio"
        author_name = "Vos Studio"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, script, audio_filename, audio_url, image_url, topics_count, voice, key_points_json, sources_json, created_at
        FROM podcasts
        ORDER BY created_at DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()

    channel_cover = DEFAULT_PODCAST_COVER
    if rows and rows[0]["image_url"]:
        channel_cover = rows[0]["image_url"]

    items_xml = []
    for r in rows:
        fn = r["audio_filename"]
        audio_stream_url = f"{b_url}/api/audio/stream/{fn}{token_param}" if fn else r["audio_url"]
        
        filepath = AUDIO_DIR / fn if fn else Path()
        file_size = filepath.stat().st_size if filepath.exists() else 1000000
        dur_seconds = get_mp3_duration_seconds(filepath)
        dur_formatted = format_duration_rss(dur_seconds)

        ep_cover = r["image_url"] or channel_cover

        try:
            dt = datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S")
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
        except Exception:
            pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")

        kp = []
        if r["key_points_json"]:
            try:
                kp = json.loads(r["key_points_json"])
            except Exception:
                pass

        srcs = []
        if r["sources_json"]:
            try:
                srcs = json.loads(r["sources_json"])
            except Exception:
                pass

        html_body = format_script_html(r["script"])
        
        extras_html = []
        if kp:
            extras_html.append("<h4 style=\"color:#2563eb;margin-top:16px;margin-bottom:6px;\">💡 Points clés :</h4><ul>")
            for point in kp:
                extras_html.append(f"<li style=\"margin-bottom:4px;\">{xml_escape(str(point))}</li>")
            extras_html.append("</ul>")

        if srcs:
            extras_html.append("<h4 style=\"color:#2563eb;margin-top:16px;margin-bottom:6px;\">🔗 Sources de l'édition :</h4><ul>")
            for s in srcs:
                t_title = xml_escape(s.get("title") or "Article")
                t_url = xml_escape(s.get("url") or "#")
                t_feed = xml_escape(s.get("feed") or "Media")
                extras_html.append(f"<li style=\"margin-bottom:4px;\"><a href=\"{t_url}\" target=\"_blank\">{t_title}</a> <small style=\"color:#6b7280;\">({t_feed})</small></li>")
            extras_html.append("</ul>")

        full_description_html = html_body + "\n" + "\n".join(extras_html)

        item = f"""
    <item>
      <title>{xml_escape(r['title'])}</title>
      <link>{xml_escape(audio_stream_url)}</link>
      <guid isPermaLink="false">vos-podcast-{r['id']}</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{full_description_html}]]></description>
      <enclosure url="{xml_escape(audio_stream_url)}" length="{file_size}" type="audio/mpeg"/>
      <itunes:duration>{dur_formatted}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:image href="{xml_escape(ep_cover)}"/>
    </item>"""
        items_xml.append(item)

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{xml_escape(channel_title)}</title>
    <link>{xml_escape(b_url)}</link>
    <language>fr-fr</language>
    <copyright>Vos Reader</copyright>
    <itunes:author>{xml_escape(author_name)}</itunes:author>
    <itunes:summary>Flux RSS privé et personnalisé de votre revue de presse audio rédigée et enregistrée automatiquement.</itunes:summary>
    <description>Revue de presse quotidienne générée automatiquement par Vos.</description>
    <itunes:owner>
      <itunes:name>{xml_escape(author_name)}</itunes:name>
      <itunes:email>podcast@{domain_host or 'vos.app'}</itunes:email>
    </itunes:owner>
    <itunes:image href="{xml_escape(channel_cover)}"/>
    <itunes:category text="News">
      <itunes:category text="Daily News"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    {"".join(items_xml)}
  </channel>
</rss>"""
    return feed_xml
