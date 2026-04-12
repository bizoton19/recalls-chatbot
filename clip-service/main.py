"""
CLIP Embedding Microservice — open-clip ViT-B/32 (512-dim).

Endpoints:
  GET  /health
  POST /embed/text        {"text": "..."}
  POST /embed/image-url   {"url": "https://..."}
  POST /embed/image-bytes {"data": "<base64>"}

All embeddings are L2-normalised 512-dim float vectors, matching
the recall_images.clip_embedding Vector(512) column in Postgres.
"""
import base64
import io
import logging
import os

import httpx
import open_clip
import torch
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="CLIP Embedding Service", version="1.0.0")

_model = None
_preprocess = None
_tokenizer = None

MODEL_NAME = os.getenv("CLIP_MODEL", "ViT-B-32")
PRETRAINED = os.getenv("CLIP_PRETRAINED", "openai")


@app.on_event("startup")
def load_model() -> None:
    global _model, _preprocess, _tokenizer
    logger.info("Loading CLIP model %s (%s)…", MODEL_NAME, PRETRAINED)
    _model, _, _preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED
    )
    _model.eval()
    _tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    logger.info("CLIP model ready")


# ── schemas ──────────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str

class ImageUrlRequest(BaseModel):
    url: str

class ImageBytesRequest(BaseModel):
    data: str  # base64-encoded image bytes

class EmbedResponse(BaseModel):
    embedding: list[float]


# ── helpers ───────────────────────────────────────────────────────────────────

def _encode_image(image: Image.Image) -> list[float]:
    tensor = _preprocess(image).unsqueeze(0)
    with torch.no_grad():
        features = _model.encode_image(tensor)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()


def _encode_text(text: str) -> list[float]:
    tokens = _tokenizer([text])
    with torch.no_grad():
        features = _model.encode_text(tokens)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/embed/text", response_model=EmbedResponse)
def embed_text(req: TextRequest) -> EmbedResponse:
    if _model is None:
        raise HTTPException(503, "Model not loaded yet")
    return EmbedResponse(embedding=_encode_text(req.text))


@app.post("/embed/image-url", response_model=EmbedResponse)
async def embed_image_url(req: ImageUrlRequest) -> EmbedResponse:
    if _model is None:
        raise HTTPException(503, "Model not loaded yet")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()
        image = Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, f"Could not fetch image: {exc}") from exc
    return EmbedResponse(embedding=_encode_image(image))


@app.post("/embed/image-bytes", response_model=EmbedResponse)
def embed_image_bytes(req: ImageBytesRequest) -> EmbedResponse:
    if _model is None:
        raise HTTPException(503, "Model not loaded yet")
    try:
        data = base64.b64decode(req.data)
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, f"Could not decode image: {exc}") from exc
    return EmbedResponse(embedding=_encode_image(image))
