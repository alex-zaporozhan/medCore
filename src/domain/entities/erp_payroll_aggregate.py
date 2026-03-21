"""Pre-aggregated ERP payroll rows (Engine L2)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, PrimaryKeyConstraint, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpPayrollAggregate(Base):
    """Same grain as ``get_visit_payroll_by_period`` (salary_transactions GROUP BY)."""

    __tablename__ = "erp_payroll_aggregate"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_bucket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start_is_null: Mapped[bool] = mapped_column(Boolean, nullable=False)
    period_start_key: Mapped[date] = mapped_column(Date(), nullable=False)
    period_end_is_null: Mapped[bool] = mapped_column(Boolean, nullable=False)
    period_end_key: Mapped[date] = mapped_column(Date(), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    updated_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "clinic_id",
            "doctor_id",
            "booking_bucket_id",
            "period_start_is_null",
            "period_start_key",
            "period_end_is_null",
            "period_end_key",
        ),
    )
