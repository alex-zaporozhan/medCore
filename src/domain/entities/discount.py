"""Discount entity — скидки по клинике (первый визит, услуга, врач, период)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Discount(Base):
    """Discount model: first_visit, service, doctor, or period."""

    __tablename__ = "discounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # first_visit | service | doctor | period
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id"), nullable=True
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id"), nullable=True
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    percent_off: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    amount_off: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_discounts_clinic_active", "clinic_id", "is_active"),
        Index("idx_discounts_valid", "valid_from", "valid_until"),
    )
