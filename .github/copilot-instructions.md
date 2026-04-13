# recalls-chatbot — Copilot / AI assistant instructions

Repository: **CPSC Recalls Chatbot** — Next.js 15 (USWDS) frontend, FastAPI backend, PostgreSQL + pgvector, LangChain RAG. Public recall data from saferproducts.gov.

## Chat assistant output (backend)

When editing `backend/services/llm/rag_chain.py` or prompts for the recall assistant:

- Answers should use **GitHub-flavored Markdown** suitable for chat.
- **Numbered lists**: Always insert a **blank line** between the lead-in sentence and `1.` (avoid `...text:1.` run together).
- **Between recalls**: Blank line between each numbered item for scanability.
- Prefer `**Label:** value` lines inside each recall block.
- Cite **recall_number, dates, URLs** from RAG context; do not invent "Not specified" — if missing, state that the detail is not in the retrieved record.
- Links: `[label](url)` with the real CPSC/saferproducts URL from context.

## Chat UI (frontend)

When editing `frontend/src/app/chat/**` or chat API client:

- Assistant content should be shown through a **Markdown renderer** (e.g. `react-markdown` + sanitization) for **streaming and final** bubbles, not plain text only, so `**bold**` and links render.
- External links: `target="_blank"` and `rel="noopener noreferrer"` where appropriate.

## Streaming client (`frontend/src/lib/api.ts`)

- Stream completion: only invoke the done handler when the SSE **`event: done`** is received — **do not** treat arbitrary empty `data:` lines as end-of-stream (prevents duplicate messages).

## Cursor parity

Team members using Cursor have the same conventions in `.cursor/rules/cpsc-chat-formatting.mdc`.

## Further plans

See `docs/advanced-search-plan.md` for advanced search / deep-link UX (not implemented in code by default).
