"""
Recall ingestion pipeline.

Flow:
  1. Fetch records from each agency API client
  2. Upsert into the recalls table
  3. Queue new/updated recalls for embedding
  4. Embed pending recalls in batches
  5. Log results to ingestion_jobs table

Scheduled every INGESTION_SCHEDULE_HOURS hours via APScheduler.
Also triggered manually via POST /api/admin/ingest.
"""
import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.database import get_db_context
from models.recall import Recall
from services.recalls import ALL_CLIENTS, RecallRecord
from services.vector.store import index_pending
from services.vector.image_store import ingest_recall_images

logger = logging.getLogger(__name__)


def record_to_dict(r: RecallRecord) -> dict:
    return {
        "agency_code": r.agency_code,
        "external_id": r.external_id,
        "recall_number": r.recall_number,
        "title": r.title,
        "description": r.description,
        "hazard": r.hazard,
        "remedy": r.remedy,
        "recall_date": r.recall_date,
        "units_affected": r.units_affected,
        "url": r.url,
        "product_name": r.product_name,
        "product_description": r.product_description,
        "product_type": r.product_type,
        "brand_name": r.brand_name,
        "manufacturer": r.manufacturer,
        "model_numbers": r.model_numbers or [],
        "vehicle_make": r.vehicle_make,
        "vehicle_model": r.vehicle_model,
        "vehicle_year_from": r.vehicle_year_from,
        "vehicle_year_to": r.vehicle_year_to,
        "component": r.component,
        "product_quantity": r.product_quantity,
        "distribution_pattern": r.distribution_pattern,
        "reason_for_recall": r.reason_for_recall,
        "classification": r.classification,
        "raw_data": r.raw_data,
        "is_indexed": False,
        "updated_at": datetime.utcnow(),
    }


async def upsert_recalls(records: list[RecallRecord], db) -> tuple[int, int]:
    """Upsert recall records. Returns (new_count, updated_count)."""
    new_count = 0
    updated_count = 0

    for record in records:
        if not record.external_id:
            continue

        row = record_to_dict(record)

        # Check existence
        existing = await db.execute(
            select(Recall).where(
                Recall.agency_code == record.agency_code,
                Recall.external_id == record.external_id,
            )
        )
        existing_recall = existing.scalar_one_or_none()

        if existing_recall:
            # Update only if title or key fields changed
            changed = (
                existing_recall.title != record.title
                or existing_recall.hazard != record.hazard
                or existing_recall.remedy != record.remedy
            )
            if changed:
                for key, value in row.items():
                    if key not in ("agency_code", "external_id"):
                        setattr(existing_recall, key, value)
                existing_recall.is_indexed = False  # re-embed on change
                updated_count += 1
        else:
            new_recall = Recall(id=uuid.uuid4(), **row)
            db.add(new_recall)
            new_count += 1

    await db.flush()
    return new_count, updated_count


async def run_ingestion(full_sync: bool = False) -> dict:
    """
    Main ingestion entry point.

    Args:
        full_sync: If True, fetch all historical recalls. Otherwise, fetch recent only.
    """
    logger.info("Starting recall ingestion (full_sync=%s)", full_sync)
    summary = {
        "started_at": datetime.utcnow().isoformat(),
        "full_sync": full_sync,
        "agencies": {},
        "total_fetched": 0,
        "total_new": 0,
        "total_updated": 0,
        "total_indexed": 0,
        "errors": [],
    }

    async with get_db_context() as db:
        for client in ALL_CLIENTS:
            agency = client.agency_code
            logger.info("Fetching recalls from %s ...", agency)

            try:
                if full_sync:
                    records = await client.fetch_all()
                else:
                    records = await client.fetch_recent()

                new_count, updated_count = await upsert_recalls(records, db)

                summary["agencies"][agency] = {
                    "fetched": len(records),
                    "new": new_count,
                    "updated": updated_count,
                }
                summary["total_fetched"] += len(records)
                summary["total_new"] += new_count
                summary["total_updated"] += updated_count

                logger.info(
                    "%s: fetched=%d new=%d updated=%d",
                    agency, len(records), new_count, updated_count
                )

            except Exception as e:
                logger.error("Ingestion failed for %s: %s", agency, e)
                summary["errors"].append({"agency": agency, "error": str(e)})

        # Text-embed all pending recalls
        logger.info("Text-embedding pending recalls ...")
        indexed = 0
        while True:
            batch_indexed = await index_pending(db, batch_size=50)
            indexed += batch_indexed
            if batch_indexed == 0:
                break
            logger.info("Text-indexed %d recalls so far ...", indexed)

        summary["total_indexed"] = indexed

        # CLIP-embed product images for newly ingested recalls
        logger.info("CLIP-embedding recall product images ...")
        images_stored = 0
        result = await db.execute(
            select(Recall).where(Recall.agency_code == "CPSC").limit(500)
        )
        recalls_for_images = result.scalars().all()
        for recall in recalls_for_images:
            try:
                count = await ingest_recall_images(recall, db)
                images_stored += count
            except Exception as e:
                logger.warning("Image ingestion failed for recall %s: %s", recall.id, e)

        summary["total_images_stored"] = images_stored
        logger.info("Stored %d product images", images_stored)
        summary["finished_at"] = datetime.utcnow().isoformat()
        logger.info("Ingestion complete: %s", summary)

    return summary


def start_scheduler():
    """Start the APScheduler background scheduler for periodic ingestion."""
    import os
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    hours = int(os.getenv("INGESTION_SCHEDULE_HOURS", "6"))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_ingestion,
        trigger="interval",
        hours=hours,
        id="recall_ingestion",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Ingestion scheduler started — runs every %d hours", hours)
    return scheduler
