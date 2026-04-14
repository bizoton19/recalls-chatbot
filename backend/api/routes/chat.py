"""
Chat API routes — conversational recall assistant.

POST /api/chat/session          — create a new chat session
POST /api/chat/{session_token}  — send a message, get a streaming response
GET  /api/chat/{session_token}/history — fetch message history
"""
import json
import logging
import secrets
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.recall import ChatSession, ChatMessage
from services.vector.store import (
    SIMILARITY_THRESHOLD_CHAT,
    keyword_recall_search,
    similarity_search,
)
from services.llm.rag_chain import answer, format_recalls_context
from services.llm.router import classify_intent, dispatch_sql_tool, format_tool_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class NewSessionResponse(BaseModel):
    session_token: str


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    agencies: list[str] = Field(default_factory=list)
    stream: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Create session
# ---------------------------------------------------------------------------

@router.post("/session", response_model=NewSessionResponse)
async def create_session(db: AsyncSession = Depends(get_db)):
    """Create an anonymous chat session. Returns a session token."""
    token = secrets.token_urlsafe(32)
    session = ChatSession(id=uuid.uuid4(), session_token=token)
    db.add(session)
    await db.flush()
    return {"session_token": token}


# ---------------------------------------------------------------------------
# Send message
# ---------------------------------------------------------------------------

@router.post("/{session_token}")
async def send_message(
    session_token: str,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and receive an AI-generated response.
    Performs semantic search over recalls before generating the answer.
    Supports streaming (SSE) when body.stream=True.
    """
    # Resolve session
    session = await _get_session(session_token, db)

    # Retrieve conversation history
    history = await _get_history(session.id, db)
    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    # Route based on intent
    intent = classify_intent(body.message)
    recalls: list[dict] = []
    chart: Optional[dict] = None
    context_override: Optional[str] = None

    if intent in ("count", "chart"):
        try:
            tool_result = await dispatch_sql_tool(body.message, db)
            context_override = format_tool_context(tool_result)
            chart = tool_result.get("chart")
            logger.info("SQL tool=%s intent=%s", tool_result.get("tool"), intent)
        except Exception as e:
            logger.warning("SQL tool failed, falling back to RAG: %s", e)

    if context_override is None:
        # Semantic search fallback (also used when SQL tool fails)
        agency_filter = body.agencies if body.agencies else None
        try:
            recalls = await similarity_search(
                query=body.message,
                db=db,
                top_k=12,
                agency_codes=agency_filter,
                min_similarity=SIMILARITY_THRESHOLD_CHAT,
            )
            if not recalls:
                recalls = await keyword_recall_search(
                    body.message,
                    db,
                    top_k=8,
                    agency_codes=agency_filter,
                )
                if recalls:
                    logger.info("Chat RAG: keyword fallback returned %d recalls", len(recalls))
        except Exception as e:
            logger.warning("Similarity search failed: %s", e)
            recalls = []

    # Save user message
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session.id)
        .values(last_active_at=datetime.utcnow())
    )

    if body.stream:
        return StreamingResponse(
            _stream_response(body.message, recalls, history_dicts, session.id, db,
                             context_override=context_override, chart=chart),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        try:
            response_text = await answer(
                question=body.message,
                recalls=recalls,
                history=history_dicts,
                streaming=False,
                context_override=context_override,
            )
        except Exception as e:
            _raise_llm_error(e)
        await _save_assistant_message(session.id, response_text, recalls, db)
        return {
            "response": response_text,
            "sources": _sources(recalls),
            "chart": chart,
            "session_token": session_token,
        }


async def _stream_response(
    question: str,
    recalls: list[dict],
    history: list[dict],
    session_id: uuid.UUID,
    db: AsyncSession,
    context_override: Optional[str] = None,
    chart: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Stream response tokens as SSE, then persist the full message."""
    # Emit chart data before text so the frontend can render it immediately
    if chart:
        yield f"event: chart\ndata: {json.dumps(chart)}\n\n"

    try:
        stream = await answer(
            question=question,
            recalls=recalls,
            history=history,
            streaming=True,
            context_override=context_override,
        )
        full_response = ""
        async for token in stream:
            full_response += token
            yield f"data: {token}\n\n"
    except Exception as e:
        msg = _friendly_llm_error(e)
        yield f"data: {msg}\n\n"
        full_response = msg

    yield f"event: done\ndata: \n\n"

    await _save_assistant_message(session_id, full_response, recalls, db)
    await db.commit()


def _friendly_llm_error(e: Exception) -> str:
    err = str(e)
    if "429" in err or "ResourceExhausted" in err or "quota" in err.lower():
        return (
            "I'm temporarily unavailable due to API rate limits. "
            "Please wait a moment and try again."
        )
    return "I encountered an error generating a response. Please try again."


def _raise_llm_error(e: Exception) -> None:
    msg = _friendly_llm_error(e)
    logger.error("LLM error: %s", e)
    raise HTTPException(status_code=503, detail=msg)


async def _save_assistant_message(
    session_id: uuid.UUID, content: str, recalls: list[dict], db: AsyncSession
):
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content=content,
        sources=_sources(recalls),
    )
    db.add(msg)
    await db.flush()


def _sources(recalls: list[dict]) -> list[dict]:
    return [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "agency_code": r.get("agency_code"),
            "recall_date": r.get("recall_date"),
            "url": r.get("url"),
            "similarity": round(r.get("similarity", 0), 3),
        }
        for r in recalls[:5]
    ]


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.get("/{session_token}/history")
async def get_history(session_token: str, db: AsyncSession = Depends(get_db)):
    session = await _get_session(session_token, db)
    messages = await _get_history(session.id, db)
    return {
        "session_token": session_token,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "sources": m.sources,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_session(token: str, db: AsyncSession) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _get_history(session_id: uuid.UUID, db: AsyncSession) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()
