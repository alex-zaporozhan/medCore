"""Admin reports API: per-clinic reports and owner dashboard."""

from datetime import date
from uuid import UUID

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.reports_dto import (
    DashboardReport,
    NoShowReport,
    OwnerDashboardReport,
    RevenueReport,
)
from src.application.services.report_service import ReportsService
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-reports"])


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
