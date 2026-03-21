"""Daily pre-aggregated ERP inventory movements (Engine L2)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpInventoryMovementAggregate(Base):
    """Quantity per calendar day, product, booking bucket (sum over days = period report)."""

    __tablename__ = "erp_inventory_movement_aggregate"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    movement_date: Mapped[date] = mapped_column(Date(), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_bucket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity_day: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    updated_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("clinic_id", "movement_date", "product_id", "booking_bucket_id"),
    )
