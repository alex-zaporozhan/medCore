"""Notification entity model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    ForeignKey,
    Index,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Notification(Base):
    """Notification log entry."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True, index=True
    )
    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_notifications_booking_id", "booking_id"),
        Index("idx_notifications_patient_id", "patient_id"),
    )

