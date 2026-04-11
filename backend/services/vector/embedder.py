"""
Embedding service — text vectors for RAG (pgvector).

Set EMBEDDING_PROVIDER to choose backend (independent of LLM_PROVIDER):

  google (default) → Google models/text-embedding-004, 1536-dim (Matryoshka), same GOOGLE_API_KEY as Gemini
  openai          → text-embedding-3-small (1536 dims)
  ollama          → nomic-embed-text (768 dims — requires schema change to vector(768))

When using Google embeddings, OPENAI_API_KEY is not required for indexing or search.
"""
import os
from typing import Protocol

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "google")
_explicit_model = os.getenv("EMBEDDING_MODEL")
if _explicit_model:
    EMBEDDING_MODEL = _explicit_model
elif EMBEDDING_PROVIDER == "google":
    EMBEDDING_MODEL = "models/text-embedding-004"
else:
    EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))


class EmbedderProtocol(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class GoogleEmbedder:
    """Google Generative Language API — same key as ChatGoogleGenerativeAI."""

    def __init__(self) -> None:
        import google.generativeai as genai

        key = os.getenv("GOOGLE_API_KEY", "")
        if not key:
            raise RuntimeError(
                "GOOGLE_API_KEY is required for EMBEDDING_PROVIDER=google. "
                "Use the same key as for Gemini chat."
            )
        genai.configure(api_key=key)
        self._model = EMBEDDING_MODEL
        self._dims = EMBEDDING_DIMS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import google.generativeai as genai

        out: list[list[float]] = []
        for t in texts:
            r = await genai.embed_content_async(
                model=self._model,
                content=t,
                task_type="retrieval_document",
                output_dimensionality=self._dims,
            )
            out.append(r["embedding"])
        return out

    async def embed_query(self, text: str) -> list[float]:
        import google.generativeai as genai

        r = await genai.embed_content_async(
            model=self._model,
            content=text,
            task_type="retrieval_query",
            output_dimensionality=self._dims,
        )
        return r["embedding"]


class OpenAIEmbedder:
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
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
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            results.append(resp.json()["embedding"])
        return results

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]


def get_embedder() -> EmbedderProtocol:
    if EMBEDDING_PROVIDER == "google":
        return GoogleEmbedder()
    if EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbedder()
    if EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbedder()
    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER!r}. "
        "Choose: google, openai, ollama"
    )
