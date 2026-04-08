"""Commerce stock balance: quantity of a nomenclature item at a stock location (Phase 4, ADR-013)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceStockBalance(Base):
    """One row per (stock_location, nomenclature_item) within a clinic."""

    __tablename__ = "commerce_stock_balances"
    __table_args__ = (
        UniqueConstraint("stock_location_id", "nomenclature_item_id", name="ux_commerce_balance_loc_item"),
        Index("ix_commerce_stock_balances_clinic_location", "clinic_id", "stock_location_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_stock_locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    nomenclature_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_nomenclature_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
