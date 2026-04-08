"""Commerce stock location: point of sale / warehouse within a clinic (Phase 4, ADR-013)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceStockLocation(Base):
    """Logical stock / sales point under organization + clinic (bounded context Commerce)."""

    __tablename__ = "commerce_stock_locations"
    __table_args__ = (
        Index("ix_commerce_stock_locations_org_clinic", "organization_id", "clinic_id"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
