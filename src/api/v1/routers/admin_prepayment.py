"""Admin prepayment policies API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.prepayment_dto import (
    PrepaymentPolicyCreate,
    PrepaymentPolicyRead,
    PrepaymentPolicyUpdate,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.prepayment_policy import PrepaymentPolicy

router = APIRouter(prefix="/admin/clinics", tags=["admin-prepayment"])


@router.get("/{clinic_id}/prepayment/policies", response_model=list[PrepaymentPolicyRead])
async def list_policies(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PrepaymentPolicy).where(PrepaymentPolicy.clinic_id == clinic_id)
    )
    return [PrepaymentPolicyRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/prepayment/policies",
    response_model=PrepaymentPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    clinic_id: UUID,
    body: PrepaymentPolicyCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    policy = PrepaymentPolicy(
        clinic_id=clinic_id,
        scope_type=body.scope_type,
        scope_doctor_id=body.scope_doctor_id,
        scope_service_id=body.scope_service_id,
        mode=body.mode,
        amount_type=body.amount_type,
        min_amount=body.min_amount,
        deadline_hours_before_visit=body.deadline_hours_before_visit,
        priority=body.priority,
        enabled=body.enabled,
    )
    session.add(policy)
    await session.flush()
    await session.refresh(policy)
    return PrepaymentPolicyRead.model_validate(policy)


@router.get(
    "/{clinic_id}/prepayment/policies/{policy_id}",
    response_model=PrepaymentPolicyRead,
)
async def get_policy(
    clinic_id: UUID,
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PrepaymentPolicy).where(
            PrepaymentPolicy.id == policy_id,
            PrepaymentPolicy.clinic_id == clinic_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PrepaymentPolicyRead.model_validate(policy)


@router.put(
    "/{clinic_id}/prepayment/policies/{policy_id}",
    response_model=PrepaymentPolicyRead,
)
async def update_policy(
    clinic_id: UUID,
    policy_id: UUID,
    body: PrepaymentPolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PrepaymentPolicy).where(
            PrepaymentPolicy.id == policy_id,
            PrepaymentPolicy.clinic_id == clinic_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(policy, k, v)
    await session.flush()
    await session.refresh(policy)
    return PrepaymentPolicyRead.model_validate(policy)


@router.delete(
    "/{clinic_id}/prepayment/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_policy(
    clinic_id: UUID,
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PrepaymentPolicy).where(
            PrepaymentPolicy.id == policy_id,
            PrepaymentPolicy.clinic_id == clinic_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(policy)
    await session.flush()
