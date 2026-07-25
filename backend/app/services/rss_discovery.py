import re
import urllib.parse
import httpx
import feedparser
from typing import Dict, Any, List, Optional
from app.services.catalog import slugify

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 VosRSS/2.0"
}

STANDARD_FEED_PATHS = [
    "/feed/",
    "/feed",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feed.xml",
    "/?feed=rss2",
    "/index.xml"
]

def auto_extract_tags(title: str, description: str, xml_categories: List[str]) -> List[str]:
    """Generates 2-4 hashtag tags based on title, description, and XML categories."""
    tags = set()
    text = (title + " " + description + " " + " ".join(xml_categories)).lower()
    
    # 🇨🇭 Suisse
    if any(k in text for k in ["rts", "suisse", "swiss", "lausanne", "genève", "zurich", "berne", "letemps", "24heures", "vaud"]):
        tags.add("#suisse")
    
    # 🚀 Tech / Numérique
    if any(k in text for k in ["tech", "numérique", "informatique", "code", "logiciel", "cyber", "ai", "ia", "hardware", "software", "web", "hacker"]):
        tags.add("#technologie")
        if "cyber" in text or "hacker" in text or "sécurité" in text:
            tags.add("#cybersécurité")
    
    # ⛪ Chrétien / Foi
    if any(k in text for k in ["chrétien", "christianisme", "évangile", "église", "foi", "bible", "vatican", "réforme", "dieu", "prière", "evangelique", "catholique", "protestant"]):
        tags.add("#chrétien")

    # 🔬 Science
    if any(k in text for k in ["science", "recherche", "espace", "astronomie", "biologie", "nature", "physics"]):
        tags.add("#science")

    # 📰 Presse & Monde
    if any(k in text for k in ["monde", "international", "presse", "journal", "actualité", "politique", "news"]):
        tags.add("#monde")

    # Default category fallback
    if not tags:
        tags.add("#actualité")

    return list(tags)

def extract_feed_links_from_html(html_text: str, base_url: str) -> List[str]:
    """Uses regex to extract RSS/Atom URLs from HTML <link> tags."""
    found_urls = []
    # Match <link ... >
    link_pattern = re.compile(r'<link\s+[^>]*>', re.IGNORECASE)
    rel_pattern = re.compile(r'rel=["\']?(?:alternate|feed)["\']?', re.IGNORECASE)
    type_pattern = re.compile(r'type=["\']?(?:application/rss\+xml|application/atom\+xml|text/xml|application/xml)["\']?', re.IGNORECASE)
    href_pattern = re.compile(r'href=["\']?([^"\'\s>]+)["\']?', re.IGNORECASE)

    for match in link_pattern.finditer(html_text):
        tag_str = match.group(0)
        if rel_pattern.search(tag_str) and type_pattern.search(tag_str):
            href_m = href_pattern.search(tag_str)
            if href_m:
                raw_href = href_m.group(1)
                full_url = urllib.parse.urljoin(base_url, raw_href)
                found_urls.append(full_url)
    return found_urls

