"""Admin reports API: dashboard aggregated over all or selected clinics."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.reports_dto import DashboardReport
from src.application.services.report_service import ReportsService
from src.domain.entities.admin_user import AdminUser

router = APIRouter(prefix="/admin", tags=["admin-reports"])


def _parse_clinic_ids(value: str | None) -> list[UUID] | None:
    """Parse comma-separated UUIDs; empty or None returns None (all clinics)."""
    if not value or not value.strip():
        return None
    ids = [x.strip() for x in value.split(",") if x.strip()]
    if not ids:
        return None
    result = []
    for s in ids:
        try:
            result.append(UUID(s))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid clinic_id in list: {s!r}",
            ) from None
    return result


@router.get("/reports/dashboard-aggregate", response_model=DashboardReport)
async def get_dashboard_aggregate(
    date_param: date = Query(..., alias="date"),
    period: str = Query("day", description="day, week, or month"),
    clinic_ids: str | None = Query(
        None,
        alias="clinic_ids",
        description="Comma-separated clinic UUIDs; omit or empty = all clinics",
    ),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> DashboardReport:
    """Dashboard metrics for a date/period, for all clinics or for selected clinic_ids.

    **nps_avg** is optional; without the reviews module it is always null. Frontend should not
    display the NPS widget when nps_avg is null.
    """
    if period not in ("day", "week", "month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period must be day, week, or month",
        )
    ids = _parse_clinic_ids(clinic_ids)
    service = ReportsService(session)
    if period == "day":
        return await service.get_dashboard_report_by_clinic_ids(date_param, clinic_ids=ids)
    return await service.get_dashboard_report_period_by_clinic_ids(
        date_param, period, clinic_ids=ids
    )
