import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import init_db, get_db_connection
from app.config import settings
from app.api import routes_feeds, routes_articles, routes_clustering, routes_audio, routes_podcast, routes_catalog, routes_stats, routes_audio_stream, routes_subscriptions, routes_audit, routes_podcast_settings, routes_settings, routes_webhooks
from app.services.scheduler import start_podcast_scheduler_loop
from seed_massive_catalog import seed_massive_catalog_async

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR_CATEGORIES = STATIC_DIR / "categories"
STATIC_DIR_CATEGORIES.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()

    # Auto-seed & sync catalog database in background thread (non-blocking)
    try:
        asyncio.create_task(asyncio.to_thread(asyncio.run, seed_massive_catalog_async()))
    except Exception as e:
        print(f"[Auto-seed background note] {e}")

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

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register routes
app.include_router(routes_feeds.router)
app.include_router(routes_articles.router)
app.include_router(routes_clustering.router)
app.include_router(routes_audio.router)
app.include_router(routes_podcast.router)
app.include_router(routes_catalog.router)
app.include_router(routes_stats.router)
app.include_router(routes_audio_stream.router)
app.include_router(routes_subscriptions.router)
app.include_router(routes_audit.router)
app.include_router(routes_podcast_settings.router)
app.include_router(routes_settings.router)
app.include_router(routes_webhooks.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
