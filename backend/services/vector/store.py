"""
Vector store operations — pgvector via raw SQLAlchemy.
Handles indexing recalls and performing similarity search.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.recall import Recall, RecallEmbedding
from services.vector.embedder import get_embedder

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.35  # cosine distance; lower = more similar
DEFAULT_TOP_K = 8


async def index_recall(recall: Recall, db: AsyncSession) -> None:
    """Embed a recall and store its vector in recall_embeddings."""
    embedder = get_embedder()
    chunk_text = recall.to_chunk_text()

    try:
        embeddings = await embedder.embed([chunk_text])
        vector = embeddings[0]

        # Upsert: delete existing embedding for this recall, then insert
        await db.execute(
            text("DELETE FROM recall_embeddings WHERE recall_id = :rid"),
            {"rid": str(recall.id)}
        )

        embedding_row = RecallEmbedding(
            id=uuid.uuid4(),
            recall_id=recall.id,
            chunk_index=0,
            chunk_text=chunk_text,
            embedding=vector,
        )
        db.add(embedding_row)

        recall.is_indexed = True
        await db.flush()

    except Exception as e:
        logger.error("Failed to index recall %s: %s", recall.id, e)
        raise


async def similarity_search(
    query: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    agency_codes: Optional[list[str]] = None,
    product_type: Optional[str] = None,
) -> list[dict]:
    """
    Find the most semantically similar recalls to the query.

    Returns a list of recall dicts with a similarity score.
    """
    embedder = get_embedder()
    query_vector = await embedder.embed_query(query)

    # Build query using pgvector cosine distance operator (<=>)
    vector_literal = f"'[{','.join(str(v) for v in query_vector)}]'::vector"

    filters = ["r.is_indexed = TRUE"]
    params: dict = {"top_k": top_k}

    if agency_codes:
        filters.append("r.agency_code = ANY(:agency_codes)")
        params["agency_codes"] = agency_codes

    if product_type:
        filters.append("r.product_type ILIKE :product_type")
        params["product_type"] = f"%{product_type}%"

    where_clause = " AND ".join(filters)

    sql = text(f"""
        SELECT
            r.id,
            r.agency_code,
            r.recall_number,
            r.title,
            r.description,
            r.hazard,
            r.remedy,
            r.recall_date,
            r.product_name,
            r.product_type,
            r.brand_name,
            r.manufacturer,
            r.vehicle_make,
            r.vehicle_model,
            r.vehicle_year_from,
            r.vehicle_year_to,
            r.component,
            r.reason_for_recall,
            r.classification,
            r.url,
            r.units_affected,
            1 - (re.embedding <=> {vector_literal}) AS similarity
        FROM recall_embeddings re
        JOIN recalls r ON r.id = re.recall_id
        WHERE {where_clause}
        ORDER BY re.embedding <=> {vector_literal}
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    return [
        {
            **dict(row),
            "id": str(row["id"]),
            "recall_date": row["recall_date"].isoformat() if row["recall_date"] else None,
            "similarity": float(row["similarity"]),
        }
        for row in rows
        if float(row["similarity"]) >= SIMILARITY_THRESHOLD
    ]


async def index_pending(db: AsyncSession, batch_size: int = 50) -> int:
    """Index all recalls that have not yet been embedded. Returns count indexed."""
    result = await db.execute(
        select(Recall).where(Recall.is_indexed == False).limit(batch_size)
    )
    recalls = result.scalars().all()

    indexed = 0
    for recall in recalls:
        try:
            await index_recall(recall, db)
            indexed += 1
        except Exception as e:
            logger.error("Skipping recall %s due to error: %s", recall.id, e)

    return indexed
