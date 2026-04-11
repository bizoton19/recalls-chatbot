"""
Admin routes — for triggering ingestion manually.
Protected by a simple API key header in production.
"""
import os
from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key")


def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


class IngestRequest(BaseModel):
    full_sync: bool = False


@router.post("/ingest", dependencies=[Depends(verify_admin_key)])
async def trigger_ingestion(body: IngestRequest, background_tasks: BackgroundTasks):
    """Manually trigger recall ingestion. Runs in the background."""
    from workers.ingestion import run_ingestion
    background_tasks.add_task(run_ingestion, full_sync=body.full_sync)
    return {
        "status": "ingestion_started",
        "full_sync": body.full_sync,
        "message": "Ingestion running in background. Check logs for progress.",
    }


@router.get("/stats", dependencies=[Depends(verify_admin_key)])
async def get_stats():
    """Return basic ingestion and index statistics."""
    from db.database import get_db_context
    from sqlalchemy import text

    async with get_db_context() as db:
        result = await db.execute(text("""
            SELECT
                agency_code,
                COUNT(*) AS total,
                SUM(CASE WHEN is_indexed THEN 1 ELSE 0 END) AS indexed,
                MAX(recall_date) AS latest_recall_date
            FROM recalls
            GROUP BY agency_code
            ORDER BY agency_code
        """))
        rows = result.mappings().all()

    return {"agencies": [dict(r) for r in rows]}
