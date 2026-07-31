import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db_connection, HAS_SQLITE_VEC, init_db
from app.config import settings
from app.api.routes_feeds import get_vps_api_key
from app.services.embeddings import vectorize_all_pending
from app.services.clustering import compute_article_clusters, synthesize_cluster, get_cached_clusters, precompute_and_cache_clusters, clear_cluster_cache

router = APIRouter(prefix="/api/clustering", tags=["Clustering"])

class VectorizeRequest(BaseModel):
    api_key: Optional[str] = None
    force_revectorize: Optional[bool] = False

class SynthesizeRequest(BaseModel):
    articles: List[dict]
    api_key: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

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

async def background_vectorize_and_precompute(api_key: str, force_revectorize: bool):
    try:
        res = await vectorize_all_pending(
            mistral_key=api_key,
            gemini_key=settings.gemini_api_key,
            provider=settings.vectorization_provider,
            fallback_provider=settings.vectorization_fallback_provider,
            mistral_model=settings.mistral_embed_model,
            gemini_model=settings.gemini_embed_model,
            force_revectorize=force_revectorize
        )
        print(f"[Vectorisation IA] {res.get('processed_count', 0)} articles vectorisés avec succès.")
        await precompute_and_cache_clusters(mistral_key=api_key)
        print("[Précalcul Grappes] Grappes et synthèses calculées et mises en cache !")
    except Exception as e:
        print(f"[Vectorisation & Grappes Erreur] {e}")

@router.post("/vectorize")
async def trigger_vectorization(payload: VectorizeRequest, background_tasks: BackgroundTasks):
    api_key = get_vps_api_key(payload.api_key)
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API Mistral requise pour la vectorisation. Veuillez la renseigner dans les Paramètres."
        )

    try:
        # Launch vectorization AND cluster precomputation in the background to avoid Nginx 504 Gateway Timeout
        background_tasks.add_task(
            background_vectorize_and_precompute,
            api_key,
            payload.force_revectorize or False
        )
        
        return {
            "status": "success", 
            "message": "La vectorisation et le calcul des grappes ont été lancés en arrière-plan avec succès !"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clear-cache")
def clear_cache():
    try:
        clear_cluster_cache()
        return {"status": "success", "message": "Cache des synthèses et grappes vidé avec succès."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/precompute")
async def trigger_precompute(payload: Optional[PrecomputeRequest] = None, background_tasks: BackgroundTasks = None):
    api_key = get_vps_api_key(payload.api_key if payload else None)
    try:
        res = await precompute_and_cache_clusters(api_key=api_key)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters")
async def get_clusters(threshold: float = 0.91, cluster_type: str = "all"):
    try:
        # Determine if we can use cache
        clusters = None
        source = "live"
        
        # We only use cache if the threshold matches exactly the precomputed modes
        if abs(threshold - 0.86) < 0.001:
            cached = get_cached_clusters("threshold_events")
            if cached is not None and len(cached) > 0:
                clusters = cached
                source = "cache"
        elif abs(threshold - 0.78) < 0.001:
            cached = get_cached_clusters("threshold_themes")
            if cached is not None and len(cached) > 0:
                clusters = cached
                source = "cache"

        if clusters is None:
            clusters = await asyncio.to_thread(compute_article_clusters, similarity_threshold=threshold)
            source = "live"

        # Apply cluster_type filtering
        if cluster_type == "events":
            filtered_clusters = []
            for c in clusters:
                cat = (c.get("category") or "").lower()
                if "bilan" not in cat and "revue" not in cat:
                    filtered_clusters.append(c)
            clusters = filtered_clusters

        return {
            "status": "success", 
            "source": source, 
            "clusters_count": len(clusters), 
            "clusters": clusters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize")
async def create_synthesis(payload: SynthesizeRequest):
    m_key = get_vps_api_key(payload.api_key) or settings.mistral_api_key
    g_key = settings.gemini_api_key
    if not m_key and not g_key:
        raise HTTPException(
            status_code=400, 
            detail="Clé API Mistral ou Gemini requise pour générer la synthèse. Veuillez la renseigner dans les Paramètres."
        )

    prov = (payload.provider or settings.synthesis_provider or ("gemini" if not m_key and g_key else "mistral")).lower()
    m_model = payload.model if (payload.model and payload.model != "mistral-small-latest") else settings.mistral_discover_model
    g_model = payload.model if (payload.model and payload.model != "mistral-small-latest") else settings.gemini_discover_model

    try:
        synthesis = await synthesize_cluster(
            payload.articles,
            mistral_key=m_key,
            gemini_key=g_key,
            provider=prov,
            mistral_model=m_model,
            gemini_model=g_model
        )
        return {"status": "success", "data": synthesis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
