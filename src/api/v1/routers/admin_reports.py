"""Admin reports API: per-clinic reports and owner dashboard."""

from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_reporting_session, get_request_context, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.reports_dto import (
    CrmFunnelReport,
    DashboardReport,
    LoyaltyObligationsReport,
    MaterialsByPeriodReport,
    NoShowReport,
    OwnerDashboardReport,
    PatientLtvReport,
    RevenueReport,
    RoiBySourceReport,
    VisitRevenueByPeriodReport,
    PayrollByPeriodReport,
)
from src.application.services.erp_aggregate_service import ErpAggregateService
from src.application.services.erp_report_cache import (
    dashboard_cache_key,
    get_cached_json,
    invalidate_clinic_erp_report_cache,
    owner_dashboard_cache_key,
    set_cached_json,
)
from src.application.services.erp_manual_refresh_audit import record_manual_refresh_audit
from src.application.services.erp_refresh_lock import acquire_erp_refresh_lock
from src.application.services.erp_report_aggregate_read import resolve_erp_aggregate_rows
from src.application.services.erp_reports_repository import ErpReportsRepository
from src.core.config import settings
from src.core.context import RequestContext
from src.core.metrics import Counter  # type: ignore[attr-defined]
from src.application.services.report_service import ReportsService
from src.domain.entities.admin_user import AdminUser

# ERP / attribution reports: avoid unbounded scans over raw transactions (PERF).
MAX_REPORT_PERIOD_DAYS = 366


def _validate_report_period_range(date_from: date, date_to: date) -> None:
    if (date_to - date_from).days > MAX_REPORT_PERIOD_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Report period must not exceed {MAX_REPORT_PERIOD_DAYS} days. "
                "Choose a shorter range or split the request into several smaller periods."
            ),
        )


router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-reports"],
)


# Metrics for ERP/owner reports latency and errors.
erp_reports_requests_total = Counter(  # type: ignore[call-arg]
    "erp_reports_requests_total",
    "Total ERP report requests by type and clinic.",
    ["report_type", "clinic_id", "status"],
)


class RevenueSavedByAiResponse(BaseModel):
    """B5.3: Revenue saved by AI (e.g. overnight). Stub when Revenue Hunter disabled."""
    amount: str | None = None
    period: str = "night"


class RefreshVisitRevenueAggregateBody(BaseModel):
    """Optional window; defaults to rolling lookback from settings."""

    date_from: date | None = None
    date_to: date | None = None


class RefreshVisitRevenueAggregateResponse(BaseModel):
    rows_written: int
    date_from: date
    date_to: date


class RefreshErpAggregatesBody(BaseModel):
    """Manual rebuild of one or all ERP vitrines for a date range."""

    kind: Literal["visit_revenue", "payroll", "materials", "attribution", "all"] = "all"
    date_from: date | None = None
    date_to: date | None = None


class RefreshErpAggregatesResponse(BaseModel):
    rows_written: dict[str, int]
    date_from: date
    date_to: date


