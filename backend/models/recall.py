from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, BigInteger, SmallInteger, Boolean,
    Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Index,
    ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
import uuid

from db.database import Base


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    api_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    recalls: Mapped[list["Recall"]] = relationship(back_populates="agency_rel")


class Recall(Base):
    __tablename__ = "recalls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_code: Mapped[str] = mapped_column(String(20), ForeignKey("agencies.code"), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(500))
    recall_number: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    hazard: Mapped[Optional[str]] = mapped_column(Text)
    remedy: Mapped[Optional[str]] = mapped_column(Text)
    recall_date: Mapped[Optional[date]] = mapped_column(Date)
    units_affected: Mapped[Optional[int]] = mapped_column(BigInteger)
    url: Mapped[Optional[str]] = mapped_column(String(1000))

    product_name: Mapped[Optional[str]] = mapped_column(Text)
    product_description: Mapped[Optional[str]] = mapped_column(Text)
    product_type: Mapped[Optional[str]] = mapped_column(String(255))
    brand_name: Mapped[Optional[str]] = mapped_column(Text)
    manufacturer: Mapped[Optional[str]] = mapped_column(Text)
    model_numbers: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    vehicle_make: Mapped[Optional[str]] = mapped_column(String(255))
    vehicle_model: Mapped[Optional[str]] = mapped_column(String(255))
    vehicle_year_from: Mapped[Optional[int]] = mapped_column(SmallInteger)
    vehicle_year_to: Mapped[Optional[int]] = mapped_column(SmallInteger)
    component: Mapped[Optional[str]] = mapped_column(String(500))

    product_quantity: Mapped[Optional[str]] = mapped_column(Text)
    distribution_pattern: Mapped[Optional[str]] = mapped_column(Text)
    reason_for_recall: Mapped[Optional[str]] = mapped_column(Text)
    classification: Mapped[Optional[str]] = mapped_column(String(50))

    manufacturer_countries: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    last_publish_date: Mapped[Optional[date]] = mapped_column(Date)

    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    agency_rel: Mapped[Agency] = relationship(back_populates="recalls")
    embeddings: Mapped[list["RecallEmbedding"]] = relationship(
        back_populates="recall", cascade="all, delete-orphan"
    )
    images: Mapped[list["RecallImage"]] = relationship(
        back_populates="recall", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("agency_code", "external_id"),
    )

    def to_chunk_text(self) -> str:
        """Produce the text that gets embedded for RAG."""
        parts = [
            f"Recall: {self.title}",
            f"Agency: {self.agency_code}",
        ]
        if self.recall_date:
            parts.append(f"Date: {self.recall_date.isoformat()}")
        if self.product_name:
            parts.append(f"Product: {self.product_name}")
        if self.brand_name:
            parts.append(f"Brand: {self.brand_name}")
        if self.manufacturer:
            parts.append(f"Manufacturer: {self.manufacturer}")
        if self.manufacturer_countries:
            parts.append(f"Country of manufacture: {', '.join(self.manufacturer_countries)}")
        if self.vehicle_make:
            parts.append(f"Vehicle: {self.vehicle_make} {self.vehicle_model or ''} ({self.vehicle_year_from}–{self.vehicle_year_to})")
        if self.hazard:
            parts.append(f"Hazard: {self.hazard}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.remedy:
            parts.append(f"Remedy: {self.remedy}")
        return "\n".join(parts)


class RecallEmbedding(Base):
    __tablename__ = "recall_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recalls.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(SmallInteger, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    recall: Mapped[Recall] = relationship(back_populates="embeddings")

    __table_args__ = (
        UniqueConstraint("recall_id", "chunk_index"),
    )


class RecallImage(Base):
    __tablename__ = "recall_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recall_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recalls.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_index: Mapped[int] = mapped_column(SmallInteger, default=0)
    alt_text: Mapped[Optional[str]] = mapped_column(Text)
    local_path: Mapped[Optional[str]] = mapped_column(Text)
    clip_embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(512))
    is_embedded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    recall: Mapped[Recall] = relationship(back_populates="images")

    __table_args__ = (
        UniqueConstraint("recall_id", "image_index"),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[list]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="chk_role"),
    )
