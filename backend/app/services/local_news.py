import asyncio
import urllib.parse
import httpx
from typing import Dict, Any, List
from app.services.rss import get_all_feeds
from app.services.rss_discovery import discover_rss_feed
from app.api.routes_feeds import get_vps_langsearch_key

EXCLUDED_DOMAINS = {
    "wikipedia.org", "facebook.com", "twitter.com", "x.com", "youtube.com",
    "instagram.com", "linkedin.com", "tiktok.com", "amazon.com", "google.com"
}

async def search_local_news_feeds(query: str, langsearch_key: str = None) -> Dict[str, Any]:
    key = get_vps_langsearch_key(langsearch_key)
    if not key:
        return {
            "status": "error",
            "message": "Clé API LangSearch manquante. Veuillez la renseigner dans les Paramètres (icône ⚙️)."
        }

    user_query = query.strip()
    if not user_query:
        return {"status": "error", "message": "Veuillez préciser un mot-clé ou une région (ex: Vaud, Toulouse, Bretagne)."}

    # Format search query for local news focus if not already specified
    lower_q = user_query.lower()
    if not any(k in lower_q for k in ["journal", "presse", "actualit", "médias", "media", "news"]):
        search_query = f"journal local actualités {user_query}"
    else:
        search_query = user_query

    candidate_urls = []
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.langsearch.com/v1/search",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "query": search_query,
                    "freshness": "oneMonth",
                    "summary": False,
                    "count": 12
                },
                timeout=12.0
            )

            if res.status_code != 200:
                err_text = res.text
                try:
                    err_json = res.json()
                    err_text = err_json.get("message", res.text)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "message": f"Erreur API LangSearch ({res.status_code}) : {err_text}"
                }

            data = res.json()
            
            # Flexible parsing for LangSearch API response formats
            items = []
            if isinstance(data, dict):
                items = (
                    data.get("data", {}).get("webPages", {}).get("value", []) or
                    data.get("results", []) or
                    data.get("data", []) or
                    data.get("value", [])
                )
            elif isinstance(data, list):
                items = data

            for item in items:
                if not isinstance(item, dict):
                    continue
                url = item.get("url") or item.get("link")
                if not url:
                    continue
                
                parsed = urllib.parse.urlparse(url)
                netloc = (parsed.netloc or "").lower()
                
                # Exclude social networks and general non-news portals
                if any(ex in netloc for ex in EXCLUDED_DOMAINS):
                    continue
                
                # Normalize site root or specific page
                base_site = f"{parsed.scheme}://{parsed.netloc}"
                if base_site not in candidate_urls:
                    candidate_urls.append(base_site)

    except Exception as e:
        return {
            "status": "error",
            "message": f"Échec de la recherche LangSearch : {str(e)}"
        }

    if not candidate_urls:
        return {
            "status": "success",
            "query": user_query,
            "count": 0,
            "data": [],
            "message": "Aucun résultat trouvé sur LangSearch."
        }

    # Fetch user's existing subscribed feed URLs
    existing_feeds = get_all_feeds()
    subscribed_urls = set()
    for category in existing_feeds.values():
        for f in category:
            subscribed_urls.add(f.get("url", "").lower())
            subscribed_urls.add(f.get("site_url", "").lower())

    # Limit to top candidate URLs for parallel RSS discovery
    target_candidates = candidate_urls[:8]
    tasks = [discover_rss_feed(site_url) for site_url in target_candidates]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    discovered_feeds = []
    seen_feed_urls = set()

    for site_url, res in zip(target_candidates, results):
        if isinstance(res, dict) and res.get("success") and res.get("feed_url"):
            f_url = res["feed_url"].lower()
            if f_url in seen_feed_urls:
                continue
            seen_feed_urls.add(f_url)

            is_subscribed = (f_url in subscribed_urls) or (res.get("site_url", "").lower() in subscribed_urls)

            discovered_feeds.append({
                "title": res.get("title") or site_url,
                "feed_url": res["feed_url"],
                "site_url": res.get("site_url") or site_url,
                "description": res.get("description", ""),
                "favicon": res.get("icon_url") or f"https://www.google.com/s2/favicons?domain={urllib.parse.urlparse(site_url).netloc}&sz=128",
                "tags": res.get("tags", ["#local"]),
                "preview_articles": res.get("preview_articles", []),
                "already_subscribed": is_subscribed
            })

    return {
        "status": "success",
        "query": user_query,
        "count": len(discovered_feeds),
        "data": discovered_feeds
    }
