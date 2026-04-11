# CPSC Recalls Chatbot

AI-powered consumer product recall search and conversational assistant, powered by the U.S. Consumer Product Safety Commission (CPSC) recall database at saferproducts.gov.

## Features

- **Latest recalls** — Homepage shows the most recent CPSC recalls with hazard and remedy info
- **Semantic search** — Vector search over the indexed recall database (pgvector)
- **AI chat assistant** — Conversational RAG agent answers natural-language recall questions
- **Source citations** — Every assistant answer cites the specific recalls it used
- **Streaming responses** — Real-time token streaming for instant feedback
- **USWDS 3.x** — Fully compliant with U.S. Web Design System and Section 508

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 + USWDS 3.x |
| Backend | Python FastAPI |
| LLM | OpenAI GPT-4o-mini (swappable via `LLM_PROVIDER`) |
| Vector DB | PostgreSQL 16 + pgvector |
| Recall Data | saferproducts.gov REST API |
| Containers | Docker + Docker Compose |

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env:
#   OPENAI_API_KEY — required for text embeddings (RAG search)
#   GOOGLE_API_KEY — if LLM_PROVIDER=google (Gemini chat)
```

### 2. Start all services

```bash
docker compose up
```

The app will:
- Start PostgreSQL with pgvector
- Start the FastAPI backend (port 8000)
- Start the Next.js frontend (port 3000)
- Automatically pull recent CPSC recalls from saferproducts.gov on first boot
- Index recalls into pgvector for semantic search

Open http://localhost:3000

### 3. Trigger a full historical sync (optional)

```bash
curl -X POST http://localhost:8000/api/admin/ingest \
  -H "x-admin-key: dev-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"full_sync": true}'
```

This fetches all CPSC recall data (30 years) and indexes it into pgvector. Takes ~10–20 minutes.

## Switching LLM Providers

Change `LLM_PROVIDER` in `.env` — no code changes needed:

```bash
# OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Groq (fast, open models)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...

# Ollama (self-hosted, no API key)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recalls/latest` | Latest CPSC recalls |
| GET | `/api/recalls/search?q=...` | Semantic search |
| GET | `/api/recalls/{id}` | Single recall |
| POST | `/api/chat/session` | Create chat session |
| POST | `/api/chat/{token}` | Send message (streaming SSE) |
| GET | `/api/chat/{token}/history` | Chat history |
| POST | `/api/admin/ingest` | Trigger ingestion (requires admin key) |
| GET | `/api/admin/stats` | Ingestion statistics |
| GET | `/health` | Health check |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Next.js Frontend (USWDS 3.x, 508 compliant)        │
│  ├── / (Latest recalls + keyword search)            │
│  └── /chat (Conversational AI assistant)            │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼────────────────────────────────┐
│  FastAPI Backend                                     │
│  ├── /api/recalls  (search, latest, detail)         │
│  ├── /api/chat     (session, message, history)      │
│  └── /api/admin    (ingest trigger, stats)          │
│                                                     │
│  Services:                                          │
│  ├── CPSC API Client (saferproducts.gov)            │
│  ├── Vector Store (pgvector similarity search)      │
│  ├── LLM Provider (OpenAI / Anthropic / Groq / Ollama) │
│  ├── RAG Chain (LangChain, conversational memory)   │
│  └── Ingestion Scheduler (APScheduler, every 6h)   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  PostgreSQL 16 + pgvector                           │
│  ├── recalls (CPSC recall records)                  │
│  ├── recall_embeddings (1536-dim vectors)           │
│  ├── chat_sessions + chat_messages                  │
│  └── ingestion_jobs (audit trail)                   │
└─────────────────────────────────────────────────────┘
```

## Data Source

All recall data is sourced from the publicly available CPSC REST API:
- **Base URL**: https://www.saferproducts.gov/RestWebServices/Recall
- **Format**: JSON
- **Coverage**: Consumer product recalls from ~1974 to present
- **Updates**: Automatically re-synced every 6 hours

## Compliance

- **Section 508 / WCAG 2.1 AA** — Semantic HTML, ARIA labels, keyboard navigation, 4.5:1 contrast
- **USWDS 3.x** — Official U.S. Web Design System components
- **Plain language** — AI responses target 8th grade reading level
- **No PII collected** — Sessions are anonymous; no user accounts required
