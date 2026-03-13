"""Schedule API router."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.schedule_dto import DailySchedule
from src.application.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["schedule"])


@router.get(
    "/{doctor_id}/schedule",
    response_model=DailySchedule,
)
async def get_doctor_schedule_public(
    doctor_id: UUID,
    date_param: date = Query(..., alias="date"),
    session: AsyncSession = Depends(get_session),
):
    """Public endpoint: get doctor's schedule for a specific date (patient view)."""
    service = ScheduleService(session)
    try:
        schedule = await service.get_daily_schedule(doctor_id=doctor_id, day=date_param)
    except Exception as exc:
        logger.exception(
            "Failed to get doctor schedule",
            extra={"doctor_id": str(doctor_id), "date": date_param.isoformat()},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get doctor schedule",
        ) from exc

    return schedule


@router.get(
    "/admin/{doctor_id}/schedule",
    response_model=DailySchedule,
)
async def get_doctor_schedule_admin(
    doctor_id: UUID,
    date_param: date = Query(..., alias="date"),
    session: AsyncSession = Depends(get_session),
):
    """Admin endpoint: get doctor's schedule for a specific date (extended view)."""
    service = ScheduleService(session)
    try:
        schedule = await service.get_daily_schedule(doctor_id=doctor_id, day=date_param)
    except Exception as exc:
        logger.exception(
            "Failed to get doctor schedule (admin)",
            extra={"doctor_id": str(doctor_id), "date": date_param.isoformat()},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get doctor schedule",
        ) from exc

    return schedule

