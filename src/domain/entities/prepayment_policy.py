"""PrepaymentPolicy entity."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PrepaymentPolicy(Base):
    """Policy for when/how much prepayment is required."""

    __tablename__ = "prepayment_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    scope_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # patient, patient_group, doctor, service, doctor_service
    scope_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id"), nullable=True
    )
    scope_service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id"), nullable=True
    )
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # none, partial, full
    amount_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # percent, fixed
    min_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )
    deadline_hours_before_visit: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
