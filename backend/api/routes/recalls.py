from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.recall import Recall
from services.vector.store import similarity_search
from api.recall_serialize import prune_empty_vehicle_fields

router = APIRouter(prefix="/recalls", tags=["recalls"])

@router.get("/latest")
async def get_latest_recalls(
    limit: int = Query(default=20, ge=1, le=100),
    product_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent CPSC recalls, optionally filtered by product type."""
    q = (
        select(Recall)
        .options(selectinload(Recall.images))
        .where(Recall.agency_code == "CPSC")
        .order_by(desc(Recall.recall_date), desc(Recall.created_at))
        .limit(limit)
    )
    if product_type:
        q = q.where(Recall.product_type.ilike(f"%{product_type}%"))

    result = await db.execute(q)
    recalls = result.scalars().all()
    return {"recalls": [_serialize(r) for r in recalls], "total": len(recalls)}


@router.get("/search")
async def search_recalls(
    q: str = Query(..., min_length=2, description="Search query"),
    agencies: Optional[str] = Query(default=None, description="Comma-separated agency codes"),
    product_type: Optional[str] = Query(default=None),
    top_k: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search over indexed recalls using pgvector.
    Returns ranked results with similarity scores.
    """
    agency_filter = [a.strip().upper() for a in agencies.split(",")] if agencies else None

    results = await similarity_search(
        query=q,
        db=db,
        top_k=top_k,
        agency_codes=agency_filter,
        product_type=product_type,
    )

    cleaned = [prune_empty_vehicle_fields({**r}) for r in results]
    return {"query": q, "results": cleaned, "total": len(cleaned)}


@router.get("/{recall_id}")
async def get_recall(recall_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch a single recall by its UUID."""
    result = await db.execute(select(Recall).where(Recall.id == recall_id))
    recall = result.scalar_one_or_none()
    if not recall:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recall not found")
    return _serialize(recall)


def _serialize(r: Recall) -> dict:
    # Pick the first image by image_index if available
    first_image = None
    if hasattr(r, "images") and r.images:
        sorted_imgs = sorted(r.images, key=lambda i: i.image_index)
        if sorted_imgs:
            first_image = sorted_imgs[0].image_url

    out: dict = {
        "id": str(r.id),
        "agency_code": r.agency_code,
        "recall_number": r.recall_number,
        "title": r.title,
        "description": r.description,
        "hazard": r.hazard,
        "remedy": r.remedy,
        "recall_date": r.recall_date.isoformat() if r.recall_date else None,
        "product_name": r.product_name,
        "product_type": r.product_type,
        "brand_name": r.brand_name,
        "manufacturer": r.manufacturer,
        "classification": r.classification,
        "units_affected": r.units_affected,
        "url": r.url,
        "image_url": first_image,
    }
    # Vehicle fields exist for non-CPSC agencies (e.g. future NHTSA). CPSC JSON has none — omit when empty.
    if r.vehicle_make or r.vehicle_model or r.vehicle_year_from is not None or r.vehicle_year_to is not None or r.component:
        out["vehicle_make"] = r.vehicle_make
        out["vehicle_model"] = r.vehicle_model
        out["vehicle_year_from"] = r.vehicle_year_from
        out["vehicle_year_to"] = r.vehicle_year_to
        out["component"] = r.component
    if r.manufacturer_countries:
        out["manufacturer_countries"] = r.manufacturer_countries
    if r.last_publish_date:
        out["last_publish_date"] = r.last_publish_date.isoformat()
    return prune_empty_vehicle_fields(out)
