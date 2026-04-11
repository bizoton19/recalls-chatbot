"""
Recalls Chatbot — FastAPI application entry point.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import recalls, chat, admin
from db.database import engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, seed agencies, start scheduler
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables ready")

    # Start ingestion scheduler
    scheduler = None
    try:
        from workers.ingestion import start_scheduler, run_ingestion
        scheduler = start_scheduler()

        # Kick off an initial recent-only sync on startup
        import asyncio
        asyncio.create_task(run_ingestion(full_sync=False))
        logger.info("Initial recall sync queued")
    except Exception as e:
        logger.warning("Scheduler startup failed: %s", e)

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown()


app = FastAPI(
    title="Recalls Chatbot API",
    description="AI-powered federal recall search and conversational assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(recalls.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
