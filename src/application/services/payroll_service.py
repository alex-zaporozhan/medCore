"""ERP payroll service: payroll policies and salary transactions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.interfaces.repositories.payroll_repository import (
    PayrollPolicyRepository,
    SalaryTransactionRepository,
)
from src.infrastructure.database.payroll_repo_impl import (
    PayrollPolicyRepositoryImpl,
    SalaryTransactionRepositoryImpl,
)


@dataclass
class SalaryCalculationContext:
    clinic_id: UUID
    doctor_id: UUID
    role: str | None
    services_amount: Decimal
    products_amount: Decimal
    period_start: date | None
    period_end: date | None
    booking_id: UUID | None


class PayrollService:
    """Application service for ERP payroll operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.policy_repository: PayrollPolicyRepository = PayrollPolicyRepositoryImpl(session)
        self.salary_repository: SalaryTransactionRepository = SalaryTransactionRepositoryImpl(
            session
        )

    # Policies CRUD
    async def create_policy(
        self,
        clinic_id: UUID,
        doctor_id: UUID | None,
        role: str | None,
        fixed_per_shift: Decimal,
        percent_from_services: Decimal,
        percent_from_products: Decimal,
    ) -> PayrollPolicy:
        policy = PayrollPolicy(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            role=role,
            fixed_per_shift=fixed_per_shift,
            percent_from_services=percent_from_services,
            percent_from_products=percent_from_products,
        )
        return await self.policy_repository.create(policy)

    async def update_policy(self, policy: PayrollPolicy) -> PayrollPolicy:
        return await self.policy_repository.update(policy)

    async def get_policy(self, policy_id: UUID) -> PayrollPolicy | None:
        return await self.policy_repository.get_by_id(policy_id)

    async def list_policies(self, clinic_id: UUID) -> list[PayrollPolicy]:
        return list(await self.policy_repository.list_for_clinic(clinic_id))

    async def delete_policy(self, policy_id: UUID) -> None:
        await self.policy_repository.delete(policy_id)

    # Salary calculations
    async def calculate_and_create_salary_transaction(
        self,
        context: SalaryCalculationContext,
    ) -> SalaryTransaction:
        """Calculate salary for a single booking and persist SalaryTransaction."""
        policy = await self.policy_repository.find_applicable_policy(
            clinic_id=context.clinic_id,
            doctor_id=context.doctor_id,
            role=context.role,
        )
        if not policy:
            raise LookupError("No payroll policy configured for doctor/role")

        services_part = (
            context.services_amount * policy.percent_from_services
            if context.services_amount > 0
            else Decimal("0")
        )
        products_part = (
            context.products_amount * policy.percent_from_products
            if context.products_amount > 0
            else Decimal("0")
        )
        amount = services_part + products_part

        tx = SalaryTransaction(
            clinic_id=context.clinic_id,
            doctor_id=context.doctor_id,
            booking_id=context.booking_id,
            amount=amount,
            type="accrual",
            period_start=context.period_start,
            period_end=context.period_end,
            description=None,
        )
        return await self.salary_repository.create(tx)

    async def list_salary_for_doctor(
        self,
        clinic_id: UUID,
        doctor_id: UUID | None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[SalaryTransaction]:
        return list(
            await self.salary_repository.list_for_clinic(
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                period_start=period_start,
                period_end=period_end,
            )
        )

