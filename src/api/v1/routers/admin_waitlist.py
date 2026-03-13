"""Admin waitlist and queue policy API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.waitlist_dto import (
    QueuePolicyRead,
    QueuePolicyUpdate,
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistEntryUpdate,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.queue_policy import QueuePolicy
from src.domain.entities.waitlist_entry import WaitlistEntry

router = APIRouter(prefix="/admin/clinics", tags=["admin-waitlist"])


@router.get("/{clinic_id}/waitlist", response_model=list[WaitlistEntryRead])
async def list_waitlist(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(WaitlistEntry).where(WaitlistEntry.clinic_id == clinic_id)
    )
    return [WaitlistEntryRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/waitlist",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_waitlist_entry(
    clinic_id: UUID,
    body: WaitlistEntryCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    entry = WaitlistEntry(
        clinic_id=clinic_id,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        speciality=body.speciality,
        time_preferences_json=body.time_preferences_json,
        preferred_date=body.preferred_date,
        preferred_time=body.preferred_time,
        priority=body.priority,
        status=body.status,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return WaitlistEntryRead.model_validate(entry)


@router.get(
    "/{clinic_id}/waitlist/{entry_id}",
    response_model=WaitlistEntryRead,
)
async def get_waitlist_entry(
    clinic_id: UUID,
    entry_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.clinic_id == clinic_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return WaitlistEntryRead.model_validate(entry)


@router.put(
    "/{clinic_id}/waitlist/{entry_id}",
    response_model=WaitlistEntryRead,
)
async def update_waitlist_entry(
    clinic_id: UUID,
    entry_id: UUID,
    body: WaitlistEntryUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.clinic_id == clinic_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(entry, k, v)
    await session.flush()
    await session.refresh(entry)
    return WaitlistEntryRead.model_validate(entry)


@router.delete(
    "/{clinic_id}/waitlist/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_waitlist_entry(
    clinic_id: UUID,
    entry_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.clinic_id == clinic_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(entry)
    await session.flush()


@router.get("/{clinic_id}/queue-policy", response_model=QueuePolicyRead | None)
async def get_queue_policy(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(QueuePolicy).where(QueuePolicy.clinic_id == clinic_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return None
    return QueuePolicyRead.model_validate(policy)


@router.put(
    "/{clinic_id}/queue-policy",
    response_model=QueuePolicyRead,
)
async def upsert_queue_policy(
    clinic_id: UUID,
    body: QueuePolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(QueuePolicy).where(QueuePolicy.clinic_id == clinic_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        policy = QueuePolicy(
            clinic_id=clinic_id,
            mode=body.mode or "sequential",
            broadcast_size=body.broadcast_size or 5,
            response_timeout_minutes=body.response_timeout_minutes or 60,
            max_notifications_per_entry=body.max_notifications_per_entry,
        )
        session.add(policy)
    else:
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(policy, k, v)
    await session.flush()
    await session.refresh(policy)
    return QueuePolicyRead.model_validate(policy)
