"""SQLAlchemy implementations for ERP payroll repositories."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.interfaces.repositories.payroll_repository import (
    PayrollPolicyRepository,
    SalaryTransactionRepository,
)

logger = logging.getLogger(__name__)


class PayrollPolicyRepositoryImpl(PayrollPolicyRepository):
    """SQLAlchemy implementation of PayrollPolicyRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, policy: PayrollPolicy) -> PayrollPolicy:
        self.session.add(policy)
        await self.session.flush()
        await self.session.refresh(policy)
        logger.info(
            "Payroll policy created",
            extra={"policy_id": str(policy.id), "clinic_id": str(policy.clinic_id)},
        )
        return policy

    async def get_by_id(self, policy_id: UUID) -> PayrollPolicy | None:
        result = await self.session.execute(
            select(PayrollPolicy).where(PayrollPolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def list_for_clinic(self, clinic_id: UUID):
        result = await self.session.execute(
            select(PayrollPolicy).where(PayrollPolicy.clinic_id == clinic_id)
        )
        return list(result.scalars().all())

    async def find_applicable_policy(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        role: str | None,
    ) -> PayrollPolicy | None:
        """Return the most specific applicable policy for given doctor/role."""
        conditions = [
            PayrollPolicy.clinic_id == clinic_id,
            or_(
                PayrollPolicy.doctor_id == doctor_id,
                and_(
                    PayrollPolicy.doctor_id.is_(None),
                    PayrollPolicy.role == role,
                ),
            ),
        ]
        query: Select[tuple[PayrollPolicy]] = (
            select(PayrollPolicy)
            .where(*conditions)
            .order_by(
                PayrollPolicy.doctor_id.is_(None),  # doctor-specific first
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def update(self, policy: PayrollPolicy) -> PayrollPolicy:
        await self.session.flush()
        await self.session.refresh(policy)
        logger.info(
            "Payroll policy updated",
            extra={"policy_id": str(policy.id), "clinic_id": str(policy.clinic_id)},
        )
        return policy

    async def delete(self, policy_id: UUID) -> None:
        policy = await self.get_by_id(policy_id)
        if policy:
            await self.session.delete(policy)
            await self.session.flush()
            logger.info("Payroll policy deleted", extra={"policy_id": str(policy_id)})


class SalaryTransactionRepositoryImpl(SalaryTransactionRepository):
    """SQLAlchemy implementation of SalaryTransactionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tx: SalaryTransaction) -> SalaryTransaction:
        self.session.add(tx)
        await self.session.flush()
        await self.session.refresh(tx)
        logger.info(
            "Salary transaction created",
            extra={
                "tx_id": str(tx.id),
                "clinic_id": str(tx.clinic_id),
                "doctor_id": str(tx.doctor_id),
                "type": tx.type,
            },
        )
        return tx

    async def get_by_id(self, tx_id: UUID) -> SalaryTransaction | None:
        result = await self.session.execute(
            select(SalaryTransaction).where(SalaryTransaction.id == tx_id)
        )
        return result.scalar_one_or_none()

    async def list_for_doctor(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        period_start: date | None = None,
        period_end: date | None = None,
    ):
        query: Select[tuple[SalaryTransaction]] = select(SalaryTransaction).where(
            SalaryTransaction.clinic_id == clinic_id,
            SalaryTransaction.doctor_id == doctor_id,
        )
        if period_start is not None:
            query = query.where(SalaryTransaction.period_start >= period_start)
        if period_end is not None:
            query = query.where(SalaryTransaction.period_end <= period_end)
        result = await self.session.execute(query)
        return list(result.scalars().all())

