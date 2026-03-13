"""Clinic payment gateway credentials per clinic and provider."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ClinicPaymentGateway(Base):
    """One row per clinic per payment gateway (excluding YooKassa credentials on Clinic)."""

    __tablename__ = "clinic_payment_gateways"
    __table_args__ = (
        UniqueConstraint("clinic_id", "gateway", name="uq_clinic_payment_gateway"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    gateway: Mapped[str] = mapped_column(String(32), nullable=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="PENDING",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

