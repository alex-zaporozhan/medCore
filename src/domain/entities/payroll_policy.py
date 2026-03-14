"""PayrollPolicy entity model for ERP salary configuration."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Index, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PayrollPolicy(Base):
    """Defines how a doctor or role is paid for work."""

    __tablename__ = "payroll_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id"), nullable=True, index=True
    )
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fixed_per_shift: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0.00"
    )
    percent_from_services: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.0000"
    )
    percent_from_products: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.0000"
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

    __table_args__ = (
        Index("idx_payroll_policies_clinic", "clinic_id"),
        Index(
            "idx_payroll_policies_clinic_doctor_role",
            "clinic_id",
            "doctor_id",
            "role",
        ),
    )

