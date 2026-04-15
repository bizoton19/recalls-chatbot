"""
RAG chain for recall queries.

Supports all 3 chat behaviors:
  Level 1 — Keyword/structured search (handled by the search route, fed into context)
  Level 2 — Semantic search via pgvector, LLM synthesizes an answer
  Level 3 — Conversational memory: past messages included as history
"""
import asyncio
import logging
from typing import AsyncIterator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from .provider import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful consumer safety assistant for the U.S. Consumer Product Safety Commission (CPSC).
You help the public find information about consumer product recalls from the CPSC recall database at saferproducts.gov.

You can help with questions like:
- "Is my [product] recalled?"
- "What products has [brand] recalled?"
- "Are there any recalls related to [hazard type]?"
- "What should I do if my product is recalled?"

Formatting (GitHub-flavored Markdown — the UI renders this). Follow these rules strictly:
- Use **bold** for labels: **Recall number:**, **Brand:**, **Date:**, **Hazard:**, **Remedy:**.
- When you list two or more recalls, you MUST use a Markdown ordered list (`1.` `2.` …). 
- Critical spacing: end your intro paragraph with a period, then insert TWO line breaks before `1.` — never run the intro into the list. Forbidden: `details:1.` or any `word:1.` on one line; the colon before `1` must not touch the numeral.
- Put one blank line between each numbered item so each recall is visually separate.
- Inside each list item, put each field on its own line (after the opening `1.` line, break before **Brand:**, etc.). Keep paragraphs inside an item readable; avoid one giant run-on sentence.
- For the official notice link, use [View recall on CPSC.gov](URL) with the exact URL from the context — not plain text like "More info: CPSC Recall Notice".
- Do not write "Not specified" for recall number, brand, or date when the context below includes them; copy values from the context.

Example shape when multiple recalls are in context (structure only):

Yes, there are recalls that match.

1. **Recall number:** 26-XXX  
**Brand:** Example Brand  
**Date:** April 1, 2026  
**Hazard:** …  
**Remedy:** …  
[View recall on CPSC.gov](https://www.cpsc.gov/...)

2. **Recall number:** 26-YYY  
**Brand:** …  
(etc.)

Guidelines:
- Answer clearly and concisely in plain language (8th grade reading level)
- Cite recall number, brand, and date when they appear in the context
- If you don't find a specific recall in the context provided, say so honestly — never guess
- Never fabricate recall information — only reference what is in the provided context
- If a product is under recall, clearly state the hazard and the remedy (refund, repair, replacement)
- Recommend users visit saferproducts.gov or call the CPSC hotline (800-638-2772) for the most current information
- Be empathetic — recalls can affect families and children's safety

Context from CPSC recall database:
{context}"""


def build_rag_chain(streaming: bool = False):
    """Build the conversational RAG chain."""
    llm = get_llm(temperature=0.1, streaming=streaming)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    return prompt | llm | StrOutputParser()


def format_recalls_context(recalls: list[dict]) -> str:
    """Format retrieved recall records into LLM context."""
    if not recalls:
        return "No specific recall records found matching this query."

    parts = []
    for i, r in enumerate(recalls[:8], 1):  # cap at 8 to stay within token limits
        lines = [f"[Recall {i}]"]
        lines.append(f"Title: {r.get('title', 'Unknown')}")
        lines.append(f"Agency: {r.get('agency_code', 'Unknown')}")
        if r.get("recall_number"):
            lines.append(f"Recall number: {r['recall_number']}")
        if r.get("recall_date"):
            lines.append(f"Date: {r['recall_date']}")
        if r.get("product_name"):
            lines.append(f"Product: {r['product_name']}")
        if r.get("brand_name"):
            lines.append(f"Brand: {r['brand_name']}")
        if r.get("manufacturer"):
            lines.append(f"Manufacturer: {r['manufacturer']}")
        if r.get("vehicle_make"):
            year_range = f"{r.get('vehicle_year_from', '?')}–{r.get('vehicle_year_to', '?')}"
            lines.append(f"Vehicle: {r['vehicle_make']} {r.get('vehicle_model', '')} ({year_range})")
        if r.get("hazard"):
            lines.append(f"Hazard: {r['hazard']}")
        if r.get("description"):
            lines.append(f"Description: {r['description'][:400]}")
        if r.get("remedy"):
            lines.append(f"Remedy: {r['remedy']}")
        if r.get("url"):
            lines.append(f"Official URL (use in markdown link): {r['url']}")
        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)


def build_history(messages: list[dict]) -> list:
    """Convert stored chat messages to LangChain message objects."""
    history = []
    for msg in messages[-10:]:  # last 10 messages for context window
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history


def _is_rate_limit(e: Exception) -> bool:
    err = str(e)
    return "429" in err or "ResourceExhausted" in err or "quota" in err.lower()


async def answer(
    question: str,
    recalls: list[dict],
    history: list[dict],
    streaming: bool = False,
    max_retries: int = 3,
    context_override: str | None = None,
) -> str | AsyncIterator[str]:
    """
    Generate an answer given a question, retrieved recalls, and chat history.
    Pass context_override to use SQL tool results instead of RAG context.
    """
    inputs = {
        "context": context_override if context_override is not None else format_recalls_context(recalls),
        "history": build_history(history),
        "question": question,
    }

    if streaming:
        return _stream_with_retry(inputs, max_retries)

    chain = build_rag_chain(streaming=False)
    for attempt in range(max_retries):
        try:
            return await chain.ainvoke(inputs)
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_retries - 1:
                wait = 20 * (attempt + 1)
                logger.warning("LLM rate limit, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
                continue
            raise


async def _stream_with_retry(inputs: dict, max_retries: int = 3) -> AsyncIterator[str]:  # noqa: E303
    """Async generator that streams LLM tokens and retries the whole call on rate limits."""
    chain = build_rag_chain(streaming=True)
    for attempt in range(max_retries):
        try:
            async for token in chain.astream(inputs):
                yield token
            return
        except Exception as e:
            if _is_rate_limit(e) and attempt < max_retries - 1:
                wait = 20 * (attempt + 1)
                logger.warning("LLM rate limit during stream, retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
                continue
            raise
