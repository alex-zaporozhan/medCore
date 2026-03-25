"""Wallet entity model for loyalty cashback/points balance."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Wallet(Base):
    """Virtual loyalty wallet for a patient within a clinic."""

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )

    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0.00"
    )
    currency: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="POINTS"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_wallets_clinic_id", "clinic_id"),
    )

