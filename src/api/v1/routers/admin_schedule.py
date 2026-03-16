"""Admin aggregated schedule API."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.schedule_dto import AggregatedSchedule, SuggestSlotsResponse
from src.application.services.schedule_service import ScheduleService
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.doctor import Doctor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-schedule"])


@router.get(
    "/{clinic_id}/schedule",
    response_model=AggregatedSchedule,
)
async def get_admin_clinic_schedule(
    clinic_id: UUID,
    date_param: date = Query(..., alias="date"),
    doctor_ids: str = Query(..., description="Comma-separated doctor UUIDs"),
    session: AsyncSession = Depends(get_session),
) -> AggregatedSchedule:
    """Aggregated schedule for multiple doctors in clinic for one day."""
    ids = [UUID(x.strip()) for x in doctor_ids.split(",") if x.strip()]
    service = ScheduleService(session)
    return await service.get_aggregated_schedule(doctor_ids=ids, day=date_param)


@router.get(
    "/{clinic_id}/schedule/suggest-slots",
    response_model=SuggestSlotsResponse,
)
async def get_suggest_slots(
    clinic_id: UUID,
    doctor_id: UUID = Query(..., description="Doctor UUID"),
    date_param: date = Query(..., alias="date"),
    service_id: UUID | None = Query(None, description="Optional service for duration"),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SuggestSlotsResponse:
    """Free slots for a doctor on a date (for booking suggestion)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    result = await session.execute(
        select(Doctor.id).where(
            Doctor.id == doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    service = ScheduleService(session)
    return await service.get_suggest_slots(doctor_id=doctor_id, day=date_param, service_id=service_id)
