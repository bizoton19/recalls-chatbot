"""
Vector store operations — pgvector via raw SQLAlchemy.
Handles indexing recalls and performing similarity search.
"""
import logging
import re
import uuid
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.recall import Recall, RecallEmbedding
from services.vector.embedder import get_embedder

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.35  # cosine similarity floor for /api/recalls/search
# Chat uses a lower floor so short product questions (e.g. "chairs") still get context.
SIMILARITY_THRESHOLD_CHAT = 0.26
DEFAULT_TOP_K = 8

# Tokens below this length are skipped for keyword fallback (after stopword filter).
_KEYWORD_MIN_LEN = 3

_STOPWORDS = frozenset(
    """
    the a an to of in on for is are was were be been being
    have has had do does did will would could should may might must can
    this that these those it its they them their there then than some any all
    each every both few more most other such no nor not only same so too very
    just also or and but if how what when where who why which
    about above after again against before below between through during from into
    out over under until with without within along across behind beyond despite
    except inside near off past since toward towards upon via
    consumer product recall recalls recalled cpsc commission safety federal
    please tell me show find get list my here help
    dont isnt arent wasnt werent hasnt havent hadnt
    """.split()
)


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


def _expand_keyword_tokens(tokens: list[str]) -> list[str]:
    """Add simple singular forms (chairs → chair) for ILIKE matching."""
    out: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        for variant in (t, t[:-1] if len(t) >= 5 and t.endswith("s") and not t.endswith("ss") else None):
            if not variant or variant in seen:
                continue
            seen.add(variant)
            out.append(variant)
    return out[:8]


def _question_keyword_tokens(question: str) -> list[str]:
    raw = re.findall(r"[a-z]{3,}", question.lower())
    picked = [t for t in raw if t not in _STOPWORDS and len(t) >= _KEYWORD_MIN_LEN]
    return _expand_keyword_tokens(picked[:5])


async def keyword_recall_search(
    question: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    agency_codes: Optional[list[str]] = None,
) -> list[dict]:
    """
    Fallback text match when vector similarity returns nothing (short questions, product names).
    """
    tokens = _question_keyword_tokens(question)
    if not tokens:
        return []

    or_clauses: list[str] = []
    params: dict = {"top_k": top_k}
    for i, tok in enumerate(tokens):
        key = f"k{i}"
        params[key] = f"%{tok}%"
        or_clauses.append(
            f"(r.title ILIKE :{key} OR r.description ILIKE :{key} OR "
            f"r.product_name ILIKE :{key} OR r.hazard ILIKE :{key} OR "
            f"r.brand_name ILIKE :{key})"
        )
    kw_or = " OR ".join(or_clauses)

    agency_filter = ""
    if agency_codes:
        agency_filter = " AND r.agency_code = ANY(:agency_codes)"
        params["agency_codes"] = agency_codes

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
            0.55 AS similarity
        FROM recalls r
        WHERE ({kw_or}){agency_filter}
        ORDER BY r.recall_date DESC NULLS LAST
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
    ]


async def similarity_search(
    query: str,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
    agency_codes: Optional[list[str]] = None,
    product_type: Optional[str] = None,
    min_similarity: Optional[float] = None,
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

    floor = SIMILARITY_THRESHOLD if min_similarity is None else min_similarity

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
        if float(row["similarity"]) >= floor
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
