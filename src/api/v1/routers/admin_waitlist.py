"""Admin waitlist and queue policy API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.waitlist_dto import (
    QueuePolicyRead,
    QueuePolicyUpdate,
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistEntryUpdate,
)
from src.application.services.waitlist_service import (
    WaitlistInvalidTransition,
    WaitlistService,
    WaitlistServiceError,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.queue_policy import QueuePolicy

router = APIRouter(prefix="/admin/clinics", tags=["admin-waitlist"])


def _svc(session: AsyncSession) -> WaitlistService:
    return WaitlistService(session)


@router.get("/{clinic_id}/waitlist", response_model=list[WaitlistEntryRead])
async def list_waitlist(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
    include_inactive: bool = Query(
        default=False,
        description="Include cancelled and expired entries",
    ),
    include_booked: bool = Query(
        default=False,
        description="Include entries already converted to a booking (status booked)",
    ),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    entries = await _svc(session).list_entries(
        clinic_id,
        include_inactive=include_inactive,
        include_booked=include_booked,
    )
    return [WaitlistEntryRead.model_validate(r) for r in entries]


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
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if body.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="clinic_id mismatch")
    try:
        entry = await _svc(session).create_entry(
            clinic_id,
            body,
            actor_admin_id=current_admin.id,
        )
    except WaitlistServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.args[0])) from e
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
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    entry = await _svc(session).get_entry(clinic_id, entry_id)
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
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        entry = await _svc(session).update_entry(
            clinic_id,
            entry_id,
            body,
            actor_admin_id=current_admin.id,
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    except WaitlistInvalidTransition as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except WaitlistServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.args[0])) from e
    return WaitlistEntryRead.model_validate(entry)


@router.delete(
    "/{clinic_id}/waitlist/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_waitlist_entry(
    clinic_id: UUID,
    entry_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
):
    """Soft-cancel: entry remains in DB with status cancelled."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        await _svc(session).cancel_entry(
            clinic_id,
            entry_id,
            actor_admin_id=current_admin.id,
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    except WaitlistInvalidTransition as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except WaitlistServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.args[0])) from e


@router.get("/{clinic_id}/queue-policy", response_model=QueuePolicyRead | None)
async def get_queue_policy(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
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
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
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
