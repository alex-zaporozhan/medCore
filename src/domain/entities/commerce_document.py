"""Commerce movement document header (Phase 4, ADR-013)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceDocument(Base):
    """Posted movement: goods_in, goods_out (one location), or goods_transfer (from→to)."""

    __tablename__ = "commerce_documents"
    __table_args__ = (
        CheckConstraint(
            "(doc_kind IN ('goods_in', 'goods_out', 'goods_transfer')) AND ("
            "(doc_kind = 'goods_transfer' AND to_stock_location_id IS NOT NULL "
            "AND to_stock_location_id <> stock_location_id) OR "
            "(doc_kind <> 'goods_transfer' AND to_stock_location_id IS NULL))",
            name="ck_commerce_documents_kind_and_transfer",
        ),
        Index("ix_commerce_documents_clinic_created", "clinic_id", "created_at"),
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
        ForeignKey("commerce_stock_locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_stock_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commerce_stock_locations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    doc_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
