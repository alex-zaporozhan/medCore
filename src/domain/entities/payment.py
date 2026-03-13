"""Payment entity model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Payment(Base):
    """Payment model for external provider."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="RUB"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pending|succeeded|canceled|refunded
    provider_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )  # raw provider response
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="ux_payments_provider_id",
        ),
        Index("idx_payments_booking_id", "booking_id"),
    )

