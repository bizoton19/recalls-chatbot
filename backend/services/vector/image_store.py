"""
Image vector store — stores and searches Jina CLIP embeddings for recall product images.

All functions return empty results gracefully when Jina is not configured.
Set JINA_API_KEY in your environment to enable image search.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.recall import RecallImage, Recall
from services.vector import jina_embedder

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.20
DEFAULT_TOP_K = 12


async def ingest_recall_images(recall: Recall, db: AsyncSession) -> int:
    """
    Extract image URLs from a recall's raw_data, store records,
    and Jina-embed each image when Jina is enabled.
    Image rows are always persisted; embeddings are added when Jina is available.
    """
    if not recall.raw_data:
        return 0

    image_urls: list[tuple[str, Optional[str]]] = []

    products = recall.raw_data.get("Products") or []
    for product in products:
        url = product.get("ImageURL") or product.get("Image")
        if url and url.startswith("http"):
            alt = product.get("Description") or recall.title
            image_urls.append((url, alt))

    for img in (recall.raw_data.get("Images") or []):
        url = img.get("URL") or img.get("ImageURL")
        if url and url.startswith("http"):
            image_urls.append((url, img.get("Caption")))

    stored = 0
    for idx, (url, alt) in enumerate(image_urls[:5]):
        existing = await db.execute(
            select(RecallImage).where(
                RecallImage.recall_id == recall.id,
                RecallImage.image_index == idx,
            )
        )
        if existing.scalar_one_or_none():
            continue

        embedding: Optional[list[float]] = None
        if jina_embedder.is_enabled():
            embedding = await jina_embedder.embed_image_url(url)

        img_row = RecallImage(
            id=uuid.uuid4(),
            recall_id=recall.id,
            image_url=url,
            image_index=idx,
            alt_text=alt,
            clip_embedding=embedding,
            is_embedded=embedding is not None,
        )
        db.add(img_row)
        stored += 1

    await db.flush()
    return stored


async def image_similarity_search(
    query_vector: list[float],
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """Find the most visually similar recall product images to a query vector."""
    vector_literal = f"'[{','.join(str(v) for v in query_vector)}]'::vector"

    sql = text(f"""
        SELECT
            ri.id            AS image_id,
            ri.image_url,
            ri.alt_text,
            ri.recall_id,
            r.title,
            r.agency_code,
            r.recall_number,
            r.recall_date,
            r.hazard,
            r.remedy,
            r.brand_name,
            r.manufacturer,
            r.product_type,
            r.url            AS recall_url,
            1 - (ri.clip_embedding <=> {vector_literal}) AS similarity
        FROM recall_images ri
        JOIN recalls r ON r.id = ri.recall_id
        WHERE ri.clip_embedding IS NOT NULL
        ORDER BY ri.clip_embedding <=> {vector_literal}
        LIMIT :top_k
    """)

    result = await db.execute(sql, {"top_k": top_k})
    rows = result.mappings().all()

    return [
        {
            **dict(row),
            "recall_id": str(row["recall_id"]),
            "image_id": str(row["image_id"]),
            "recall_date": row["recall_date"].isoformat() if row["recall_date"] else None,
            "similarity": float(row["similarity"]),
        }
        for row in rows
        if float(row["similarity"]) >= SIMILARITY_THRESHOLD
    ]


async def search_images_by_text(query: str, db: AsyncSession, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Find recall product images matching a text query (cross-modal CLIP search)."""
    if not jina_embedder.is_enabled():
        return []
    query_vector = await jina_embedder.embed_text(query)
    if not query_vector:
        return []
    return await image_similarity_search(query_vector, db, top_k=top_k)


async def search_images_by_image(image_bytes: bytes, db: AsyncSession, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Find recall product images visually similar to an uploaded image."""
    if not jina_embedder.is_enabled():
        return []
    query_vector = await jina_embedder.embed_image_bytes(image_bytes)
    if not query_vector:
        return []
    return await image_similarity_search(query_vector, db, top_k=top_k)
