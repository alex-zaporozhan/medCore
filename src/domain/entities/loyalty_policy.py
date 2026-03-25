"""LoyaltyPolicy entity model for clinic-level loyalty configuration."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class LoyaltyPolicy(Base):
    """Per-clinic loyalty policy (cashback and points rules)."""

    __tablename__ = "loyalty_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
        unique=True,
    )

    cashback_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.00")
    )
    min_check_for_cashback: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    allow_pay_with_points: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    max_points_share: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    points_expire_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

