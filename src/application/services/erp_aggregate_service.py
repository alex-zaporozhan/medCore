"""Fill and read ERP reporting pre-aggregates (Engine L2)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.erp_report_cache import invalidate_clinic_erp_report_cache
from src.application.services.erp_refresh_lock import acquire_erp_refresh_lock
from src.application.services.erp_reports_repository import (
    ErpAttributionRevenueView,
    ErpReportsRepository,
    ErpVisitInventoryView,
    ErpVisitPayrollView,
    ErpVisitRevenueView,
)
from src.core.config import settings
from src.core.metrics import (
    erp_aggregate_nightly_kind_failures_total,
    erp_aggregate_refresh_seconds,
    erp_aggregate_rows_processed,
)
from src.domain.entities.erp_aggregate_coverage_watermark import ErpAggregateCoverageWatermark
from src.domain.entities.erp_attribution_revenue_aggregate import ErpAttributionRevenueAggregate
from src.domain.entities.erp_inventory_movement_aggregate import ErpInventoryMovementAggregate
from src.domain.entities.erp_payroll_aggregate import ErpPayrollAggregate
from src.domain.entities.erp_report_buckets import (
    NULL_BOOKING_BUCKET,
    NULL_CAMPAIGN_BUCKET,
    NULL_TRAFFIC_SOURCE_BUCKET,
    payroll_period_from_storage,
    payroll_period_keys_for_storage,
)
from src.domain.entities.erp_visit_revenue_aggregate import ErpVisitRevenueAggregate

logger = logging.getLogger(__name__)


def _booking_bucket(booking_id: UUID | None) -> UUID:
    return booking_id if booking_id is not None else NULL_BOOKING_BUCKET


def _traffic_bucket(traffic_source_id: UUID | None) -> UUID:
    return traffic_source_id if traffic_source_id is not None else NULL_TRAFFIC_SOURCE_BUCKET


def _campaign_bucket(campaign_id: UUID | None) -> UUID:
    return campaign_id if campaign_id is not None else NULL_CAMPAIGN_BUCKET


class ErpAggregateService:
    """Idempotent refresh of ERP vitrines from canonical ErpReportsRepository queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._erp = ErpReportsRepository(session)

    async def _merge_coverage_watermark(
        self,
        clinic_id: UUID,
        aggregate_kind: str,
        date_from: date,
        date_to: date,
    ) -> None:
        """Extend known refresh window for this vitrine kind (A5)."""
        now = datetime.now(timezone.utc)
        stmt = select(ErpAggregateCoverageWatermark).where(
            ErpAggregateCoverageWatermark.clinic_id == clinic_id,
            ErpAggregateCoverageWatermark.aggregate_kind == aggregate_kind,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            self._session.add(
                ErpAggregateCoverageWatermark(
                    clinic_id=clinic_id,
                    aggregate_kind=aggregate_kind,
                    covered_from=date_from,
                    covered_to=date_to,
                    updated_at=now,
                )
            )
        else:
            row.covered_from = min(row.covered_from, date_from)
            row.covered_to = max(row.covered_to, date_to)
            row.updated_at = now

    async def watermark_trusts_empty_range(
        self,
        *,
        clinic_id: UUID,
        aggregate_kind: str,
        date_from: date,
        date_to: date,
        stale_limit_seconds: int,
        now: datetime,
    ) -> bool:
        """True if requested period was refreshed and watermark is fresh enough to trust zero rows."""
        stmt = select(ErpAggregateCoverageWatermark).where(
            ErpAggregateCoverageWatermark.clinic_id == clinic_id,
            ErpAggregateCoverageWatermark.aggregate_kind == aggregate_kind,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        if date_from < row.covered_from or date_to > row.covered_to:
            return False
        u = self._normalize_ts(row.updated_at)
        if u is None:
            return False
        if (now - u).total_seconds() > stale_limit_seconds:
            return False
        return True

    async def refresh_clinic_erp_aggregates_window(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        job_type: str = "window",
    ) -> dict[str, int]:
        """Serialize by clinic (advisory lock) and refresh all four vitrine kinds in one transaction."""
        await acquire_erp_refresh_lock(self._session, clinic_id)
        return {
            "visit_revenue": await self.refresh_visit_revenue_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type=job_type,
            ),
            "payroll": await self.refresh_payroll_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type=job_type,
            ),
            "materials": await self.refresh_inventory_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type=job_type,
            ),
            "attribution": await self.refresh_attribution_revenue_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type=job_type,
            ),
        }

    async def refresh_visit_revenue_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        job_type: str = "manual",
    ) -> int:
        """Replace aggregate rows for [date_from, date_to] from raw ERP query. Returns rows inserted."""
        t0 = time.perf_counter()
        rows = await self._erp.get_visit_revenue_by_period(
            clinic_id=clinic_id, date_from=date_from, date_to=date_to
        )
        await self._session.execute(
            delete(ErpVisitRevenueAggregate).where(
                ErpVisitRevenueAggregate.clinic_id == clinic_id,
                ErpVisitRevenueAggregate.visit_date >= date_from,
                ErpVisitRevenueAggregate.visit_date <= date_to,
            )
        )
        for v in rows:
            bucket = _booking_bucket(v.booking_id)
            self._session.add(
                ErpVisitRevenueAggregate(
                    clinic_id=v.clinic_id,
                    visit_date=v.visit_date,
                    booking_bucket_id=bucket,
                    total_revenue=v.total_revenue,
                )
            )
        await self._session.flush()
        await self._merge_coverage_watermark(clinic_id, "visit_revenue", date_from, date_to)
        erp_aggregate_refresh_seconds.labels(job_type=job_type).observe(time.perf_counter() - t0)
        erp_aggregate_rows_processed.labels(job_type=job_type).inc(max(0, len(rows)))
        return len(rows)

    async def fetch_visit_revenue_aggregate(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitRevenueView]:
        """Read vitrine rows (same DTO as raw repository)."""
        stmt = (
            select(ErpVisitRevenueAggregate)
            .where(
                ErpVisitRevenueAggregate.clinic_id == clinic_id,
                ErpVisitRevenueAggregate.visit_date >= date_from,
                ErpVisitRevenueAggregate.visit_date <= date_to,
            )
            .order_by(
                ErpVisitRevenueAggregate.visit_date.asc(),
                ErpVisitRevenueAggregate.booking_bucket_id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        out: list[ErpVisitRevenueView] = []
        for r in result.scalars().all():
            bid = None if r.booking_bucket_id == NULL_BOOKING_BUCKET else r.booking_bucket_id
            out.append(
                ErpVisitRevenueView(
                    clinic_id=r.clinic_id,
                    visit_date=r.visit_date,
                    booking_id=bid,
                    total_revenue=r.total_revenue,
                )
            )
        return out

    async def max_aggregate_updated_at(self, *, clinic_id: UUID) -> datetime | None:
        stmt = select(func.max(ErpVisitRevenueAggregate.updated_at)).where(
            ErpVisitRevenueAggregate.clinic_id == clinic_id
        )
        raw = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._normalize_ts(raw)

    async def max_aggregate_updated_at_for_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> datetime | None:
        """Latest vitrine write time for rows whose visit_date falls in [date_from, date_to]."""
        stmt = select(func.max(ErpVisitRevenueAggregate.updated_at)).where(
            ErpVisitRevenueAggregate.clinic_id == clinic_id,
            ErpVisitRevenueAggregate.visit_date >= date_from,
            ErpVisitRevenueAggregate.visit_date <= date_to,
        )
        raw = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._normalize_ts(raw)

    # --- Payroll ---

    async def refresh_payroll_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        job_type: str = "manual",
    ) -> int:
        t0 = time.perf_counter()
        rows = await self._erp.get_visit_payroll_by_period(
            clinic_id=clinic_id, date_from=date_from, date_to=date_to
        )
        await self._session.execute(
            delete(ErpPayrollAggregate).where(
                ErpPayrollAggregate.clinic_id == clinic_id,
                ErpPayrollAggregate.period_start_key <= date_to,
                ErpPayrollAggregate.period_end_key >= date_from,
            )
        )
        for v in rows:
            ps, pe = payroll_period_keys_for_storage(v.period_start, v.period_end)
            ps_null = v.period_start is None
            pe_null = v.period_end is None
            self._session.add(
                ErpPayrollAggregate(
                    clinic_id=v.clinic_id,
                    doctor_id=v.doctor_id,
                    booking_bucket_id=_booking_bucket(v.booking_id),
                    period_start_is_null=ps_null,
                    period_start_key=ps,
                    period_end_is_null=pe_null,
                    period_end_key=pe,
                    amount=v.amount,
                )
            )
        await self._session.flush()
        await self._merge_coverage_watermark(clinic_id, "payroll", date_from, date_to)
        erp_aggregate_refresh_seconds.labels(job_type=job_type).observe(time.perf_counter() - t0)
        erp_aggregate_rows_processed.labels(job_type=job_type).inc(max(0, len(rows)))
        return len(rows)

    async def fetch_payroll_aggregate(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitPayrollView]:
        stmt = (
            select(ErpPayrollAggregate)
            .where(
                ErpPayrollAggregate.clinic_id == clinic_id,
                ErpPayrollAggregate.period_start_key <= date_to,
                ErpPayrollAggregate.period_end_key >= date_from,
            )
            .order_by(
                ErpPayrollAggregate.doctor_id.asc(),
                ErpPayrollAggregate.period_start_is_null.asc(),
                ErpPayrollAggregate.period_start_key.asc(),
                ErpPayrollAggregate.period_end_is_null.asc(),
                ErpPayrollAggregate.period_end_key.asc(),
                ErpPayrollAggregate.booking_bucket_id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        out: list[ErpVisitPayrollView] = []
        for r in result.scalars().all():
            p_start, p_end = payroll_period_from_storage(
                r.period_start_key,
                r.period_end_key,
                period_start_is_null=r.period_start_is_null,
                period_end_is_null=r.period_end_is_null,
            )
            bid = None if r.booking_bucket_id == NULL_BOOKING_BUCKET else r.booking_bucket_id
            out.append(
                ErpVisitPayrollView(
                    clinic_id=r.clinic_id,
                    doctor_id=r.doctor_id,
                    booking_id=bid,
                    period_start=p_start,
                    period_end=p_end,
                    amount=r.amount,
                )
            )
        return out

    async def max_payroll_aggregate_updated_at_for_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> datetime | None:
        stmt = select(func.max(ErpPayrollAggregate.updated_at)).where(
            ErpPayrollAggregate.clinic_id == clinic_id,
            ErpPayrollAggregate.period_start_key <= date_to,
            ErpPayrollAggregate.period_end_key >= date_from,
        )
        raw = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._normalize_ts(raw)

    # --- Materials (daily vitrine) ---

    async def refresh_inventory_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        job_type: str = "manual",
    ) -> int:
        t0 = time.perf_counter()
        rows = await self._erp.get_visit_inventory_daily_by_period(
            clinic_id=clinic_id, date_from=date_from, date_to=date_to
        )
        await self._session.execute(
            delete(ErpInventoryMovementAggregate).where(
                ErpInventoryMovementAggregate.clinic_id == clinic_id,
                ErpInventoryMovementAggregate.movement_date >= date_from,
                ErpInventoryMovementAggregate.movement_date <= date_to,
            )
        )
        for v in rows:
            self._session.add(
                ErpInventoryMovementAggregate(
                    clinic_id=v.clinic_id,
                    movement_date=v.movement_date,
                    product_id=v.product_id,
                    booking_bucket_id=_booking_bucket(v.booking_id),
                    quantity_day=v.quantity_day,
                )
            )
        await self._session.flush()
        await self._merge_coverage_watermark(clinic_id, "materials", date_from, date_to)
        erp_aggregate_refresh_seconds.labels(job_type=job_type).observe(time.perf_counter() - t0)
        erp_aggregate_rows_processed.labels(job_type=job_type).inc(max(0, len(rows)))
        return len(rows)

    async def fetch_inventory_aggregate(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitInventoryView]:
        stmt = (
            select(ErpInventoryMovementAggregate)
            .where(
                ErpInventoryMovementAggregate.clinic_id == clinic_id,
                ErpInventoryMovementAggregate.movement_date >= date_from,
                ErpInventoryMovementAggregate.movement_date <= date_to,
            )
            .order_by(
                ErpInventoryMovementAggregate.product_id.asc(),
                ErpInventoryMovementAggregate.booking_bucket_id.asc(),
                ErpInventoryMovementAggregate.movement_date.asc(),
            )
        )
        result = await self._session.execute(stmt)
        totals: dict[tuple[UUID, UUID], Decimal] = defaultdict(lambda: Decimal("0"))
        for r in result.scalars().all():
            key = (r.product_id, r.booking_bucket_id)
            totals[key] += r.quantity_day
        out: list[ErpVisitInventoryView] = []
        for (product_id, bbid) in sorted(totals.keys(), key=lambda k: (k[0], k[1])):
            bid = None if bbid == NULL_BOOKING_BUCKET else bbid
            out.append(
                ErpVisitInventoryView(
                    clinic_id=clinic_id,
                    product_id=product_id,
                    booking_id=bid,
                    total_quantity=totals[(product_id, bbid)],
                )
            )
        out.sort(key=lambda row: (row.product_id, row.booking_id or NULL_BOOKING_BUCKET))
        return out

    async def max_inventory_aggregate_updated_at_for_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> datetime | None:
        stmt = select(func.max(ErpInventoryMovementAggregate.updated_at)).where(
            ErpInventoryMovementAggregate.clinic_id == clinic_id,
            ErpInventoryMovementAggregate.movement_date >= date_from,
            ErpInventoryMovementAggregate.movement_date <= date_to,
        )
        raw = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._normalize_ts(raw)

    # --- Attribution / ROI ---

    async def refresh_attribution_revenue_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        job_type: str = "manual",
    ) -> int:
        t0 = time.perf_counter()
        rows = await self._erp.get_attribution_revenue_by_period(
            clinic_id=clinic_id, date_from=date_from, date_to=date_to
        )
        await self._session.execute(
            delete(ErpAttributionRevenueAggregate).where(
                ErpAttributionRevenueAggregate.clinic_id == clinic_id,
                ErpAttributionRevenueAggregate.visit_date >= date_from,
                ErpAttributionRevenueAggregate.visit_date <= date_to,
            )
        )
        for v in rows:
            self._session.add(
                ErpAttributionRevenueAggregate(
                    clinic_id=v.clinic_id,
                    visit_date=v.visit_date,
                    traffic_source_bucket_id=_traffic_bucket(v.traffic_source_id),
                    campaign_bucket_id=_campaign_bucket(v.campaign_id),
                    total_revenue=v.total_revenue,
                )
            )
        await self._session.flush()
        await self._merge_coverage_watermark(clinic_id, "attribution", date_from, date_to)
        erp_aggregate_refresh_seconds.labels(job_type=job_type).observe(time.perf_counter() - t0)
        erp_aggregate_rows_processed.labels(job_type=job_type).inc(max(0, len(rows)))
        return len(rows)

    async def fetch_attribution_revenue_aggregate(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpAttributionRevenueView]:
        stmt = (
            select(ErpAttributionRevenueAggregate)
            .where(
                ErpAttributionRevenueAggregate.clinic_id == clinic_id,
                ErpAttributionRevenueAggregate.visit_date >= date_from,
                ErpAttributionRevenueAggregate.visit_date <= date_to,
            )
            .order_by(
                ErpAttributionRevenueAggregate.visit_date.asc(),
                ErpAttributionRevenueAggregate.traffic_source_bucket_id.asc(),
                ErpAttributionRevenueAggregate.campaign_bucket_id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        out: list[ErpAttributionRevenueView] = []
        for r in result.scalars().all():
            ts = None if r.traffic_source_bucket_id == NULL_TRAFFIC_SOURCE_BUCKET else r.traffic_source_bucket_id
            cid = None if r.campaign_bucket_id == NULL_CAMPAIGN_BUCKET else r.campaign_bucket_id
            out.append(
                ErpAttributionRevenueView(
                    clinic_id=r.clinic_id,
                    visit_date=r.visit_date,
                    traffic_source_id=ts,
                    campaign_id=cid,
                    total_revenue=r.total_revenue,
                )
            )
        return out

    async def max_attribution_aggregate_updated_at_for_range(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> datetime | None:
        stmt = select(func.max(ErpAttributionRevenueAggregate.updated_at)).where(
            ErpAttributionRevenueAggregate.clinic_id == clinic_id,
            ErpAttributionRevenueAggregate.visit_date >= date_from,
            ErpAttributionRevenueAggregate.visit_date <= date_to,
        )
        raw = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._normalize_ts(raw)

    @staticmethod
    def _normalize_ts(raw: object) -> datetime | None:
        if raw is None:
            return None
        if isinstance(raw, datetime) and raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw  # type: ignore[return-value]


async def refresh_all_clinics_visit_revenue_nightly(
    *,
    lookback_days: int | None = None,
) -> None:
    """Backward-compatible alias: refreshes all ERP vitrines for every clinic."""
    await refresh_all_clinics_erp_aggregates_nightly(lookback_days=lookback_days)


async def refresh_all_clinics_erp_aggregates_nightly(
    *,
    lookback_days: int | None = None,
) -> None:
    """Refresh sliding window for every clinic (Celery): visit revenue, payroll, materials, ROI."""
    from src.domain.entities.clinic import Clinic
    from src.infrastructure.database.base import AsyncSessionLocal

    factory = AsyncSessionLocal
    days = lookback_days if lookback_days is not None else settings.erp_aggregate_refresh_lookback_days
    today = datetime.now(timezone.utc).date()
    date_from = date.fromordinal(today.toordinal() - max(0, days - 1))
    date_to = today
    async with factory() as list_session:
        res = await list_session.execute(select(Clinic.id))
        clinic_ids = [row[0] for row in res.all()]

    for cid in clinic_ids:
        try:
            async with factory() as session:
                async with session.begin():
                    svc = ErpAggregateService(session)
                    rows_by_kind = await svc.refresh_clinic_erp_aggregates_window(
                        clinic_id=cid,
                        date_from=date_from,
                        date_to=date_to,
                        job_type="nightly_clinic",
                    )
            logger.info(
                "erp_aggregate_refresh_clinic_done",
                extra={
                    "clinic_id": str(cid),
                    "rows_by_kind": rows_by_kind,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                },
            )
            await invalidate_clinic_erp_report_cache(cid)
        except Exception:
            for kind in ("visit_revenue", "payroll", "materials", "attribution"):
                erp_aggregate_nightly_kind_failures_total.labels(aggregate_kind=kind).inc()
            logger.exception(
                "erp_aggregate_refresh_clinic_failed",
                extra={"clinic_id": str(cid)},
            )
