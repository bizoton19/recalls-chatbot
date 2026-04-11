"""
RAG chain for recall queries.

Supports all 3 chat behaviors:
  Level 1 — Keyword/structured search (handled by the search route, fed into context)
  Level 2 — Semantic search via pgvector, LLM synthesizes an answer
  Level 3 — Conversational memory: past messages included as history
"""
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

Guidelines:
- Answer clearly and concisely in plain language (8th grade reading level)
- Always cite the recall number, brand, and date when referencing specific recalls
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
            lines.append(f"More info: {r['url']}")
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


async def answer(
    question: str,
    recalls: list[dict],
    history: list[dict],
    streaming: bool = False,
) -> str | AsyncIterator[str]:
    """
    Generate an answer given a question, retrieved recalls, and chat history.

    Args:
        question:  The user's question.
        recalls:   Recall records retrieved via vector search.
        history:   Prior messages in this chat session.
        streaming: Whether to stream the response token by token.

    Returns:
        Full string answer (streaming=False) or async iterator of tokens (streaming=True).
    """
    chain = build_rag_chain(streaming=streaming)

    inputs = {
        "context": format_recalls_context(recalls),
        "history": build_history(history),
        "question": question,
    }

    if streaming:
        return chain.astream(inputs)
    else:
        return await chain.ainvoke(inputs)
