"""ERP loyalty obligations and their movements for subscription packages."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpLoyaltyObligation(Base):
    """ERP-level obligation created from loyalty subscription sale."""

    __tablename__ = "erp_loyalty_obligations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    customer_subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_subscriptions.id"),
        nullable=False,
        index=True,
    )

    # Monetary representation of obligation in ERP currency (RUB).
    initial_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    remaining_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )  # active|settled|expired

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_erp_loyalty_obligations_clinic_patient",
            "clinic_id",
            "patient_id",
        ),
        Index(
            "idx_erp_loyalty_obligations_subscription",
            "customer_subscription_id",
        ),
    )


class ErpLoyaltyObligationMovement(Base):
    """Single movement on ERP loyalty obligation (sale, write-off, refund)."""

    __tablename__ = "erp_loyalty_obligation_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    obligation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("erp_loyalty_obligations.id"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True
    )
    subscription_usage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_usages.id"),
        nullable=True,
        index=True,
    )

    movement_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # CREATE_FROM_SALE|WRITE_OFF_ON_VISIT|REFUND|ADJUSTMENT
    amount_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )  # positive or negative

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    beneficiary_patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True
    )
    family_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_links.id"), nullable=True, index=True
    )

    __table_args__ = (
        Index(
            "idx_erp_loyalty_obligation_movements_clinic_booking",
            "clinic_id",
            "booking_id",
        ),
    )

