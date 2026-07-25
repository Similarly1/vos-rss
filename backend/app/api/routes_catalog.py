from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import feedparser
import httpx
from app.services.catalog import search_catalog, get_all_tags, add_or_update_catalog_feed
from app.services.rss_discovery import discover_rss_feed

router = APIRouter(prefix="/api/catalog", tags=["Catalog"])

from app.services.opml_importer import import_opml_text

class DiscoverRequest(BaseModel):
    query: str
    auto_save: Optional[bool] = False

class OpmlImportRequest(BaseModel):
    content: str
    default_category: Optional[str] = "Général"

@router.get("")
@router.get("/")
def get_catalog_feeds(
    q: Optional[str] = Query(None, description="Search term or keywords"),
    category: Optional[str] = Query(None, description="Category filter"),
    tag: Optional[str] = Query(None, description="Hashtag filter (e.g. #suisse)"),
    language: Optional[str] = Query(None, description="Language code filter (fr, en, de, es)"),
    limit: int = Query(30, ge=1, le=200, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Search and filter catalog feeds stored in SQLite using Full-Text Search or tags with pagination.
    """
    return search_catalog(query=q, category=category, tag=tag, language=language, limit=limit, offset=offset)

@router.get("/tags")
def get_catalog_tags():
    """
    Returns list of available tags with count of associated catalog feeds.
    """
    return get_all_tags()

@router.post("/import-opml")
def import_opml_catalog(payload: OpmlImportRequest):
    """
    Imports catalog feeds from raw OPML content.
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Contenu OPML vide.")

    count = import_opml_text(payload.content, default_category=payload.default_category)
    return {"success": True, "imported_count": count}

@router.post("/discover")
async def discover_feed(payload: DiscoverRequest):
    """
    Performs Web Auto-Discovery on a domain, website URL, or RSS feed link.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="La requête ne peut pas être vide.")

    res = await discover_rss_feed(query)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Aucun flux RSS trouvé."))

    # Save to catalog database ONLY if explicitly requested (auto_save defaults to False)
    if payload.auto_save:
        feed_data = {
            "url": res["feed_url"],
            "site_url": res.get("site_url", ""),
            "title": res.get("title", ""),
            "description": res.get("description", ""),
            "icon_url": res.get("icon_url", ""),
            "category": "Général",
            "language": "fr",
            "is_full_text": True,
            "is_verified": False
        }
        try:
            add_or_update_catalog_feed(feed_data, tags=res.get("tags", []))
        except Exception as e:
            print(f"[Catalog Auto-Save Note] {e}")

    return res

from app.services.rss import robust_parse_feed, extract_main_image_url

@router.get("/preview")
async def preview_feed(url: str = Query(..., description="Feed RSS URL to preview")):
    """
    Fetches the 3 most recent articles from a feed URL without subscribing.
    """
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="URL requise.")

    try:
        parsed, final_url = robust_parse_feed(clean_url)
        if not parsed or not parsed.entries:
            raise HTTPException(status_code=400, detail="Impossible de lire ce flux RSS (Format invalide, indisponible ou URL incorrecte).")

        articles = []
        for entry in parsed.entries[:3]:
            summary = entry.get("summary", entry.get("description", ""))
            img_url = extract_main_image_url(entry, summary)
            
            import re
            summary_clean = re.sub(r'<[^>]+>', '', summary)[:180] + ("..." if len(summary) > 180 else "")

            articles.append({
                "title": entry.get("title", "Sans titre"),
                "link": entry.get("link", "#"),
                "published": entry.get("published", entry.get("updated", "")),
                "summary": summary_clean,
                "image_url": img_url
            })

        return {
            "title": parsed.feed.get("title", "Flux RSS"),
            "description": parsed.feed.get("description", ""),
            "articles": articles
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible d'afficher l'aperçu du flux : {str(e)}")

class SearchLocalNewsRequest(BaseModel):
    query: str
    api_key: Optional[str] = None

@router.post("/search-local")
async def search_local_news(payload: SearchLocalNewsRequest):
    from app.services.local_news import search_local_news_feeds
    res = await search_local_news_feeds(payload.query, langsearch_key=payload.api_key)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Erreur lors de la recherche LangSearch."))
    return res
