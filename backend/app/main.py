import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db, get_db_connection
from app.config import settings
from app.api import routes_feeds, routes_articles, routes_clustering, routes_audio, routes_podcast, routes_catalog
from app.services.scheduler import start_podcast_scheduler_loop
from seed_catalog import seed_catalog

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()

    # Auto-seed catalog if empty
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM catalog_feeds")
        cnt = c.fetchone()["cnt"]
        conn.close()
        if cnt == 0:
            seed_catalog()
    except Exception as e:
        print(f"[Auto-seed note] {e}")

    # Start background podcast scheduler loop
    scheduler_task = asyncio.create_task(start_podcast_scheduler_loop())
    yield
    scheduler_task.cancel()

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(routes_feeds.router)
app.include_router(routes_articles.router)
app.include_router(routes_clustering.router)
app.include_router(routes_audio.router)
app.include_router(routes_podcast.router)
app.include_router(routes_catalog.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
