"""Additional bookings linked to a CRM lead beyond primary_booking_id (CRM_MONEY E7)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class LeadSecondaryBooking(Base):
    """Many bookings per lead for ERP actual_value aggregation."""

    __tablename__ = "lead_secondary_bookings"
    __table_args__ = (
        UniqueConstraint("lead_id", "booking_id", name="uq_lead_secondary_booking"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
