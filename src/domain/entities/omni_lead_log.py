"""Immutable lead log snapshot for omnichannel chats.

Each resolved omni-chat produces a single lead log entry with transcript snapshot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OmniLeadLog(Base):
    __tablename__ = "omni_lead_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    omni_chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("omni_chats.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("omni_contacts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opened_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, server_default="Обращение")
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="UNKNOWN", index=True
    )  # BOOKED | NOT_BOOKED | UNKNOWN
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    transcript_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_cards.id", ondelete="SET NULL"), nullable=True, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_omni_lead_logs_clinic_closed_at", "clinic_id", "closed_at"),
        Index("idx_omni_lead_logs_clinic_outcome_closed_at", "clinic_id", "outcome", "closed_at"),
        Index("idx_omni_lead_logs_clinic_contact_closed_at", "clinic_id", "contact_id", "closed_at"),
    )

