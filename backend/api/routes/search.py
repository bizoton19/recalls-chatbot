"""
Unified search API — handles both text and image queries,
returning two result types: recall cards + image matches.

POST /api/search/image  — upload an image file
GET  /api/search        — text query returning both result types
"""
import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.vector.store import similarity_search
from services.vector.image_store import search_images_by_image, search_images_by_text
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ---------------------------------------------------------------------------
# Text search — returns recalls + image results
# ---------------------------------------------------------------------------

@router.get("")
async def text_search(
    q: str = Query(..., min_length=2),
    top_k: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified text search over recalls and product images.
    Returns two result sets:
      - recalls: ranked recall cards (text RAG)
      - images:  visually matching product photos (CLIP cross-modal)
    """
    # Run text RAG search and CLIP image search in parallel
    import asyncio

    recall_task = asyncio.create_task(
        similarity_search(query=q, db=db, top_k=top_k)
    )
    image_task = asyncio.create_task(
        search_images_by_text(query=q, db=db, top_k=top_k)
    )

    recalls, images = await asyncio.gather(recall_task, image_task, return_exceptions=True)

    return {
        "query": q,
        "recalls": recalls if not isinstance(recalls, Exception) else [],
        "images": images if not isinstance(images, Exception) else [],
    }


# ---------------------------------------------------------------------------
# Image upload search
# ---------------------------------------------------------------------------

@router.post("/image")
async def image_search(
    file: UploadFile = File(..., description="Product image to search (JPEG, PNG, WebP)"),
    top_k: int = Form(default=12),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a product photo to find visually similar recalled products.

    Flow:
      1. Validate and read uploaded image
      2. CLIP-embed the image (512-dim vector)
      3. pgvector similarity search → matching recall product photos
      4. GPT-4o-mini vision → extract product description from the photo
      5. Text similarity search using that description → matching recalls
      6. Return both result sets
    """
    # Validate
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP."
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10 MB.")

    import asyncio

    # Run CLIP visual search
    image_results_task = asyncio.create_task(
        search_images_by_image(image_bytes, db, top_k=top_k)
    )

    # Run GPT-4o-mini vision to get product description
    vision_task = asyncio.create_task(
        _describe_image_with_vision(image_bytes)
    )

    image_results, vision_description = await asyncio.gather(
        image_results_task, vision_task, return_exceptions=True
    )

    if isinstance(image_results, Exception):
        logger.error("CLIP search failed: %s", image_results)
        image_results = []

    if isinstance(vision_description, Exception):
        logger.error("Vision analysis failed: %s", vision_description)
        vision_description = None

    # Text search using vision description
    recall_results = []
    if vision_description:
        try:
            recall_results = await similarity_search(
                query=vision_description,
                db=db,
                top_k=top_k,
            )
        except Exception as e:
            logger.error("Text search from vision failed: %s", e)

    return {
        "vision_description": vision_description,
        "images": image_results,
        "recalls": recall_results,
    }


async def _describe_image_with_vision(image_bytes: bytes) -> str:
    """
    Use GPT-4o-mini vision to extract a product description from an image.
    Returns a text description suitable for recall search.
    """
    if not settings.openai_api_key:
        return ""

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "low",  # cheaper, sufficient for product ID
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe this consumer product in 1–2 sentences focusing on: "
                            "product type, brand name (if visible), color, material, and any "
                            "model numbers or labels you can read. Be specific and factual. "
                            "Do not mention recalls — only describe what you see."
                        ),
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content.strip()
