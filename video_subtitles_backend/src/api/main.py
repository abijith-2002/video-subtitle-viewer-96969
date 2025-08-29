from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.db.session import init_db, engine, get_async_session
from src.api.routers.videos import router as videos_router
from src.api.routers.subtitles import router as subtitles_router
from src.services.storage import ensure_media_dirs
from src.api.settings import settings
from src.db.seed import seed_if_empty

openapi_tags = [
    {
        "name": "Health",
        "description": "Basic service health and status endpoints.",
    },
    {
        "name": "Videos",
        "description": "Endpoints for listing, uploading, and streaming videos.",
    },
    {
        "name": "Subtitles",
        "description": "Endpoints for managing subtitle files associated to videos.",
    },
]

# Load .env (non-fatal if missing; rely on environment in deployment)
load_dotenv()

app = FastAPI(
    title="Video Subtitles Backend",
    description="Backend service for managing and serving videos and subtitles.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS - wide open for now; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Initialize application resources.

    - Ensure media storage directories are present (configurable via MEDIA_ROOT)
    - Initialize database connectivity and create tables (simple migration)
    - Optionally seed DB with sample data on first run (dev utility controlled by SEED_DB)
    """
    # Ensure directories based on MEDIA_ROOT from settings
    ensure_media_dirs()

    # Initialize DB (reads env vars in db.session.build_postgres_dsn)
    await init_db()

    # Optional seeding for development environments
    if settings.ENV in {"development", "dev"} and settings.SEED_DB:
        async with get_async_session() as session:
            await seed_if_empty(session)


@app.on_event("shutdown")
async def on_shutdown():
    """Cleanup resources on shutdown."""
    # Dispose engine if created
    if engine is not None:
        await engine.dispose()


@app.get("/", tags=["Health"], summary="Health Check")
def health_check():
    """Health check endpoint.

    Returns:
        JSON containing a simple 'Healthy' message.
    """
    return {"message": "Healthy"}


# Register routers
app.include_router(videos_router)
app.include_router(subtitles_router)
