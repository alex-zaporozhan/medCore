"""Persist + log manual ERP vitrine refresh (A13)."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.erp_manual_refresh_audit import ErpAggregateManualRefreshAudit

logger = logging.getLogger(__name__)


async def record_manual_refresh_audit(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    admin_user_id: UUID,
    scope_kind: str,
    date_from: date,
    date_to: date,
    rows_written: dict[str, int],
) -> None:
    row = ErpAggregateManualRefreshAudit(
        clinic_id=clinic_id,
        admin_user_id=admin_user_id,
        scope_kind=scope_kind,
        date_from=date_from,
        date_to=date_to,
        rows_written=dict(rows_written),
    )
    session.add(row)
    await session.flush()
    logger.info(
        "erp_manual_refresh_audit",
        extra={
            "clinic_id": str(clinic_id),
            "admin_user_id": str(admin_user_id),
            "scope_kind": scope_kind,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "rows_written": rows_written,
        },
    )
