"""Idempotency log for omni chat presence events (OPEN/HEARTBEAT/CLOSE)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OmniChatPresenceEvent(Base):
    __tablename__ = "omni_chat_presence_events"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("omni_chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tab_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_event_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event: Mapped[str] = mapped_column(String(16), nullable=False)  # OPEN|HEARTBEAT|CLOSE
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_omni_chat_presence_events_clinic_event", "clinic_id", "client_event_id", unique=True),
        Index("idx_omni_chat_presence_events_clinic_chat", "clinic_id", "chat_id"),
    )

