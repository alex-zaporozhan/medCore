"""Per-clinic coverage window for ERP L2 vitrines (QA_ARCH A5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpAggregateCoverageWatermark(Base):
    """Last merged refresh window [covered_from, covered_to] per clinic and vitrine kind."""

    __tablename__ = "erp_aggregate_coverage_watermark"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    aggregate_kind: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # visit_revenue | payroll | materials | attribution
    covered_from: Mapped[date] = mapped_column(Date(), nullable=False)
    covered_to: Mapped[date] = mapped_column(Date(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("clinic_id", "aggregate_kind", name="uq_erp_agg_watermark_clinic_kind"),
    )
