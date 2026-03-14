"""Payroll repository interfaces for ERP payroll policies and salary transactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Sequence
from uuid import UUID

from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.salary_transaction import SalaryTransaction


class PayrollPolicyRepository(ABC):
    """Repository interface for PayrollPolicy entity."""

    @abstractmethod
    async def create(self, policy: PayrollPolicy) -> PayrollPolicy:
        ...

    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> PayrollPolicy | None:
        ...

    @abstractmethod
    async def list_for_clinic(self, clinic_id: UUID) -> Sequence[PayrollPolicy]:
        ...

    @abstractmethod
    async def find_applicable_policy(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        role: str | None,
    ) -> PayrollPolicy | None:
        """Return the most specific applicable policy for given doctor/role."""
        ...

    @abstractmethod
    async def update(self, policy: PayrollPolicy) -> PayrollPolicy:
        ...

    @abstractmethod
    async def delete(self, policy_id: UUID) -> None:
        ...


class SalaryTransactionRepository(ABC):
    """Repository interface for SalaryTransaction entity."""

    @abstractmethod
    async def create(self, tx: SalaryTransaction) -> SalaryTransaction:
        ...

    @abstractmethod
    async def get_by_id(self, tx_id: UUID) -> SalaryTransaction | None:
        ...

    @abstractmethod
    async def list_for_doctor(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> Sequence[SalaryTransaction]:
        ...

