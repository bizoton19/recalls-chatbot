"""
Recalls Chatbot — FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import recalls, chat, admin, search
from config import settings
from db.database import engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, seed agencies, start scheduler
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from models.recall import Agency

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

        # Add recall columns when missing (existing DBs won't auto-alter with create_all)
        await conn.execute(text(
            "ALTER TABLE recalls ADD COLUMN IF NOT EXISTS manufacturer_countries TEXT[]"
        ))
        await conn.execute(text(
            "ALTER TABLE recalls ADD COLUMN IF NOT EXISTS last_publish_date DATE"
        ))
        # Backfill manufacturer_countries from raw_data JSON (CPSC: ManufacturerCountries[].Country)
        await conn.execute(text("""
            UPDATE recalls r
            SET manufacturer_countries = sub.arr
            FROM (
                SELECT id AS sid,
                    (
                        SELECT COALESCE(array_agg(DISTINCT trim(e->>'Country')), ARRAY[]::text[])
                        FROM jsonb_array_elements(
                            COALESCE(raw_data->'ManufacturerCountries', '[]'::jsonb)
                        ) AS e
                        WHERE trim(e->>'Country') IS NOT NULL AND trim(e->>'Country') != ''
                    ) AS arr
                FROM recalls
            ) sub
            WHERE r.id = sub.sid
              AND (r.manufacturer_countries IS NULL OR cardinality(r.manufacturer_countries) = 0)
              AND sub.arr IS NOT NULL AND cardinality(sub.arr) > 0
        """))

        # Migrate embedding column from vector(1536) → vector(768) if needed.
        # recall_embeddings is safe to truncate since indexing runs on every startup.
        await conn.execute(text(
            "DO $$ BEGIN "
            "  IF EXISTS (SELECT 1 FROM information_schema.columns "
            "              WHERE table_name='recall_embeddings' AND column_name='embedding') THEN "
            "    EXECUTE 'ALTER TABLE recall_embeddings ALTER COLUMN embedding TYPE vector(768)'; "
            "    DELETE FROM recall_embeddings; "
            "    UPDATE recalls SET is_indexed = FALSE; "
            "  END IF; "
            "END $$;"
        ))

        # Seed known agencies
        await conn.execute(
            pg_insert(Agency).values([
                {"code": "CPSC", "name": "U.S. Consumer Product Safety Commission",
                 "url": "https://www.cpsc.gov", "api_url": "https://www.saferproducts.gov/RestWebServices/Recall"},
            ]).on_conflict_do_nothing(index_elements=["code"])
        )

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(recalls.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/health")
async def health():
    from sqlalchemy import text
    from db.database import AsyncSessionLocal
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "version": "1.0.0",
        "environment": settings.environment,
    }
