"""WalletTransaction entity model for loyalty wallet movements."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class WalletTransaction(Base):
    """Single loyalty wallet transaction (earn, spend, expire, adjustment)."""

    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False, index=True
    )

    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # earn|spend|expire|adjustment
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    happened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_subscriptions.id"),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    beneficiary_patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True
    )
    family_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_links.id"), nullable=True, index=True
    )

    __table_args__ = (
        Index("idx_wallet_tx_clinic_happened_at", "clinic_id", "happened_at"),
        Index("idx_wallet_tx_clinic_wallet", "clinic_id", "wallet_id"),
    )

