"""Schedule API router."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.schedule_dto import DailySchedule
from src.application.multitenancy import EntityClinicMismatchError
from src.application.services.multitenancy_alert_service import record_admin_clinic_boundary_event
from src.application.services.schedule_service import ScheduleService
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["schedule"])


@router.get(
    "/{doctor_id}/schedule",
    response_model=DailySchedule,
)
async def get_doctor_schedule_public(
    doctor_id: UUID,
    clinic_id: UUID = Query(
        ...,
        description="Clinic context: schedule is returned only if the doctor belongs to this clinic.",
    ),
    date_param: date = Query(..., alias="date"),
    session: AsyncSession = Depends(get_session),
):
    """Public endpoint: get doctor's schedule for a specific date (patient view)."""
    service = ScheduleService(session)
    try:
        schedule = await service.get_daily_schedule(
            doctor_id=doctor_id, day=date_param, clinic_id=clinic_id
        )
    except EntityClinicMismatchError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расписание не найдено для этой клиники.",
        ) from None
    except Exception as exc:
        logger.exception(
            "Failed to get doctor schedule",
            extra={
                "doctor_id": str(doctor_id),
                "clinic_id": str(clinic_id),
                "date": date_param.isoformat(),
            },
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
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin endpoint: get doctor's schedule for a specific date (extended view)."""
    service = ScheduleService(session)
    try:
        schedule = await service.get_daily_schedule(
            doctor_id=doctor_id,
            day=date_param,
            clinic_id=current_admin.clinic_id,
        )
    except EntityClinicMismatchError:
        await record_admin_clinic_boundary_event(
            session,
            current_admin,
            reason="schedule_guard: врач не принадлежит клинике администратора",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "clinic_forbidden",
                "message": "Врач не относится к вашей клинике.",
            },
        ) from None
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
