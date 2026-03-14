"""FinancialTransaction entity model for ERP finance movements."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class FinancialTransaction(Base):
    """Single financial movement within a clinic cashbox."""

    __tablename__ = "financial_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    cashbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cashboxes.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # income|expense|transfer
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="RUB"
    )
    happened_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True
    )
    # Optional links for marketing attribution of revenue
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    visit_attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # manual|booking_completed|refund|...

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
        Index(
            "idx_fin_tx_clinic_happened_at",
            "clinic_id",
            "happened_at",
        ),
        Index(
            "idx_fin_tx_clinic_cashbox",
            "clinic_id",
            "cashbox_id",
        ),
        Index(
            "idx_fin_tx_clinic_visit_attr",
            "clinic_id",
            "visit_attribution_id",
        ),
    )
