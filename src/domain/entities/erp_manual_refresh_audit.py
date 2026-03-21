"""Audit rows for manual POST /erp-aggregates/refresh (QA_ARCH A13)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ErpAggregateManualRefreshAudit(Base):
    """One row per manual vitrine refresh API call (unified or legacy visit-revenue-only)."""

    __tablename__ = "erp_aggregate_manual_refresh_audit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id"), nullable=False, index=True
    )
    date_from: Mapped[date] = mapped_column(Date(), nullable=False)
    date_to: Mapped[date] = mapped_column(Date(), nullable=False)
    scope_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="visit_revenue|payroll|materials|attribution|all",
    )
    rows_written: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
