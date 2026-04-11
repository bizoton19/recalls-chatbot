"""
Jina AI multimodal embedding client — jina-clip-v2 (1024 dims).

Handles both image and text embeddings in the same vector space,
enabling true cross-modal search (image → text, text → image, image → image).

Disabled when JINA_API_KEY is not set. All functions return None gracefully,
and callers skip image search silently. Set JINA_API_KEY to enable.

Docs: https://jina.ai/embeddings
"""
import base64
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

JINA_API_KEY = os.getenv("JINA_API_KEY", "")
JINA_MODEL = "jina-clip-v2"
JINA_DIM = 1024
JINA_API_URL = "https://api.jina.ai/v1/embeddings"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def is_enabled() -> bool:
    return bool(JINA_API_KEY)


async def _call_jina(inputs: list[dict]) -> Optional[list[list[float]]]:
    """POST to Jina embeddings API. Returns list of vectors or None on failure."""
    if not is_enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                JINA_API_URL,
                headers={
                    "Authorization": f"Bearer {JINA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": JINA_MODEL, "input": inputs},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
    except Exception as e:
        logger.error("Jina API error: %s", e)
        return None


async def embed_image_bytes(image_bytes: bytes) -> Optional[list[float]]:
    """Embed a raw image using Jina CLIP. Returns 1024-dim vector or None."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    results = await _call_jina([{"image": b64}])
    return results[0] if results else None


async def embed_image_url(url: str) -> Optional[list[float]]:
    """Embed a remote image URL using Jina CLIP."""
    results = await _call_jina([{"url": url}])
    return results[0] if results else None


async def embed_text(text: str) -> Optional[list[float]]:
    """
    Embed text in the same CLIP vector space as images.
    Enables cross-modal search: text query → find matching product images.
    """
    results = await _call_jina([{"text": text}])
    return results[0] if results else None


async def embed_image_urls_batch(urls: list[str]) -> list[Optional[list[float]]]:
    """Batch-embed multiple image URLs. More efficient than one-by-one."""
    if not urls:
        return []
    inputs = [{"url": url} for url in urls]
    results = await _call_jina(inputs)
    if results is None:
        return [None] * len(urls)
    return results
