import json
import httpx
import re
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse
from app.database import get_db_connection
from app.config import settings
from app.services.clustering import compute_article_clusters
from app.services.audio import generate_podcast_audio, generate_audio_bytes_for_voice, combine_audio_chunks, AUDIO_DIR

DEFAULT_PODCAST_COVER = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

def format_script_html(script_text: str) -> str:
    """
    Formats the raw podcast transcript into clean, readable HTML paragraphs and subheadings for AntennaPod.
    """
    if not script_text:
        return "<p>Aucune transcription disponible.</p>"
    
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

def sanitize_script_for_tts(text: str) -> str:
    if not text:
        return ""
    # 1. Remove bracketed text like [Votre Nom], [Nom du présentateur], [Musique], [Rires], etc.
    text = re.sub(r"\[([^\]]+)\]", "", text)
    # 2. Remove parenthetical stage directions like (musique dynamique)
    text = re.sub(r"\((musique|rires|pause|transition|jingle|sourire|silence)[^\)]*\)", "", text, flags=re.IGNORECASE)
    # 3. Clean up repetitive intro phrases
    text = re.sub(r"revue\s+de\s+presse\s+Vos\s+Revue\s+de\s+Presse", "revue de presse Vos", text, flags=re.IGNORECASE)
    text = re.sub(r"revue\s+de\s+presse\s+Vos\s+Revue\s+de\s+presse", "revue de presse Vos", text, flags=re.IGNORECASE)
    # 4. Normalize spaces and floating punctuation
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,\.\?!;:])", r"\1", text)
    return text.strip()

def clean_podcast_title(raw_title: str) -> str:
    if not raw_title:
        return f"Vos : Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"
    
    t = raw_title.strip()
    t = t.strip('"\'')
    # Clean redundant prefixes/suffixes
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
    """
    Extracts the best article image URL from selected topics for AntennaPod / iTunes episode cover.
    Iterates over articles in topics clusters to find an authentic article image URL.
    """
    if not selected_topics:
        return DEFAULT_PODCAST_COVER

    for t in selected_topics:
        # Check if t is a cluster dictionary containing an "articles" list
        articles = t.get("articles") or ([t] if isinstance(t, dict) and ("title" in t or "image_url" in t) else [])
        for a in articles:
            if isinstance(a, dict):
                img = a.get("image_url")
                if img and isinstance(img, str) and img.startswith("http"):
                    return img
                content = a.get("content") or ""
                match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if match and match.group(1).startswith("http"):
                    return match.group(1)

        # Direct check if t itself has an image_url
        if isinstance(t, dict):
            img = t.get("image_url")
            if img and isinstance(img, str) and img.startswith("http"):
                return img

    return DEFAULT_PODCAST_COVER

