"""InventoryTransaction entity model for ERP inventory movements."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Index, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class InventoryTransaction(Base):
    """Single inventory movement (incoming, outgoing, adjustment)."""

    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # incoming|outgoing|adjustment
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    happened_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )

    __table_args__ = (
        Index(
            "idx_inventory_tx_clinic_happened_at",
            "clinic_id",
            "happened_at",
        ),
        Index(
            "idx_inventory_tx_clinic_product_warehouse",
            "clinic_id",
            "product_id",
            "warehouse_id",
        ),
    )

