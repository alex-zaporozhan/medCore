"""Reporting API endpoints."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.reports_dto import (
    DashboardReport,
    NoShowReport,
    RevenueReport,
)
from src.application.services.report_service import ReportsService
from src.core.user_messages import EMPTY_DB_NO_CLINIC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/dashboard",
    response_model=DashboardReport,
)
async def get_dashboard_report(
    date_param: date = Query(..., alias="date"),
    period: str = Query("day", description="Aggregation: day, week, or month"),
    session: AsyncSession = Depends(get_session),
):
    """Get dashboard metrics for a date or period (day/week/month)."""
    if period not in ("day", "week", "month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period must be day, week, or month",
        )
    service = ReportsService(session)
    try:
        if period == "day":
            report = await service.get_dashboard_report(day=date_param)
        else:
            report = await service.get_dashboard_report_period(
                day=date_param, period=period
            )
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to get dashboard report",
            extra={"date": date_param.isoformat(), "period": period},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build dashboard report",
        ) from exc
    return report


@router.get(
    "/no-show",
    response_model=NoShowReport,
)
async def get_no_show_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Get no-show statistics for a period."""
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be less than or equal to date_to",
        )

    service = ReportsService(session)
    try:
        report = await service.get_no_show_report(
            date_from=date_from,
            date_to=date_to,
        )
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to get no-show report",
            extra={
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build no-show report",
        ) from exc
    return report


@router.get(
    "/revenue",
    response_model=RevenueReport,
)
async def get_revenue_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Get revenue statistics for a period."""
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be less than or equal to date_to",
        )

    service = ReportsService(session)
    try:
        report = await service.get_revenue_report(
            date_from=date_from,
            date_to=date_to,
        )
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to get revenue report",
            extra={
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build revenue report",
        ) from exc
    return report

