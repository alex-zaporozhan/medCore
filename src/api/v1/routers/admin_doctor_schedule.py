"""Admin API: doctor working hours and absence (график врачей)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.doctor_schedule_dto import (
    AbsenceCreate,
    AbsenceRead,
    WorkingHoursCreate,
    WorkingHoursRead,
    WorkingHoursUpdate,
)
from src.domain.entities.doctor_absence import DoctorAbsence
from src.domain.entities.doctor_working_hours import DoctorWorkingHours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/doctors", tags=["admin-doctor-schedule"])


# ---------- Working hours ----------


@router.get("/{doctor_id}/working-hours", response_model=list[WorkingHoursRead])
async def list_working_hours(
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[WorkingHoursRead]:
    """List working hours for a doctor (all weekdays configured)."""
    result = await session.execute(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor_id
        ).order_by(DoctorWorkingHours.weekday)
    )
    rows = list(result.scalars().all())
    return [WorkingHoursRead.model_validate(r) for r in rows]


@router.post(
    "/{doctor_id}/working-hours",
    response_model=WorkingHoursRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_working_hours(
    doctor_id: UUID,
    data: WorkingHoursCreate,
    session: AsyncSession = Depends(get_session),
) -> WorkingHoursRead:
    """Add or replace working hours for one weekday (upsert by doctor_id + weekday)."""
    existing = await session.execute(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor_id,
            DoctorWorkingHours.weekday == data.weekday,
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        row.start_time = data.start_time
        row.end_time = data.end_time
        await session.flush()
        await session.refresh(row)
        return WorkingHoursRead.model_validate(row)
    entity = DoctorWorkingHours(
        doctor_id=doctor_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    logger.info(
        "Working hours created",
        extra={"doctor_id": str(doctor_id), "weekday": data.weekday},
    )
    return WorkingHoursRead.model_validate(entity)


@router.put("/{doctor_id}/working-hours/{wh_id}", response_model=WorkingHoursRead)
async def update_working_hours(
    doctor_id: UUID,
    wh_id: UUID,
    data: WorkingHoursUpdate,
    session: AsyncSession = Depends(get_session),
) -> WorkingHoursRead:
    """Update working hours row."""
    result = await session.execute(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.id == wh_id,
            DoctorWorkingHours.doctor_id == doctor_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working hours not found")
    if data.start_time is not None:
        row.start_time = data.start_time
    if data.end_time is not None:
        row.end_time = data.end_time
    await session.flush()
    await session.refresh(row)
    return WorkingHoursRead.model_validate(row)


@router.delete("/{doctor_id}/working-hours/{wh_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_working_hours(
    doctor_id: UUID,
    wh_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove working hours for one weekday."""
    result = await session.execute(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.id == wh_id,
            DoctorWorkingHours.doctor_id == doctor_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working hours not found")
    await session.delete(row)
    await session.flush()
    return None


# ---------- Absence (vacation) ----------


@router.get("/{doctor_id}/absence", response_model=list[AbsenceRead])
async def list_absence(
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[AbsenceRead]:
    """List absence periods for a doctor."""
    result = await session.execute(
        select(DoctorAbsence).where(
            DoctorAbsence.doctor_id == doctor_id
        ).order_by(DoctorAbsence.date_from.desc())
    )
    rows = list(result.scalars().all())
    return [AbsenceRead.model_validate(r) for r in rows]


@router.post(
    "/{doctor_id}/absence",
    response_model=AbsenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_absence(
    doctor_id: UUID,
    data: AbsenceCreate,
    session: AsyncSession = Depends(get_session),
) -> AbsenceRead:
    """Add absence period (vacation)."""
    if data.date_to < data.date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )
    entity = DoctorAbsence(
        doctor_id=doctor_id,
        date_from=data.date_from,
        date_to=data.date_to,
        reason=data.reason,
    )
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    logger.info(
        "Doctor absence created",
        extra={"doctor_id": str(doctor_id), "date_from": str(data.date_from), "date_to": str(data.date_to)},
    )
    return AbsenceRead.model_validate(entity)


@router.delete("/{doctor_id}/absence/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_absence(
    doctor_id: UUID,
    absence_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove absence period."""
    result = await session.execute(
        select(DoctorAbsence).where(
            DoctorAbsence.id == absence_id,
            DoctorAbsence.doctor_id == doctor_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found")
    await session.delete(row)
    await session.flush()
    return None
