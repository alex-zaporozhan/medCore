"""Admin reports API: per-clinic reports and owner dashboard."""

from datetime import date
from uuid import UUID

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.reports_dto import (
    CrmFunnelReport,
    DashboardReport,
    NoShowReport,
    OwnerDashboardReport,
    PatientLtvReport,
    RevenueReport,
)
from src.application.services.report_service import ReportsService
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-reports"])


class RevenueSavedByAiResponse(BaseModel):
    """B5.3: Revenue saved by AI (e.g. overnight). Stub when Revenue Hunter disabled."""
    amount: str | None = None
    period: str = "night"


@router.get("/{clinic_id}/reports/revenue-saved-by-ai", response_model=RevenueSavedByAiResponse)
async def get_revenue_saved_by_ai(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if period not in ("day", "week", "month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period must be day, week, or month",
        )
    service = ReportsService(session)
    try:
        if period == "day":
            return await service.get_dashboard_report(date_param, clinic_id=clinic_id)
        return await service.get_dashboard_report_period(
            date_param, period, clinic_id=clinic_id
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/no-show", response_model=NoShowReport)
async def get_admin_no_show_report(
    clinic_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
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
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    service = ReportsService(session)
    try:
        return await service.get_revenue_report(
            date_from, date_to, clinic_id=clinic_id
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/owner-dashboard", response_model=OwnerDashboardReport)
async def get_owner_dashboard(
    clinic_id: UUID,
    date_param: date = Query(..., alias="date"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    service = ReportsService(session)
    try:
        return await service.get_owner_dashboard(
            clinic_id=clinic_id,
            day=date_param,
            date_from=date_from,
            date_to=date_to,
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{clinic_id}/reports/crm-funnel", response_model=CrmFunnelReport)
async def get_crm_funnel_report(
    clinic_id: UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