async def generate_podcast_show(
    topics_count: int = 5,
    max_days: int = 7,
    only_verified: bool = False,
    tone: str = "journal_matinal",
    voice_key: str = "Marie - Dynamic",
    theme: str = None,
    api_key: str = None, # kept for retrocompatibility
    mistral_key: str = "",
    gemini_key: str = "",
    provider: str = None,
    fallback_enabled: bool = True,
    mistral_model: str = None,
    gemini_model: str = None,
    base_url: str = None
) -> dict:
    """
    1. Selects top news topics from SQLite
    2. Writes a script with Mistral AI or Gemini
    3. Synthesizes full multi-voice audio with Voxtral TTS
    4. Saves into podcasts SQLite database table
    """
    m_key = mistral_key or api_key or settings.mistral_api_key
    g_key = gemini_key or settings.gemini_api_key
    
    if not m_key and not g_key:
        raise ValueError("Clé API Mistral ou Gemini requise pour générer l'émission de podcast.")

    prov = (provider or settings.synthesis_provider or ("mistral" if m_key else "gemini")).lower()
    m_model = mistral_model or settings.mistral_podcast_model or settings.mistral_model or "mistral-large-latest"
    g_model = gemini_model or settings.gemini_podcast_model or settings.gemini_model or "gemini-1.5-pro"

    b_url = sanitize_base_url(base_url)
    feed_token = get_or_create_podcast_feed_token()
    token_param = f"?token={feed_token}" if feed_token else ""

    # Fetch recent clusters from SQLite
    clusters = compute_article_clusters(similarity_threshold=0.91)
    if not clusters:
        raise ValueError("Aucun article disponible pour composer le podcast.")

    filtered_clusters = []
    cutoff_date = datetime.now() - timedelta(days=max_days)

    for c in clusters:
        if only_verified and c.get("distinct_feed_count", 1) < 3:
            continue

        if theme and theme.strip():
            clean_t = theme.strip().lower()
            cat = (c.get("category") or "").lower()
            title = (c.get("topic_title") or "").lower()
            if clean_t not in cat and clean_t not in title:
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

    # Prepare prompt text for Mistral
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

    theme_note = f" (Focus thématique : {theme})" if theme and theme.strip() else ""

    system_prompt = (
        "Tu es un journaliste radio chevronné et le présentateur principal de l'émission d'actualités 'Vos'. "
        f"Ton rôle est de rédiger un script d'émission d'actualités radio d'une qualité professionnelle irréprochable{theme_note}.\n"
        f"Style d'antenne souhaité : {tone_instruction}\n\n"
        "CONSIGNES STRICTES POUR LA SYNTHÈSE VOCALE (TTS) :\n"
        "1. INTERDICTION ABSOLUE des crochets et des textes de remplacement. Ne jamais écrire [Votre Nom], [Nom du présentateur], [Musique], [Rires], etc. Le texte sera directement lu à voix haute par un synthétiseur vocal.\n"
        "2. N'utilise aucun nom de présentateur fictif ou générique entre crochets. Si tu te présentes en intro, dis simplement 'Bonjour et bienvenue dans Vos, votre revue de presse quotidienne.' sans mentionner de nom propre d'animateur.\n"
        "3. Ne répète jamais inutilement le nom de l'émission (Évite absolument 'votre revue de presse Vos Revue de Presse').\n"
        "4. Rédige un français naturel, captivant, vivant et dynamique, fluide à la lecture audio.\n"
        "5. Les transitions entre chaque sujet doivent être naturelles et journalistiques (ex: 'Du côté de la technologie...', 'En Europe...', 'Autre fait marquant aujourd'hui...').\n"
        "6. Cite clairement et naturellement les médias sources (ex: 'Selon une enquête du Monde...', 'D'après les informations de TechCrunch...').\n"
        "7. Évite les phrases moralisatrices clichés en conclusion. Reste sobre, professionnel et chaleureux ('Merci d'avoir suivi cette édition de Vos, et à très vite pour la suite de l'actualité.')."
    )

    user_prompt = f"""
    Voici les {actual_topics_count} actualités majeures sélectionnées aujourd'hui :

    {all_topics_text}

    Rédige le script intégral du podcast au format JSON suivant :
    {{
      "show_title": "Titre clair et percutant résumant les sujets phares de l'édition (sans ajouter '(Revue de presse)' au début ou à la fin)",
      "script": "Script radio complet rédigé en français..."
    }}
    Réponds uniquement au format JSON valide.
    """

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
            
            raw_content = res.json()["choices"][0]["message"]["content"]
            cleaned = re.sub(r"^```json\s*", "", raw_content.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            return json.loads(cleaned)

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
            
            raw_content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = re.sub(r"^```json\s*", "", raw_content.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            return json.loads(cleaned)

    async def try_provider(p_name: str):
        if p_name == "mistral":
            return await call_mistral()
        elif p_name == "gemini":
            return await call_gemini()
        else:
            raise ValueError(f"Fournisseur IA inconnu ({p_name}).")

    errors = []
    try:
        script_data = await try_provider(prov)
    except Exception as e:
        err_msg = f"Erreur {prov} : {e}"
        print(f"[Podcast Script Generation Note]: {err_msg}")
        errors.append(err_msg)
        if fallback_enabled:
            fallback_provider = "gemini" if prov == "mistral" else "mistral"
            has_fallback_key = bool(g_key) if fallback_provider == "gemini" else bool(m_key)
            if has_fallback_key:
                print(f"Fallback activé : tentative avec {fallback_provider}...")
                try:
                    script_data = await try_provider(fallback_provider)
                except Exception as e2:
                    err_msg2 = f"Erreur fallback {fallback_provider} : {e2}"
                    print(f"[Podcast Script Fallback Note]: {err_msg2}")
                    errors.append(err_msg2)
                    raise ValueError(" ; ".join(errors))
            else:
                raise ValueError(f"{err_msg}. Pour activer le secours automatique, renseignez votre clé API de secours dans les Paramètres.")
        else:
            raise ValueError(err_msg)

    raw_title = script_data.get("show_title") or f"Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"
    show_title = clean_podcast_title(raw_title)

    raw_script = script_data.get("script", "")
    full_script = sanitize_script_for_tts(raw_script)
    
    # Audio generation is still dependent on voxtral TTS API, we assume it's working with any text.
    audio_filename = await generate_podcast_audio(full_script, voice_key=voice_key, api_key=m_key)

    audio_url = f"{b_url}/api/audio/stream/{audio_filename}{token_param}"

    # Save into SQLite database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO podcasts (title, script, audio_filename, audio_url, image_url, topics_count, max_days, only_verified, voice)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (show_title, full_script, audio_filename, audio_url, cover_image_url, actual_topics_count, max_days, 1 if only_verified else 0, voice_key))
    
    podcast_id = cursor.lastrowid
    conn.commit()
    conn.close()

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
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def sanitize_base_url(url: str) -> str:
    b_url = (url or settings.base_url or "").rstrip("/")
    if b_url.startswith("http://") and not b_url.startswith("http://127.0.0.1") and not b_url.startswith("http://localhost"):
        b_url = b_url.replace("http://", "https://")
    return b_url

def generate_podcast_rss_feed(base_url: str = None, token: str = None) -> str:
    """
    Generates a 100% valid RSS 2.0 XML podcast feed with iTunes / AntennaPod / Spotify / Apple Podcasts metadata.
    Includes domain host in channel title, unique episode cover images, and structured HTML description with key points & full transcript.
    """
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
        SELECT id, title, script, audio_filename, audio_url, image_url, topics_count, voice, created_at
        FROM podcasts
        ORDER BY id DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()

    feed_url = f"{b_url}/api/podcast/feed.xml{token_param}"

    items_xml = []
    for r in rows:
        title = xml_escape(r["title"])
        script = r["script"]
        topics_count = r["topics_count"] or 5
        voice_used = r["voice"] or "Marie"
        
        audio_filename = r["audio_filename"]
        audio_url = f"{b_url}/api/audio/stream/{audio_filename}{token_param}"
        audio_url_escaped = xml_escape(audio_url)
        img_url = r["image_url"] or DEFAULT_PODCAST_COVER
        img_url_escaped = xml_escape(img_url)

        filepath = AUDIO_DIR / audio_filename
        file_size = filepath.stat().st_size if filepath.exists() else 2000000

        try:
            dt = datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S")
            pub_date_str = dt.strftime("%a, %d %b %Y %H:%M:%S +0200")
            display_date = dt.strftime("%d/%m/%Y à %H:%M")
        except Exception:
            pub_date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")
            display_date = datetime.now().strftime("%d/%m/%Y")

        formatted_script_html = format_script_html(script)

        desc_html = f"""<![CDATA[<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;line-height:1.6;color:#333;">
  <p><strong>🎙️ Édition du {display_date}</strong> • <em>{topics_count} sujets d'actualité récapitulés • Voix: {xml_escape(voice_used)}</em></p>
  <hr style="border:0;border-top:1px solid #eee;margin:12px 0;"/>
  <h3 style="color:#2563eb;margin-bottom:8px;">📌 Points clés &amp; Transcription radio :</h3>
  {formatted_script_html}
  <hr style="border:0;border-top:1px solid #eee;margin:16px 0;"/>
  <p style="font-size:12px;color:#666;">Émission générée automatiquement par <strong>Vos AI Reader</strong> sur {xml_escape(domain_host or 'adrienotge.nohost.me')}.</p>
</div>]]>"""

        item_str = f"""    <item>
      <title>{title}</title>
      <link>{audio_url_escaped}</link>
      <description>{desc_html}</description>
      <content:encoded>{desc_html}</content:encoded>
      <enclosure url="{audio_url_escaped}" length="{file_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">vos-podcast-{r['id']}</guid>
      <pubDate>{pub_date_str}</pubDate>
      <itunes:image href="{img_url_escaped}"/>
      <itunes:duration>05:00</itunes:duration>
      <itunes:explicit>no</itunes:explicit>
    </item>"""
        items_xml.append(item_str)

    items_joined = "\n".join(items_xml)

    xml_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
     xmlns:content="http://purl.org/rss/1.0/modules/content/" 
     xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>{xml_escape(channel_title)}</title>
    <link>{xml_escape(feed_url)}</link>
    <language>fr</language>
    <copyright>Vos AI Reader</copyright>
    <itunes:subtitle>Revues de presse quotidiennes scénarisées et lues par Voxtral</itunes:subtitle>
    <itunes:author>{xml_escape(author_name)}</itunes:author>
    <itunes:summary>Vos génère automatiquement votre revue de presse personnalisée à partir d'actualités croisées et lue par la voix de Marie.</itunes:summary>
    <description>Revue de presse quotidienne personnalisée et croisée.</description>
    <itunes:owner>
      <itunes:name>{xml_escape(author_name)}</itunes:name>
      <itunes:email>podcast@{xml_escape(domain_host or 'vos-app.local')}</itunes:email>
    </itunes:owner>
    <itunes:image href="{xml_escape(DEFAULT_PODCAST_COVER)}"/>
    <itunes:category text="News">
      <itunes:category text="Daily News"/>
    </itunes:category>
    <itunes:explicit>no</itunes:explicit>
{items_joined}
  </channel>
</rss>"""
    return xml_feed

def get_podcast_history(base_url: str = None):
    """
    Returns the list of previously generated podcasts with dynamically adapted audio URLs.
    """
    b_url = sanitize_base_url(base_url)
    token = get_or_create_podcast_feed_token()
    token_param = f"?token={token}" if token else ""

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, script, audio_filename, audio_url, image_url, topics_count, max_days, only_verified, voice, created_at
        FROM podcasts
        ORDER BY id DESC
        LIMIT 30
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        fn = item.get("audio_filename")
        if fn:
            item["audio_url"] = f"{b_url}/api/audio/stream/{fn}{token_param}"
        result.append(item)
    return result
