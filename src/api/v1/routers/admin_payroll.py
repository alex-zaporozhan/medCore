"""Admin ERP payroll API: payroll policies and salary transactions."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.erp_payroll_dto import (
    PayrollPolicyCreate,
    PayrollPolicyRead,
    PayrollPolicyUpdate,
    SalaryTransactionRead,
)
from src.application.services.payroll_service import PayrollService
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-payroll"],
    dependencies=[Depends(require_permissions("view_payroll"))],
)


@router.get(
    "/{clinic_id}/payroll/policies",
    response_model=list[PayrollPolicyRead],
)
async def list_payroll_policies(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PayrollPolicyRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = PayrollService(session)
    items = await service.list_policies(clinic_id)
    return [PayrollPolicyRead.model_validate(p) for p in items]


@router.post(
    "/{clinic_id}/payroll/policies",
    response_model=PayrollPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_payroll_policy(
    clinic_id: UUID,
    data: PayrollPolicyCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_payroll")),
) -> PayrollPolicyRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = PayrollService(session)
    policy = await service.create_policy(
        clinic_id=clinic_id,
        doctor_id=data.doctor_id,
        role=data.role,
        fixed_per_shift=data.fixed_per_shift,
        percent_from_services=data.percent_from_services,
        percent_from_products=data.percent_from_products,
    )
    await session.commit()
    return PayrollPolicyRead.model_validate(policy)


@router.patch(
    "/{clinic_id}/payroll/policies/{policy_id}",
    response_model=PayrollPolicyRead,
)
async def update_payroll_policy(
    clinic_id: UUID,
    policy_id: UUID,
    data: PayrollPolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_payroll")),
) -> PayrollPolicyRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = PayrollService(session)
    policy = await service.get_policy(policy_id)
    if not policy or policy.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PayrollPolicy not found")
    if data.doctor_id is not None:
        policy.doctor_id = data.doctor_id
    if data.role is not None:
        policy.role = data.role
    if data.fixed_per_shift is not None:
        policy.fixed_per_shift = data.fixed_per_shift
    if data.percent_from_services is not None:
        policy.percent_from_services = data.percent_from_services
    if data.percent_from_products is not None:
        policy.percent_from_products = data.percent_from_products
    policy = await service.update_policy(policy)
    await session.commit()
    return PayrollPolicyRead.model_validate(policy)


@router.delete(
    "/{clinic_id}/payroll/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_payroll_policy(
    clinic_id: UUID,
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = PayrollService(session)
    policy = await service.get_policy(policy_id)
    if not policy or policy.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PayrollPolicy not found")
    await service.delete_policy(policy_id)
    await session.commit()


@router.get(
    "/{clinic_id}/payroll/transactions",
    response_model=list[SalaryTransactionRead],
)
async def list_salary_transactions(
    clinic_id: UUID,
    doctor_id: UUID | None = Query(
        None,
        description="Filter by doctor; omit to return all salary transactions for the clinic.",
    ),
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[SalaryTransactionRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = PayrollService(session)
    items = await service.list_salary_for_doctor(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        period_start=period_start,
        period_end=period_end,
    )
    return [SalaryTransactionRead.model_validate(tx) for tx in items]


