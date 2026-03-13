"""Admin aggregated schedule API."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.schedule_dto import AggregatedSchedule
from src.application.services.schedule_service import ScheduleService

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
