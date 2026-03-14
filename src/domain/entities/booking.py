"""Booking entity model."""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Date,
    Time,
    String,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
    TIMESTAMP,
    func,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Booking(Base):
    """Patient booking model."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id"), nullable=False
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    appointment_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pending|confirmed|cancelled|completed|no_show
    prepayment_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True
    )
    paid_by_subscription: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    erp_processed: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    erp_error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "appointment_date",
            "appointment_time",
            name="ux_bookings_doctor_slot",
        ),
        Index("idx_bookings_patient_date", "patient_id", "appointment_date"),
        Index("idx_bookings_doctor_date", "doctor_id", "appointment_date"),
        Index("idx_bookings_status_date", "status", "appointment_date"),
        Index("idx_bookings_clinic_date", "clinic_id", "appointment_date"),
    )

