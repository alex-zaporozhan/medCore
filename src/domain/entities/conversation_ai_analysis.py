"""AI analysis of conversations for conflict/coaching reports."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ConversationAiAnalysis(Base):
    __tablename__ = "conversation_ai_analysis"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False)
    issue_category: Mapped[str] = mapped_column(String(32), nullable=False)
    is_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    admin_mistakes: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default=text("'[]'::jsonb"))
    business_root_causes: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default=text("'[]'::jsonb"))
    suggested_playbook: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default=text("'[]'::jsonb"))
    raw_ai_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

