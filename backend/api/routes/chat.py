"""
Chat API routes — conversational recall assistant.

POST /api/chat/session          — create a new chat session
POST /api/chat/{session_token}  — send a message, get a streaming response
GET  /api/chat/{session_token}/history — fetch message history
"""
import logging
import secrets
import uuid
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.recall import ChatSession, ChatMessage
from services.vector.store import similarity_search
from services.llm.rag_chain import answer, format_recalls_context

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

    # Semantic search: find relevant recalls (best-effort — empty list if not indexed yet)
    agency_filter = body.agencies if body.agencies else None
    try:
        recalls = await similarity_search(
            query=body.message,
            db=db,
            top_k=8,
            agency_codes=agency_filter,
        )
    except Exception as e:
        logger.warning("Similarity search failed (embeddings may not be ready): %s", e)
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

    # Update session activity
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session.id)
        .values(last_active_at=datetime.utcnow())
    )

    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    if body.stream:
        return StreamingResponse(
            _stream_response(body.message, recalls, history_dicts, session.id, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        try:
            response_text = await answer(
                question=body.message,
                recalls=recalls,
                history=history_dicts,
                streaming=False,
            )
        except Exception as e:
            _raise_llm_error(e)
        await _save_assistant_message(session.id, response_text, recalls, db)
        return {
            "response": response_text,
            "sources": _sources(recalls),
            "session_token": session_token,
        }


async def _stream_response(
    question: str,
    recalls: list[dict],
    history: list[dict],
    session_id: uuid.UUID,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """Stream response tokens as SSE, then persist the full message."""
    try:
        stream = await answer(question=question, recalls=recalls, history=history, streaming=True)
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
