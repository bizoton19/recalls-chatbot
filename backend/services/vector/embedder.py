"""
Embedding service — provider-agnostic.
Reads LLM_PROVIDER env var to choose the embedding backend.

Supported:
  openai   → text-embedding-3-small (1536 dims)
  ollama   → nomic-embed-text (768 dims — requires schema change)
"""
import os
import logging
from typing import Protocol

logger = logging.getLogger(__name__)

PROVIDER = os.getenv("LLM_PROVIDER", "openai")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS = 1536  # text-embedding-3-small; change to 768 for nomic-embed-text


class EmbedderProtocol(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbedder:
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Batch in chunks of 100 (OpenAI limit)
        results = []
        for i in range(0, len(texts), 100):
            batch = texts[i:i + 100]
            response = await self.client.embeddings.create(model=self.model, input=batch)
            results.extend(item.embedding for item in response.data)
        return results

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0]


class OllamaEmbedder:
    def __init__(self):
        import httpx
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            resp = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            resp.raise_for_status()
            results.append(resp.json()["embedding"])
        return results

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]


def get_embedder() -> EmbedderProtocol:
    if PROVIDER == "ollama":
        return OllamaEmbedder()
    return OpenAIEmbedder()
