"""SalaryTransaction entity model for ERP salary accruals and payouts."""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Index, TIMESTAMP, Date, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class SalaryTransaction(Base):
    """Represents salary-related movement for a doctor."""

    __tablename__ = "salary_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # accrual|adjustment|payout
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_salary_tx_clinic_doctor_period",
            "clinic_id",
            "doctor_id",
            "period_start",
            "period_end",
        ),
    )

