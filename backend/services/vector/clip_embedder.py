"""
Self-hosted CLIP embedding client — calls the clip-service container.

Mirrors the jina_embedder interface so image_store.py needs only an import swap.
Returns 512-dim vectors matching Vector(512) in recall_images.clip_embedding.

Set CLIP_SERVICE_URL to enable (e.g. http://cpsc-chatbot-clip internally in
Azure Container Apps). Disabled gracefully when the env var is not set.
"""
import base64
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CLIP_SERVICE_URL = os.getenv("CLIP_SERVICE_URL", "").rstrip("/")
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def is_enabled() -> bool:
    return bool(CLIP_SERVICE_URL)


async def _post(path: str, payload: dict) -> Optional[list[float]]:
    if not is_enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{CLIP_SERVICE_URL}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()["embedding"]
    except Exception as exc:
        logger.error("CLIP service error (%s): %s", path, exc)
        return None


async def embed_text(text: str) -> Optional[list[float]]:
    """Embed text in the CLIP vector space (cross-modal: text → image search)."""
    return await _post("/embed/text", {"text": text})


async def embed_image_url(url: str) -> Optional[list[float]]:
    """Embed a remote image URL."""
    return await _post("/embed/image-url", {"url": url})


async def embed_image_bytes(image_bytes: bytes) -> Optional[list[float]]:
    """Embed raw image bytes (base64-encoded before sending)."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return await _post("/embed/image-bytes", {"data": b64})


async def embed_image_urls_batch(urls: list[str]) -> list[Optional[list[float]]]:
    """Embed multiple image URLs sequentially."""
    results = []
    for url in urls:
        results.append(await embed_image_url(url))
    return results
