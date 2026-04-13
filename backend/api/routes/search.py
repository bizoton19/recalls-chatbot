"""
Unified search API — text-based semantic recall search.

GET  /api/search         — text query, returns ranked recall cards
GET  /api/search/status  — feature flags (image search when CLIP_SERVICE_URL or JINA_API_KEY)
POST /api/search/image   — upload image; needs CLIP/Jina for embeddings (503 when disabled)
"""
import asyncio
import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.vector.store import similarity_search
from services.vector.image_store import search_images_by_image, search_images_by_text
from services.vector import clip_embedder
from services.vector import jina_embedder
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _image_search_enabled() -> bool:
    """True when embeddings can be computed (local clip-service or Jina API)."""
    return clip_embedder.is_enabled() or jina_embedder.is_enabled()


def _image_search_status_note() -> str:
    if not _image_search_enabled():
        return (
            "Set CLIP_SERVICE_URL (local clip-service) or JINA_API_KEY for "
            "image-to-image and text-to-image visual search."
        )
    if clip_embedder.is_enabled():
        return "Local CLIP service — image search enabled."
    return "Jina CLIP active — image search enabled."


# ---------------------------------------------------------------------------
# Feature flag status
# ---------------------------------------------------------------------------

@router.get("/status")
async def search_status():
    """Returns which search features are currently active."""
    return {
        "text_search": True,
        "image_search": _image_search_enabled(),
        "image_search_note": _image_search_status_note(),
    }


# ---------------------------------------------------------------------------
# Text search
# ---------------------------------------------------------------------------

@router.get("")
async def text_search(
    q: str = Query(..., min_length=2),
    top_k: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic text search over recalls using pgvector embeddings.
    When CLIP (local or Jina) is configured, also returns matching product image results.
    """
    recall_task = asyncio.create_task(
        similarity_search(query=q, db=db, top_k=top_k)
    )

    recalls, = await asyncio.gather(recall_task, return_exceptions=True)

    # Image search via CLIP cross-modal — no-op when neither local CLIP nor Jina is configured
    images: list = []
    if _image_search_enabled():
        try:
            images = await search_images_by_text(query=q, db=db, top_k=top_k)
        except Exception as e:
            logger.error("Image search from text failed: %s", e)

    return {
        "query": q,
        "recalls": recalls if not isinstance(recalls, Exception) else [],
        "images": images,
        "image_search_enabled": _image_search_enabled(),
    }


# ---------------------------------------------------------------------------
# Image upload search (requires CLIP embeddings: local clip-service or Jina)
# ---------------------------------------------------------------------------

@router.post("/image")
async def image_search(
    file: UploadFile = File(..., description="Product image to search (JPEG, PNG, WebP)"),
    top_k: int = Form(default=12),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a product photo to find visually similar recalled products.
    Requires CLIP_SERVICE_URL (local) or JINA_API_KEY. Returns HTTP 503 when disabled.

    When enabled:
      1. CLIP embeds the uploaded image
      2. pgvector similarity search finds matching recall product photos
      3. Vision (OpenAI/Gemini if configured) extracts a product description
      4. Text similarity search finds matching recalls
    """
    if not _image_search_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Image search is not enabled. Set CLIP_SERVICE_URL to your clip-service "
                "(e.g. http://clip-service:8001) or set JINA_API_KEY for Jina embeddings."
            ),
        )

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10 MB.")

    image_results_task = asyncio.create_task(
        search_images_by_image(image_bytes, db, top_k=top_k)
    )
    vision_task = asyncio.create_task(
        _describe_image_with_vision(image_bytes)
    )

    image_results, vision_description = await asyncio.gather(
        image_results_task, vision_task, return_exceptions=True
    )

    if isinstance(image_results, Exception):
        logger.error("Image similarity search failed: %s", image_results)
        image_results = []

    if isinstance(vision_description, Exception):
        logger.error("Vision analysis failed: %s", vision_description)
        vision_description = None

    recall_results: list = []
    if vision_description:
        try:
            recall_results = await similarity_search(
                query=vision_description,
                db=db,
                top_k=top_k,
            )
        except Exception as e:
            logger.error("Text search from vision description failed: %s", e)

    return {
        "vision_description": vision_description,
        "images": image_results,
        "recalls": recall_results,
    }


_VISION_PROMPT = (
    "Describe this consumer product in 1-2 sentences focusing on: "
    "product type, brand name (if visible), color, material, and any "
    "model numbers or labels you can read. Be specific and factual. "
    "Do not mention recalls — only describe what you see."
)


async def _describe_image_with_vision(image_bytes: bytes) -> Optional[str]:
    """Extract a product description from an image: OpenAI vision if set, else Gemini."""
    if settings.openai_api_key:
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
                                "detail": "low",
                            },
                        },
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }
            ],
        )
        return response.choices[0].message.content.strip()

    if settings.google_api_key:
        return await _describe_image_with_gemini(image_bytes)

    return None


async def _describe_image_with_gemini(image_bytes: bytes) -> Optional[str]:
    import asyncio
    import io

    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(settings.llm_model or "gemini-2.0-flash")

    def _sync() -> str:
        img = Image.open(io.BytesIO(image_bytes))
        resp = model.generate_content([_VISION_PROMPT, img])
        return (resp.text or "").strip()

    return await asyncio.to_thread(_sync)