@router.get("/{clinic_id}/reports/revenue-saved-by-ai", response_model=RevenueSavedByAiResponse)
async def get_revenue_saved_by_ai(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RevenueSavedByAiResponse:
    """Revenue saved by AI (e.g. overnight). Stub: returns amount=null until Revenue Hunter/Celery is wired."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return RevenueSavedByAiResponse(amount=None, period="night")


@router.get("/{clinic_id}/reports/dashboard", response_model=DashboardReport)
async def get_admin_dashboard_report(
    clinic_id: UUID,
    date_param: date = Query(..., alias="date"),
    period: str = Query("day", description="day, week, or month"),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if period not in ("day", "week", "month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period must be day, week, or month",
        )
    cache_key = dashboard_cache_key(
        clinic_id,
        anchor=date_param.isoformat(),
        period=period,
    )
    if settings.erp_dashboard_cache_enabled:
        raw = await get_cached_json(cache_key)
        if raw:
            return DashboardReport.model_validate_json(raw)
    service = ReportsService(session)
    try:
        if period == "day":
            out = await service.get_dashboard_report(date_param, clinic_id=clinic_id)
        else:
            out = await service.get_dashboard_report_period(
                date_param, period, clinic_id=clinic_id
            )
        if settings.erp_dashboard_cache_enabled:
            await set_cached_json(cache_key, out.model_dump_json())
        return out
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/no-show", response_model=NoShowReport)
async def get_admin_no_show_report(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    service = ReportsService(session)
    try:
        return await service.get_no_show_report(
            date_from, date_to, clinic_id=clinic_id
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/revenue", response_model=RevenueReport)
async def get_admin_revenue_report(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    service = ReportsService(session)
    try:
        return await service.get_revenue_report(
            date_from, date_to, clinic_id=clinic_id
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/{clinic_id}/reports/revenue-by-period",
    response_model=VisitRevenueByPeriodReport,
    dependencies=[Depends(require_permissions("erp.owner_reports.read"))],
)
async def get_erp_revenue_by_period(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> VisitRevenueByPeriodReport:
    """ERP-based revenue report grouped by visit date using financial transactions."""
    if clinic_id != current_admin.clinic_id:
        erp_reports_requests_total.labels(
            report_type="revenue-by-period",
            clinic_id=str(clinic_id),
            status="clinic_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        erp_reports_requests_total.labels(
            report_type="revenue-by-period",
            clinic_id=str(clinic_id),
            status="invalid_period",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    repo = ErpReportsRepository(session)
    agg_svc = ErpAggregateService(session)
    now = datetime.now(timezone.utc)
    stale_limit = max(0, settings.erp_aggregate_stale_max_seconds)

    async def _trust_empty_visit_revenue() -> bool:
        return await agg_svc.watermark_trusts_empty_range(
            clinic_id=clinic_id,
            aggregate_kind="visit_revenue",
            date_from=date_from,
            date_to=date_to,
            stale_limit_seconds=stale_limit,
            now=now,
        )

    items, data_source, aggregate_max_updated_at, aggregate_stale = await resolve_erp_aggregate_rows(
        use_aggregate=settings.erp_read_from_aggregate_for_kind("visit_revenue"),
        fetch_agg=lambda: agg_svc.fetch_visit_revenue_aggregate(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        max_updated_for_range=lambda: agg_svc.max_aggregate_updated_at_for_range(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        fetch_raw=lambda: repo.get_visit_revenue_by_period(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        report_type="revenue-by-period",
        aggregate_kind="visit_revenue",
        stale_limit_seconds=stale_limit,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="erp_revenue_report_fallback_raw_stale",
        empty_log_event="erp_revenue_report_fallback_raw",
        trust_empty_if=_trust_empty_visit_revenue,
    )
    total = sum((v.total_revenue for v in items), start=0)
    erp_reports_requests_total.labels(
        report_type="revenue-by-period",
        clinic_id=str(clinic_id),
        status="success",
    ).inc()
    return VisitRevenueByPeriodReport(
        clinic_id=str(clinic_id),
        date_from=date_from,
        date_to=date_to,
        total_revenue=total,
        items=[
            {
                "date": v.visit_date,
                "booking_id": str(v.booking_id) if v.booking_id is not None else None,
                "amount": v.total_revenue,
            }
            for v in items
        ],
        data_source=data_source,
        aggregate_max_updated_at=aggregate_max_updated_at,
        aggregate_stale=aggregate_stale,
    )


@router.post(
    "/{clinic_id}/reports/erp-aggregates/visit-revenue/refresh",
    response_model=RefreshVisitRevenueAggregateResponse,
    dependencies=[Depends(require_permissions("erp.owner_reports.read"))],
)
async def post_refresh_visit_revenue_aggregate(
    clinic_id: UUID,
    background_tasks: BackgroundTasks,
    body: RefreshVisitRevenueAggregateBody | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RefreshVisitRevenueAggregateResponse:
    """Manual rebuild of visit-revenue vitrine for a date range (ops / catch-up)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    today = date.today()
    lookback = max(1, settings.erp_aggregate_refresh_lookback_days)
    date_from = (body.date_from if body and body.date_from else today - timedelta(days=lookback - 1))
    date_to = body.date_to if body and body.date_to else today
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    svc = ErpAggregateService(session)
    await acquire_erp_refresh_lock(session, clinic_id)
    n = await svc.refresh_visit_revenue_range(
        clinic_id=clinic_id,
        date_from=date_from,
        date_to=date_to,
        job_type="manual",
    )
    await record_manual_refresh_audit(
        session,
        clinic_id=clinic_id,
        admin_user_id=current_admin.id,
        scope_kind="visit_revenue",
        date_from=date_from,
        date_to=date_to,
        rows_written={"visit_revenue": n},
    )
    background_tasks.add_task(invalidate_clinic_erp_report_cache, clinic_id)
    return RefreshVisitRevenueAggregateResponse(rows_written=n, date_from=date_from, date_to=date_to)


@router.post(
    "/{clinic_id}/reports/erp-aggregates/refresh",
    response_model=RefreshErpAggregatesResponse,
)
async def post_refresh_erp_aggregates(
    clinic_id: UUID,
    background_tasks: BackgroundTasks,
    body: RefreshErpAggregatesBody | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
) -> RefreshErpAggregatesResponse:
    """Rebuild one or all ERP vitrines for a date range (ops / catch-up)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if context.user_type != "admin" or "erp.owner_reports.read" not in context.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    today = date.today()
    lookback = max(1, settings.erp_aggregate_refresh_lookback_days)
    b = body or RefreshErpAggregatesBody()
    date_from = b.date_from if b.date_from is not None else today - timedelta(days=lookback - 1)
    date_to = b.date_to if b.date_to is not None else today
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    kinds: list[str]
    if b.kind == "all":
        kinds = ["visit_revenue", "payroll", "materials", "attribution"]
    else:
        kinds = [b.kind]
    if "attribution" in kinds and "attribution.reports.read" not in context.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refreshing attribution/ROI vitrine requires attribution.reports.read permission.",
        )
    svc = ErpAggregateService(session)
    await acquire_erp_refresh_lock(session, clinic_id)
    rows_written: dict[str, int] = {}
    for k in kinds:
        if k == "visit_revenue":
            rows_written[k] = await svc.refresh_visit_revenue_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type="manual",
            )
        elif k == "payroll":
            rows_written[k] = await svc.refresh_payroll_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type="manual",
            )
        elif k == "materials":
            rows_written[k] = await svc.refresh_inventory_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type="manual",
            )
        else:
            rows_written[k] = await svc.refresh_attribution_revenue_range(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type="manual",
            )
    await record_manual_refresh_audit(
        session,
        clinic_id=clinic_id,
        admin_user_id=current_admin.id,
        scope_kind=b.kind,
        date_from=date_from,
        date_to=date_to,
        rows_written=rows_written,
    )
    background_tasks.add_task(invalidate_clinic_erp_report_cache, clinic_id)
    return RefreshErpAggregatesResponse(
        rows_written=rows_written,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{clinic_id}/reports/owner-dashboard", response_model=OwnerDashboardReport)
async def get_owner_dashboard(
    clinic_id: UUID,
    date_param: date = Query(..., alias="date"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    cache_key = owner_dashboard_cache_key(
        clinic_id,
        day=date_param.isoformat(),
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
    )
    if settings.erp_dashboard_cache_enabled:
        raw = await get_cached_json(cache_key)
        if raw:
            return OwnerDashboardReport.model_validate_json(raw)
    service = ReportsService(session)
    try:
        out = await service.get_owner_dashboard(
            clinic_id=clinic_id,
            day=date_param,
            date_from=date_from,
            date_to=date_to,
        )
        if settings.erp_dashboard_cache_enabled:
            await set_cached_json(cache_key, out.model_dump_json())
        return out
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/crm-funnel", response_model=CrmFunnelReport)
async def get_crm_funnel_report(
    clinic_id: UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Сумма по этапам CRM‑воронки (estimated/actual) для владельца клиники."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    if date_from and date_to:
        _validate_report_period_range(date_from, date_to)
    service = ReportsService(session)
    try:
        return await service.get_crm_funnel_report(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/patient-ltv", response_model=PatientLtvReport)
async def get_patient_ltv_report(
    clinic_id: UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    min_ltv: float | None = Query(
        None,
        description="Фильтр: минимальный LTV пациента (по сумме успешных лидов)",
    ),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """LTV пациентов по успешным лидам CRM (для отчётов владельца)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    if date_from and date_to:
        _validate_report_period_range(date_from, date_to)
    from decimal import Decimal

    service = ReportsService(session)
    try:
        return await service.get_patient_ltv_report(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
            min_ltv=Decimal(str(min_ltv)) if min_ltv is not None else None,
            limit=limit,
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/{clinic_id}/reports/payroll-by-period",
    response_model=PayrollByPeriodReport,
    dependencies=[Depends(require_permissions("erp.owner_reports.read"))],
)
async def get_erp_payroll_by_period(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PayrollByPeriodReport:
    """ERP-based payroll movements for a clinic in period."""
    if clinic_id != current_admin.clinic_id:
        erp_reports_requests_total.labels(
            report_type="payroll-by-period",
            clinic_id=str(clinic_id),
            status="clinic_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        erp_reports_requests_total.labels(
            report_type="payroll-by-period",
            clinic_id=str(clinic_id),
            status="invalid_period",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    repo = ErpReportsRepository(session)
    agg_svc = ErpAggregateService(session)
    now = datetime.now(timezone.utc)
    stale_limit = max(0, settings.erp_aggregate_stale_max_seconds)

    async def _trust_empty_payroll() -> bool:
        return await agg_svc.watermark_trusts_empty_range(
            clinic_id=clinic_id,
            aggregate_kind="payroll",
            date_from=date_from,
            date_to=date_to,
            stale_limit_seconds=stale_limit,
            now=now,
        )

    rows, data_source, aggregate_max_updated_at, aggregate_stale = await resolve_erp_aggregate_rows(
        use_aggregate=settings.erp_read_from_aggregate_for_kind("payroll"),
        fetch_agg=lambda: agg_svc.fetch_payroll_aggregate(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        max_updated_for_range=lambda: agg_svc.max_payroll_aggregate_updated_at_for_range(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        fetch_raw=lambda: repo.get_visit_payroll_by_period(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        report_type="payroll-by-period",
        aggregate_kind="payroll",
        stale_limit_seconds=stale_limit,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="erp_payroll_report_fallback_raw_stale",
        empty_log_event="erp_payroll_report_fallback_raw",
        trust_empty_if=_trust_empty_payroll,
    )

    erp_reports_requests_total.labels(
        report_type="payroll-by-period",
        clinic_id=str(clinic_id),
        status="success",
    ).inc()
    return PayrollByPeriodReport(
        clinic_id=str(clinic_id),
        date_from=date_from,
        date_to=date_to,
        items=[
            {
                "doctor_id": str(r.doctor_id),
                "booking_id": str(r.booking_id) if r.booking_id is not None else None,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "amount": r.amount,
            }
            for r in rows
        ],
        data_source=data_source,
        aggregate_max_updated_at=aggregate_max_updated_at,
        aggregate_stale=aggregate_stale,
    )


@router.get(
    "/{clinic_id}/reports/materials-by-period",
    response_model=MaterialsByPeriodReport,
    dependencies=[Depends(require_permissions("erp.owner_reports.read"))],
)
async def get_erp_materials_by_period(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MaterialsByPeriodReport:
    """ERP-based inventory movements (materials) for a clinic in period."""
    if clinic_id != current_admin.clinic_id:
        erp_reports_requests_total.labels(
            report_type="materials-by-period",
            clinic_id=str(clinic_id),
            status="clinic_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        erp_reports_requests_total.labels(
            report_type="materials-by-period",
            clinic_id=str(clinic_id),
            status="invalid_period",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    repo = ErpReportsRepository(session)
    agg_svc = ErpAggregateService(session)
    now = datetime.now(timezone.utc)
    stale_limit = max(0, settings.erp_aggregate_stale_max_seconds)

    async def _trust_empty_materials() -> bool:
        return await agg_svc.watermark_trusts_empty_range(
            clinic_id=clinic_id,
            aggregate_kind="materials",
            date_from=date_from,
            date_to=date_to,
            stale_limit_seconds=stale_limit,
            now=now,
        )

    rows, data_source, aggregate_max_updated_at, aggregate_stale = await resolve_erp_aggregate_rows(
        use_aggregate=settings.erp_read_from_aggregate_for_kind("materials"),
        fetch_agg=lambda: agg_svc.fetch_inventory_aggregate(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        max_updated_for_range=lambda: agg_svc.max_inventory_aggregate_updated_at_for_range(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        fetch_raw=lambda: repo.get_visit_inventory_by_period(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        report_type="materials-by-period",
        aggregate_kind="materials",
        stale_limit_seconds=stale_limit,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="erp_materials_report_fallback_raw_stale",
        empty_log_event="erp_materials_report_fallback_raw",
        trust_empty_if=_trust_empty_materials,
    )

    erp_reports_requests_total.labels(
        report_type="materials-by-period",
        clinic_id=str(clinic_id),
        status="success",
    ).inc()
    return MaterialsByPeriodReport(
        clinic_id=str(clinic_id),
        date_from=date_from,
        date_to=date_to,
        items=[
            {
                "product_id": str(r.product_id),
                "booking_id": str(r.booking_id) if r.booking_id is not None else None,
                "total_quantity": r.total_quantity,
            }
            for r in rows
        ],
        data_source=data_source,
        aggregate_max_updated_at=aggregate_max_updated_at,
        aggregate_stale=aggregate_stale,
    )


@router.get(
    "/{clinic_id}/reports/loyalty-obligations",
    response_model=LoyaltyObligationsReport,
    dependencies=[Depends(require_permissions("erp.owner_reports.read"))],
)
async def get_loyalty_obligations_report(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> LoyaltyObligationsReport:
    """Snapshot of loyalty obligations per patient for clinic."""
    if clinic_id != current_admin.clinic_id:
        erp_reports_requests_total.labels(
            report_type="loyalty-obligations",
            clinic_id=str(clinic_id),
            status="clinic_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    repo = ErpReportsRepository(session)
    rows = await repo.get_loyalty_obligations_snapshot(clinic_id=clinic_id)
    erp_reports_requests_total.labels(
        report_type="loyalty-obligations",
        clinic_id=str(clinic_id),
        status="success",
    ).inc()
    return LoyaltyObligationsReport(
        clinic_id=str(clinic_id),
        as_of=None,
        items=[
            {
                "patient_id": str(r.patient_id) if r.patient_id is not None else None,
                "total_obligations_amount": r.total_obligations_amount,
            }
            for r in rows
        ],
    )


@router.get(
    "/{clinic_id}/reports/roi-by-source",
    response_model=RoiBySourceReport,
    dependencies=[Depends(require_permissions("attribution.reports.read"))],
)
async def get_roi_by_source_report(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_reporting_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RoiBySourceReport:
    """ERP-based revenue by traffic source / campaign for period."""
    if clinic_id != current_admin.clinic_id:
        erp_reports_requests_total.labels(
            report_type="roi-by-source",
            clinic_id=str(clinic_id),
            status="clinic_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        erp_reports_requests_total.labels(
            report_type="roi-by-source",
            clinic_id=str(clinic_id),
            status="invalid_period",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    _validate_report_period_range(date_from, date_to)
    repo = ErpReportsRepository(session)
    agg_svc = ErpAggregateService(session)
    now = datetime.now(timezone.utc)
    stale_limit = max(0, settings.erp_aggregate_stale_max_seconds)

    async def _trust_empty_attribution() -> bool:
        return await agg_svc.watermark_trusts_empty_range(
            clinic_id=clinic_id,
            aggregate_kind="attribution",
            date_from=date_from,
            date_to=date_to,
            stale_limit_seconds=stale_limit,
            now=now,
        )

    rows, data_source, aggregate_max_updated_at, aggregate_stale = await resolve_erp_aggregate_rows(
        use_aggregate=settings.erp_read_from_aggregate_for_kind("attribution"),
        fetch_agg=lambda: agg_svc.fetch_attribution_revenue_aggregate(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        max_updated_for_range=lambda: agg_svc.max_attribution_aggregate_updated_at_for_range(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        fetch_raw=lambda: repo.get_attribution_revenue_by_period(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
        ),
        report_type="roi-by-source",
        aggregate_kind="attribution",
        stale_limit_seconds=stale_limit,
        now=now,
        clinic_id=clinic_id,
        stale_log_event="erp_roi_report_fallback_raw_stale",
        empty_log_event="erp_roi_report_fallback_raw",
        trust_empty_if=_trust_empty_attribution,
    )

    erp_reports_requests_total.labels(
        report_type="roi-by-source",
        clinic_id=str(clinic_id),
        status="success",
    ).inc()
    return RoiBySourceReport(
        clinic_id=str(clinic_id),
        date_from=date_from,
        date_to=date_to,
        items=[
            {
                "date": r.visit_date,
                "traffic_source_id": str(r.traffic_source_id) if r.traffic_source_id is not None else None,
                "campaign_id": str(r.campaign_id) if r.campaign_id is not None else None,
                "revenue": r.total_revenue,
            }
            for r in rows
        ],
        data_source=data_source,
        aggregate_max_updated_at=aggregate_max_updated_at,
        aggregate_stale=aggregate_stale,
    )
