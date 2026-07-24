import json
import httpx
import re
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape
from app.database import get_db_connection
from app.config import settings
from app.services.clustering import compute_article_clusters
from app.services.audio import generate_podcast_audio, generate_audio_bytes_for_voice, combine_audio_chunks, AUDIO_DIR

DEFAULT_PODCAST_COVER = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

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
    """
    for t in selected_topics:
        img = t.get("image_url")
        if img and img.startswith("http"):
            return img
        content = t.get("content") or ""
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if match and match.group(1).startswith("http"):
            return match.group(1)
    return DEFAULT_PODCAST_COVER

async def generate_podcast_show(
    topics_count: int = 5,
    max_days: int = 7,
    only_verified: bool = False,
    tone: str = "journal_matinal",
    voice_key: str = "Marie - Dynamic",
    theme: str = None,
    api_key: str = None,
    base_url: str = None
) -> dict:
    """
    1. Selects top news topics from SQLite
    2. Writes a script with Mistral AI
    3. Synthesizes full multi-voice audio with Voxtral TTS
    4. Saves into podcasts SQLite database table
    """
    key = api_key or settings.mistral_api_key
    if not key:
        raise ValueError("Clé API Mistral requise pour générer l'émission de podcast.")

    b_url = (base_url or settings.base_url).rstrip("/")
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
        "Tu es le producteur et présentateur vedette du podcast d'actualités 'Vos Revue de Presse'."
        f"Tu dois rédiger un script d'émission de radio captivant{theme_note} en français, entièrement rédigé pour être lu à haute voix par une synthèse vocale. "
        f"Style souhaité : {tone_instruction}\n"
        "Règles d'écriture :\n"
        "- Commence par une introduction accueillante et accrocheuse ('Bonjour et bienvenue dans votre revue de presse Vos...').\n"
        "- Enchaîne naturellement les sujets avec de belles transitions radio.\n"
        "- Cite les médias sources de façon fluide ('Selon Le Temps...', 'D'après une enquête de Mediapart...').\n"
        "- Termine par une conclusion synthétique et chaleureuse.\n"
        "- Rédige le texte en français fluide, sans annotations de mise en scène (pas de [Musique], [Rires] ou d'emojis)."
    )

    user_prompt = f"""
    Voici les {actual_topics_count} actualités majeures sélectionnées aujourd'hui :

    {all_topics_text}

    Génère le script complet du podcast au format JSON suivant :
    {{
      "show_title": "Titre d'émission accrocheur incluant les mots-clés principaux et (Revue de presse)",
      "script": "Script radio intégral rédigé en français..."
    }}
    Réponds uniquement au format JSON valide.
    """

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=45.0
        )

        if res.status_code != 200:
            raise ValueError(f"Erreur génération script Mistral: {res.text}")

        script_data = res.json()["choices"][0]["message"]["content"]
        try:
            script_data = json.loads(script_data)
        except Exception:
            script_data = {
                "show_title": f"Revue de presse du {datetime.now().strftime('%d/%m/%Y')}",
                "script": script_data
            }

        show_title = script_data.get("show_title") or f"Revue de presse du {datetime.now().strftime('%d/%m/%Y')}"
        if "(Revue de presse)" not in show_title and "Revue de presse" not in show_title:
            show_title = f"{show_title} (Revue de presse)"

        full_script = script_data.get("script", "")
        audio_filename = await generate_podcast_audio(full_script, voice_key=voice_key, api_key=key)

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

def generate_podcast_rss_feed(base_url: str = None, token: str = None) -> str:
    """
    Generates a 100% valid RSS 2.0 XML podcast feed with iTunes / AntennaPod / Spotify / Apple Podcasts metadata.
    Includes episode image, HTML description with clickable sources, and audio enclosure length.
    """
    b_url = (base_url or settings.base_url).rstrip("/")
    feed_token = token or get_or_create_podcast_feed_token()
    token_param = f"?token={feed_token}" if feed_token else ""

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
        img_url = r["image_url"] or DEFAULT_PODCAST_COVER
        
        audio_filename = r["audio_filename"]
        audio_url = f"{b_url}/api/audio/stream/{audio_filename}{token_param}"

        filepath = AUDIO_DIR / audio_filename
        file_size = filepath.stat().st_size if filepath.exists() else 2000000

        try:
            dt = datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S")
            pub_date_str = dt.strftime("%a, %d %b %Y %H:%M:%S +0200")
        except Exception:
            pub_date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")

        desc_html = f"<![CDATA[<p>{script[:500]}...</p><h3>Transcription &amp; Émission complète :</h3><p>{script}</p>]]>"

        item_str = f"""    <item>
      <title>{title}</title>
      <link>{audio_url}</link>
      <description>{desc_html}</description>
      <enclosure url="{audio_url}" length="{file_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">vos-podcast-{r['id']}</guid>
      <pubDate>{pub_date_str}</pubDate>
      <itunes:image href="{img_url}"/>
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
    <title>Vos - Revues de Presse Audio</title>
    <link>{feed_url}</link>
    <language>fr</language>
    <copyright>Vos AI Reader</copyright>
    <itunes:subtitle>Revues de presse quotidiennes scénarisées et lues par Voxtral</itunes:subtitle>
    <itunes:author>Vos Studio</itunes:author>
    <itunes:summary>Vos génère automatiquement votre revue de presse personnalisée à partir d'actualités croisées et lue par la voix de Marie.</itunes:summary>
    <description>Revue de presse quotidienne personnalisée et croisée.</description>
    <itunes:owner>
      <itunes:name>Vos App</itunes:name>
      <itunes:email>podcast@vos-app.local</itunes:email>
    </itunes:owner>
    <itunes:image href="{DEFAULT_PODCAST_COVER}"/>
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
    b_url = (base_url or settings.base_url).rstrip("/")
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
