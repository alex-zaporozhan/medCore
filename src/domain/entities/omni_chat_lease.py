"""Ephemeral presence lease for omni-chat (no-buttons automation support)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OmniChatLease(Base):
    __tablename__ = "omni_chat_leases"

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
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, index=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_omni_chat_leases_clinic_chat_expires", "clinic_id", "chat_id", "expires_at"),
        Index("idx_omni_chat_leases_clinic_admin_expires", "clinic_id", "admin_id", "expires_at"),
        Index("idx_omni_chat_leases_chat_tab", "chat_id", "tab_id"),
    )

