# CPSC Recalls Chatbot

AI-powered consumer product recall search and conversational assistant. Indexes CPSC recall data from saferproducts.gov with pgvector and provides a natural-language chat interface powered by LangChain.

## Architecture

```
frontend/   Next.js + USWDS 3.x          — recall browse + AI chat UI
backend/    Python FastAPI + LangChain    — API, RAG chain, ingestion
db/         PostgreSQL 16 + pgvector      — recall storage + vector index
```

## Quick Start

```bash
# 1. Copy env file and add your OpenAI key
cp .env.example .env
# Edit .env → set OPENAI_API_KEY

# 2. Start everything
docker compose up

# 3. Open the app
open http://localhost:3000
```

On first startup the backend automatically fetches recent recalls from all agencies and indexes them. Full historical sync can be triggered manually:

```bash
curl -X POST http://localhost:8000/api/admin/ingest \
  -H "X-Admin-Key: dev-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"full_sync": true}'
```

## Switching LLM Providers

Change `LLM_PROVIDER` in `.env` — no code changes needed:

| Provider | `.env` settings |
|----------|----------------|
| OpenAI (default) | `LLM_PROVIDER=openai` + `OPENAI_API_KEY=sk-...` |
| Anthropic Claude | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=sk-ant-...` |
| Groq (fast/cheap) | `LLM_PROVIDER=groq` + `GROQ_API_KEY=gsk_...` |
| Ollama (self-hosted) | `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL=http://host:11434` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recalls/latest` | Latest recalls (filterable by agency) |
| GET | `/api/recalls/search?q=` | Semantic search |
| GET | `/api/recalls/{id}` | Single recall detail |
| POST | `/api/chat/session` | Create anonymous chat session |
| POST | `/api/chat/{token}` | Send message (streaming SSE) |
| GET | `/api/chat/{token}/history` | Chat history |
| POST | `/api/admin/ingest` | Trigger ingestion (requires admin key) |
| GET | `/api/admin/stats` | Index statistics |
| GET | `/health` | Health check |

## Data Source

| Agency | Data | Source |
|--------|------|--------|
| CPSC | Consumer products | saferproducts.gov/RestWebServices/Recall |

## Standards

- USWDS 3.x — U.S. Web Design System
- Section 508 / WCAG 2.1 AA — accessibility
- OWASP Top 10 — backend security
- Cloud agnostic — Docker Compose, runs on any cloud or on-prem
