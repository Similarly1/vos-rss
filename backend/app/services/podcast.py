import json
import httpx
import re
from pathlib import Path
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape
from app.database import get_db_connection
from app.config import settings
from app.services.clustering import compute_article_clusters
from app.services.audio import generate_podcast_audio, generate_audio_bytes_for_voice, combine_audio_chunks, AUDIO_DIR

DEFAULT_PODCAST_COVER = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

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
    Generates a full scripted radio podcast show covering N selected topics,
    filtered optional by keyword/theme, and synthesizes audio via Mistral Voxtral.
    """
    key = (api_key or settings.mistral_api_key or "").strip()
    if not key:
        raise ValueError("Clé API Mistral requise pour générer le podcast. Veuillez renseigner votre clé API dans les Paramètres (⚙️).")

    b_url = (base_url or settings.base_url).rstrip("/")
    theme_query = (theme or "").strip().lower()

    # 1. Fetch clusters and filter by max_days, verification, and optional theme/keyword
    raw_clusters = compute_article_clusters(similarity_threshold=0.91)
    
    now = datetime.now()
    cutoff_date = now - timedelta(days=max_days) if max_days > 0 else datetime.min

    filtered_clusters = []
    for c in raw_clusters:
        main_art = c["articles"][0]
        pub_str = main_art.get("published_date")
        
        if pub_str:
            try:
                pub_date = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
                if pub_date < cutoff_date:
                    continue
            except Exception:
                pass

        if only_verified and c.get("distinct_feed_count", 1) < 3:
            continue

        if theme_query:
            match_title = theme_query in c["topic_title"].lower()
            match_content = any(theme_query in (a.get("content") or "").lower() for a in c["articles"])
            match_cat = theme_query in (c.get("category") or "").lower()
            if not (match_title or match_content or match_cat):
                continue

        filtered_clusters.append(c)

    selected_topics = []
    seen_urls = set()

    for c in filtered_clusters:
        main_art = c["articles"][0]
        if main_art["url"] not in seen_urls:
            selected_topics.append({
                "title": c["topic_title"],
                "content": (main_art.get("content") or main_art.get("title"))[:800],
                "image_url": main_art.get("image_url"),
                "sources": [{"feed": a.get("feed_title", "RSS"), "title": a.get("title"), "url": a.get("url")} for a in c["articles"][:3]]
            })
            seen_urls.add(main_art["url"])
            if len(selected_topics) >= topics_count:
                break

    if len(selected_topics) < topics_count:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT a.title, a.content, a.url, a.image_url, f.title as feed_title FROM articles a JOIN feeds f ON a.feed_id = f.id ORDER BY a.id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            if r["url"] not in seen_urls:
                if theme_query:
                    match_t = theme_query in r["title"].lower()
                    match_c = theme_query in (r["content"] or "").lower()
                    if not (match_t or match_c):
                        continue

                selected_topics.append({
                    "title": r["title"],
                    "content": (r["content"] or r["title"])[:800],
                    "image_url": r["image_url"],
                    "sources": [{"feed": r["feed_title"], "title": r["title"], "url": r["url"]}]
                })
                seen_urls.add(r["url"])
                if len(selected_topics) >= topics_count:
                    break

    if not selected_topics:
        theme_msg = f" sur le thème '{theme}'" if theme_query else ""
        raise ValueError(f"Aucun article disponible pour la période sélectionnée{theme_msg}.")

    actual_topics_count = len(selected_topics)
    cover_image_url = extract_cover_image(selected_topics)

    topics_formatted = "\n\n".join([
        f"--- SUJET #{idx+1} : {t['title']} ---\nSources: {', '.join([s['feed'] + ': ' + s['title'] for s in t['sources']])}\nExtrait: {t['content'][:400]}"
        for idx, t in enumerate(selected_topics)
    ])

    tone_instructions = {
        "journal_matinal": "un ton de journal matinal radio fluide, dynamique, clair et professionnel",
        "decryptage": "un ton de décryptage analytique, posé, approfondi et explicatif",
        "flash_express": "un ton de flash d'information rapide, concis et synthétique"
    }
    chosen_tone = tone_instructions.get(tone, tone_instructions["journal_matinal"])

    is_dynamic_voice = "dynamic" in voice_key.lower() or "multi" in voice_key.lower()

    system_prompt = (
        "Tu es la présentatrice vedette Marie de l'émission de radio podcast 'Vos'. "
        f"Rédige le script intégral d'une revue de presse audio avec {chosen_tone}. "
        f"\nCONSIGNE CAPITALE : Le script DOIT OBLIGATOIREMENT traiter les {actual_topics_count} sujets d'actualités distincts présentés ci-dessous. "
        f"Il doit comporter EXACTEMENT {actual_topics_count} sections/paragraphes bien identifiés."
        "\nIMPORTANT POUR LE TITRE DE L'ÉMISSION (show_title) :"
        "\nLe titre DOIT OBLIGATOIREMENT lister les 2 à 4 mots-clés majeurs des sujets traités suivis impérativement de '(revue de presse)'."
        "\nExemple : 'Guerre en Ukraine, Climat & IA (revue de presse)'"
    )

    if is_dynamic_voice:
        system_prompt += (
            "\nPOUR CHAQUE SECTION/SUJET, associe l'émotion vocale exacte la plus appropriée dans la liste suivante :"
            "\n- 'Marie - Neutral' (Intro, transitions, faits neutres)"
            "\n- 'Marie - Excited' (Exploits, victoires, avancées majeures, événements palpitants)"
            "\n- 'Marie - Happy' (Nouvelles réjouissantes, initiatives positives, touche d'espoir)"
            "\n- 'Marie - Sad' (Inondations, bilans graves, décès, drames humanitaires)"
            "\n- 'Marie - Curious' (Découvertes scientifiques, enquêtes, mystères)"
            "\n- 'Marie - Angry' (Scandales, injustices, colères, crises politiques)"
        )
        user_prompt = f"""
        Voici les {actual_topics_count} sujets d'actualités distincts à traiter dans l'émission :
        {topics_formatted}

        Rédige le script au format JSON suivant :
        {{
          "show_title": "Mots-Clés Principaux (revue de presse)",
          "sections": [
            {{
              "emotion": "Marie - Neutral",
              "text": "Introduction radiophonique chaleureuse..."
            }},
            {{
              "emotion": "Une des 6 émotions parmi Marie - Excited / Neutral / Happy / Sad / Curious / Angry",
              "text": "Texte du sujet 1..."
            }}
          ]
        }}
        Réponds uniquement au format JSON valide.
        """
    else:
        user_prompt = f"""
        Voici les {actual_topics_count} sujets d'actualités distincts à traiter dans l'émission :
        {topics_formatted}

        Rédige le script au format JSON suivant :
        {{
          "show_title": "Mots-Clés Principaux (revue de presse)",
          "script": "Texte intégral rédigé pour la diction radio couvrant tous les sujets."
        }}
        Réponds uniquement au format JSON valide.
        """

    async with httpx.AsyncClient() as client:
        response = await client.post(
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

        if response.status_code != 200:
            raise ValueError(f"Erreur lors de la rédaction du script par Mistral: {response.text}")

        res_json = response.json()
        ai_raw = res_json["choices"][0]["message"]["content"]
        script_data = json.loads(ai_raw)

    raw_title = script_data.get("show_title", f"Actualités du jour (revue de presse)")
    if "(revue de presse)" not in raw_title.lower():
        show_title = f"{raw_title} (revue de presse)"
    else:
        show_title = raw_title

    # 3. Audio Synthesis
    if is_dynamic_voice and "sections" in script_data:
        sections = script_data["sections"]
        full_script = "\n\n".join([f"[{sec.get('emotion', 'Marie - Neutral')}]\n{sec.get('text')}" for sec in sections])
        
        audio_chunks = []
        for sec in sections:
            sec_text = sec.get("text", "").strip()
            if not sec_text:
                continue
            sec_emotion = sec.get("emotion", "Marie - Neutral")
            chunk_bytes = await generate_audio_bytes_for_voice(sec_text, voice_key=sec_emotion, api_key=key)
            audio_chunks.append(chunk_bytes)

        if not audio_chunks:
            audio_filename = await generate_podcast_audio("Synthèse d'actualité.", voice_key="Marie - Neutral", api_key=key)
        else:
            audio_filename = combine_audio_chunks(audio_chunks)

    else:
        full_script = script_data.get("script", "")
        audio_filename = await generate_podcast_audio(full_script, voice_key=voice_key, api_key=key)

    audio_url = f"{b_url}/api/audio/stream/{audio_filename}"

    # 4. Save into SQLite database
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
        "theme": theme_query,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def generate_podcast_rss_feed(base_url: str = None) -> str:
    """
    Generates a 100% valid RSS 2.0 XML podcast feed with iTunes / AntennaPod / Spotify / Apple Podcasts metadata.
    Includes episode image, HTML description with clickable sources, and audio enclosure length.
    """
    b_url = (base_url or settings.base_url).rstrip("/")
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

    feed_url = f"{b_url}/api/podcast/feed.xml"

    items_xml = []
    for r in rows:
        p_id = r["id"]
        title = xml_escape(r["title"])
        script = r["script"]
        raw_audio_url = r["audio_url"]
        img_url = r["image_url"] or DEFAULT_PODCAST_COVER
        
        # Dynamically adapt audio_url if host changed or VPS URL is specified
        audio_filename = r["audio_filename"]
        audio_url = f"{b_url}/api/audio/stream/{audio_filename}"

        filepath = AUDIO_DIR / audio_filename
        file_size = filepath.stat().st_size if filepath.exists() else 2000000

        try:
            dt = datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S")
            pub_date_str = dt.strftime("%a, %d %b %Y %H:%M:%S +0200")
        except Exception:
            pub_date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")

        clean_script = script.replace("<", "&lt;").replace(">", "&gt;")
        desc_html = f"<![CDATA[<p>{script[:500]}...</p><h3>Transcription &amp; Émission complète :</h3><p>{script}</p>]]>"

        item_str = f"""    <item>
      <title>{title}</title>
      <link>{audio_url}</link>
      <guid isPermaLink="false">vos-podcast-ep-{p_id}</guid>
      <pubDate>{pub_date_str}</pubDate>
      <description>{desc_html}</description>
      <content:encoded>{desc_html}</content:encoded>
      <enclosure url="{audio_url}" length="{file_size}" type="audio/mpeg"/>
      <itunes:image href="{xml_escape(img_url)}"/>
      <itunes:duration>04:00</itunes:duration>
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

def get_podcast_history():
    """
    Returns the list of previously generated podcasts.
    """
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
    return [dict(r) for r in rows]
