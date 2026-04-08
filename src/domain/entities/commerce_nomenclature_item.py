"""Commerce nomenclature (SKU) per clinic — separate from ERP `products` (Phase 4, ADR-013)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceNomenclatureItem(Base):
    """Sellable / stock-keeping item in the Commerce context."""

    __tablename__ = "commerce_nomenclature_items"
    __table_args__ = (
        UniqueConstraint("clinic_id", "sku", name="ux_commerce_nom_clinic_sku"),
        Index("ix_commerce_nom_org_clinic", "organization_id", "clinic_id"),
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
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pcs")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
