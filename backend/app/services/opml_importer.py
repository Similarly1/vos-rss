import re
import xml.etree.ElementTree as ET
import httpx
from typing import Dict, Any, List, Optional
from app.services.catalog import add_or_update_catalog_feed, slugify

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 VosRSS/2.0"
}

def parse_opml_outlines(element: ET.Element, current_folder: str = "") -> List[Dict[str, Any]]:
    """
    Recursively parses OPML <outline> tags and extracts feed metadata + folder categories.
    """
    feeds = []
    for outline in element.findall("outline"):
        xml_url = outline.get("xmlUrl") or outline.get("xmlurl")
        html_url = outline.get("htmlUrl") or outline.get("htmlurl") or ""
        title = outline.get("title") or outline.get("text") or outline.get("description") or ""
        folder_text = outline.get("text") or outline.get("title") or ""

        if xml_url:
            # It's a feed item
            tags = []
            category = "Général"

            if current_folder:
                folder_clean = current_folder.strip()
                category = folder_clean.capitalize()
                tag_name = "#" + slugify(folder_clean)
                tags.append(tag_name)

            feeds.append({
                "url": xml_url.strip(),
                "site_url": html_url.strip(),
                "title": title.strip() or xml_url.strip(),
                "description": "",
                "icon_url": f"https://www.google.com/s2/favicons?domain={html_url or xml_url}&sz=128",
                "category": category,
                "language": "fr",
                "is_full_text": True,
                "is_verified": True,
                "tags": tags
            })
        else:
            # It's a parent folder container
            sub_folder = folder_text if folder_text else current_folder
            feeds.extend(parse_opml_outlines(outline, current_folder=sub_folder))

    return feeds

def import_opml_text(opml_content: str, default_category: str = "Général") -> int:
    """
    Parses OPML XML content string and inserts/updates catalog feeds in SQLite DB.
    Returns count of successfully imported feeds.
    """
    if not opml_content or not opml_content.strip():
        return 0

    try:
        root = ET.fromstring(opml_content.strip())
    except Exception as e:
        print(f"[OPML Parse Error]: {e}")
        return 0

    body = root.find("body")
    if body is None:
        body = root

    extracted_feeds = parse_opml_outlines(body)
    imported_count = 0

    for feed_info in extracted_feeds:
        feed_url = feed_info.get("url")
        if not feed_url or not feed_url.startswith("http"):
            continue
        
        tags = feed_info.pop("tags", [])
        if default_category and default_category != "Général" and feed_info.get("category") == "Général":
            feed_info["category"] = default_category
            tags.append("#" + slugify(default_category))

        try:
            feed_id = add_or_update_catalog_feed(feed_info, tags=tags)
            if feed_id:
                imported_count += 1
        except Exception as err:
            print(f"[OPML Import Feed Error for {feed_url}]: {err}")

    return imported_count

async def fetch_and_import_opml_url(opml_url: str, default_category: str = "Général") -> int:
    """
    Downloads an OPML file over HTTP and imports its feeds into the catalog database.
    """
    clean_url = opml_url.strip()
    if not clean_url:
        return 0

    print(f"[OPML Auto-Import] Téléchargement depuis {clean_url}...")
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20.0) as client:
            r = await client.get(clean_url)
            if r.status_code == 200 and r.text:
                count = import_opml_text(r.text, default_category=default_category)
                print(f"[OPML Auto-Import] [OK] {count} flux importes depuis {clean_url}.")
                return count
            else:
                print(f"[OPML Auto-Import] HTTP {r.status_code} pour {clean_url}")
    except Exception as e:
        print(f"[OPML Auto-Import Exception for {clean_url}]: {e}")

    return 0