async def discover_rss_feed(query_or_url: str) -> Dict[str, Any]:
    """
    Dynamically discovers RSS/Atom feed from a domain or URL.
    Returns result dict with: success (bool), feed_url, site_url, title, description, icon_url, tags, preview_articles.
    """
    raw_input = query_or_url.strip()
    if not raw_input:
        return {"success": False, "error": "URL ou terme de recherche vide."}

    # Ensure URL scheme
    if not raw_input.startswith("http://") and not raw_input.startswith("https://"):
        target_url = "https://" + raw_input
    else:
        target_url = raw_input

    parsed_target = urllib.parse.urlparse(target_url)
    domain = parsed_target.netloc or parsed_target.path.split('/')[0]

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
        # Step 1: Direct test if target_url is already a feed
        try:
            r = await client.get(target_url)
            if r.status_code == 200:
                parsed = feedparser.parse(r.text)
                if parsed.version and parsed.entries:
                    feed_title = parsed.feed.get("title", domain)
                    feed_desc = parsed.feed.get("description", parsed.feed.get("subtitle", ""))
                    feed_link = parsed.feed.get("link", target_url)
                    categories = [c.get("term", "") for c in parsed.feed.get("categories", []) if isinstance(c, dict)]
                    
                    preview_articles = []
                    for entry in parsed.entries[:3]:
                        preview_articles.append({
                            "title": entry.get("title", "Sans titre"),
                            "link": entry.get("link", "#"),
                            "published": entry.get("published", entry.get("updated", ""))
                        })

                    favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

                    return {
                        "success": True,
                        "feed_url": str(r.url),
                        "site_url": feed_link,
                        "title": feed_title,
                        "description": feed_desc,
                        "icon_url": favicon,
                        "tags": auto_extract_tags(feed_title, feed_desc, categories),
                        "preview_articles": preview_articles
                    }
        except Exception:
            pass

        # Step 2: Parse Homepage HTML for <link rel="alternate">
        try:
            r = await client.get(target_url)
            if r.status_code == 200 and "text/html" in r.headers.get("content-type", "").lower():
                feed_urls_found = extract_feed_links_from_html(r.text, str(r.url))

                # Try parsing discovered feed URLs
                for found_feed_url in feed_urls_found:
                    try:
                        fr = await client.get(found_feed_url)
                        if fr.status_code == 200:
                            parsed = feedparser.parse(fr.text)
                            if parsed.entries:
                                feed_title = parsed.feed.get("title", domain)
                                feed_desc = parsed.feed.get("description", parsed.feed.get("subtitle", ""))
                                categories = [c.get("term", "") for c in parsed.feed.get("categories", []) if isinstance(c, dict)]
                                
                                preview_articles = []
                                for entry in parsed.entries[:3]:
                                    preview_articles.append({
                                        "title": entry.get("title", "Sans titre"),
                                        "link": entry.get("link", "#"),
                                        "published": entry.get("published", entry.get("updated", ""))
                                    })

                                favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

                                return {
                                    "success": True,
                                    "feed_url": str(fr.url),
                                    "site_url": str(r.url),
                                    "title": feed_title,
                                    "description": feed_desc,
                                    "icon_url": favicon,
                                    "tags": auto_extract_tags(feed_title, feed_desc, categories),
                                    "preview_articles": preview_articles
                                }
                    except Exception:
                        continue
        except Exception:
            pass

        # Step 3: Probe Fallback Paths
        base_origin = f"{parsed_target.scheme or 'https'}://{domain}"
        for path in STANDARD_FEED_PATHS:
            candidate_url = base_origin + path
            try:
                fr = await client.get(candidate_url)
                if fr.status_code == 200:
                    parsed = feedparser.parse(fr.text)
                    if parsed.version and parsed.entries:
                        feed_title = parsed.feed.get("title", domain)
                        feed_desc = parsed.feed.get("description", "")
                        categories = [c.get("term", "") for c in parsed.feed.get("categories", []) if isinstance(c, dict)]
                        
                        preview_articles = []
                        for entry in parsed.entries[:3]:
                            preview_articles.append({
                                "title": entry.get("title", "Sans titre"),
                                "link": entry.get("link", "#"),
                                "published": entry.get("published", entry.get("updated", ""))
                            })

                        favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

                        return {
                            "success": True,
                            "feed_url": str(fr.url),
                            "site_url": base_origin,
                            "title": feed_title,
                            "description": feed_desc,
                            "icon_url": favicon,
                            "tags": auto_extract_tags(feed_title, feed_desc, categories),
                            "preview_articles": preview_articles
                        }
            except Exception:
                continue

    return {
        "success": False,
        "error": f"Aucun flux RSS/Atom valide n'a pu être détecté automatiquement sur {domain}."
    }
