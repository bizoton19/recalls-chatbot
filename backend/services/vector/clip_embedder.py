"""
CLIP image embedding service.

Uses OpenAI CLIP (ViT-B/32) via the `transformers` + `torch` pipeline locally.
Produces 512-dim vectors that live in the same embedding space as text —
meaning you can find images by text query AND images by uploaded image.

For Railway deployment: runs CPU-only (no GPU needed for ViT-B/32).
First call downloads the model (~350MB) and caches it.
"""
import io
import logging
from functools import lru_cache
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CLIP_DIM = 512


@lru_cache(maxsize=1)
def _load_clip():
    """Load CLIP model once and cache in memory."""
    try:
        from transformers import CLIPProcessor, CLIPModel
        import torch

        model_name = "openai/clip-vit-base-patch32"
        logger.info("Loading CLIP model %s ...", model_name)
        model = CLIPModel.from_pretrained(model_name)
        processor = CLIPProcessor.from_pretrained(model_name)
        model.eval()
        logger.info("CLIP model loaded")
        return model, processor
    except ImportError:
        raise RuntimeError(
            "transformers and torch are required for CLIP embeddings. "
            "Run: pip install transformers torch pillow"
        )


async def embed_image_bytes(image_bytes: bytes) -> list[float]:
    """Embed a raw image (bytes) using CLIP. Returns 512-dim vector."""
    from PIL import Image
    import torch

    model, processor = _load_clip()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)  # normalize

    return features[0].tolist()


async def embed_image_url(url: str) -> Optional[list[float]]:
    """Fetch an image from a URL and CLIP-embed it."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            return await embed_image_bytes(resp.content)
    except Exception as e:
        logger.warning("Failed to embed image %s: %s", url, e)
        return None


async def embed_text_clip(text: str) -> list[float]:
    """
    Embed a text query using CLIP's text encoder.
    Returns a 512-dim vector in the same space as image embeddings —
    enabling cross-modal search (text query → find similar images).
    """
    import torch

    model, processor = _load_clip()

    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)

    with torch.no_grad():
        features = model.get_text_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)

    return features[0].tolist()
