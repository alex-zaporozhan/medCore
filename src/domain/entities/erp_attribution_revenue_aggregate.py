"""Pre-aggregated attribution ROI rows (Engine L2)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpAttributionRevenueAggregate(Base):
    """Same grain as ``get_attribution_revenue_by_period``."""

    __tablename__ = "erp_attribution_revenue_aggregate"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    visit_date: Mapped[date] = mapped_column(Date(), nullable=False)
    traffic_source_bucket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    campaign_bucket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    updated_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "clinic_id",
            "visit_date",
            "traffic_source_bucket_id",
            "campaign_bucket_id",
        ),
    )
