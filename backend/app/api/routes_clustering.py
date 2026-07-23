import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db_connection, HAS_SQLITE_VEC, init_db
from app.config import settings
from app.services.embeddings import vectorize_all_pending
from app.services.clustering import compute_article_clusters, synthesize_cluster, get_cached_clusters, precompute_and_cache_clusters

router = APIRouter(prefix="/api/clustering", tags=["Clustering"])

class VectorizeRequest(BaseModel):
    api_key: Optional[str] = None
    force_revectorize: Optional[bool] = False

class SynthesizeRequest(BaseModel):
    articles: List[dict]
    api_key: Optional[str] = None
    model: Optional[str] = "mistral-small-latest"

class PrecomputeRequest(BaseModel):
    api_key: Optional[str] = None

@router.get("/status")
def get_vector_status():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM articles")
    total_articles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as count FROM article_embeddings")
    vectorized_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "total_articles": total_articles,
        "vectorized_articles": vectorized_count,
        "sqlite_vec_enabled": HAS_SQLITE_VEC,
        "pending_articles": total_articles - vectorized_count
    }

@router.post("/vectorize")
async def trigger_vectorization(payload: VectorizeRequest, background_tasks: BackgroundTasks):
    api_key = payload.api_key or settings.mistral_api_key
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API Mistral requise pour la vectorisation. Veuillez la renseigner dans les Paramètres."
        )

    try:
        res = await vectorize_all_pending(api_key, force_revectorize=payload.force_revectorize or False)
        
        # Schedule cluster & AI summary pre-computation in the background
        background_tasks.add_task(precompute_and_cache_clusters, api_key)
        
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/precompute")
async def trigger_precompute(payload: Optional[PrecomputeRequest] = None, background_tasks: BackgroundTasks = None):
    api_key = (payload.api_key if payload else None) or settings.mistral_api_key
    try:
        res = await precompute_and_cache_clusters(api_key=api_key)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters")
def get_clusters(threshold: float = 0.91):
    try:
        # Determine cache key
        mode_key = "events" if threshold >= 0.86 else "themes"
        cached = get_cached_clusters(f"threshold_{mode_key}") or get_cached_clusters(f"threshold_{threshold}")

        if cached is not None:
            return {
                "status": "success", 
                "source": "cache", 
                "clusters_count": len(cached), 
                "clusters": cached
            }

        # Fallback to computing on-the-fly if cache is empty
        clusters = compute_article_clusters(similarity_threshold=threshold)
        return {"status": "success", "source": "live", "clusters_count": len(clusters), "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize")
async def create_synthesis(payload: SynthesizeRequest):
    api_key = payload.api_key or settings.mistral_api_key
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API Mistral requise pour générer la synthèse. Veuillez la renseigner dans les Paramètres."
        )

    try:
        synthesis = await synthesize_cluster(payload.articles, api_key=api_key, model=payload.model or "mistral-small-latest")
        return {"status": "success", "data": synthesis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
