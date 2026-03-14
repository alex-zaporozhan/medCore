"""Finance repository interfaces for ERP cashboxes and financial transactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction


class CashboxRepository(ABC):
    """Repository interface for Cashbox entity."""

    @abstractmethod
    async def create(self, cashbox: Cashbox) -> Cashbox:
        ...

    @abstractmethod
    async def get_by_id(self, cashbox_id: UUID) -> Cashbox | None:
        ...

    @abstractmethod
    async def get_for_clinic(self, clinic_id: UUID) -> Sequence[Cashbox]:
        ...

    @abstractmethod
    async def get_default_for_clinic(self, clinic_id: UUID) -> Cashbox | None:
        ...

    @abstractmethod
    async def update(self, cashbox: Cashbox) -> Cashbox:
        ...

    @abstractmethod
    async def delete(self, cashbox_id: UUID) -> None:
        ...


class FinancialTransactionRepository(ABC):
    """Repository interface for FinancialTransaction entity."""

    @abstractmethod
    async def create(self, tx: FinancialTransaction) -> FinancialTransaction:
        ...

    @abstractmethod
    async def get_by_id(self, tx_id: UUID) -> FinancialTransaction | None:
        ...

    @abstractmethod
    async def list_for_clinic(
        self,
        clinic_id: UUID,
        cashbox_id: UUID | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[FinancialTransaction]:
        ...

    @abstractmethod
    async def get_balance_for_cashbox(
        self,
        clinic_id: UUID,
        cashbox_id: UUID,
    ) -> Decimal:
        """Return current balance for given cashbox (income - expense)."""
        ...

