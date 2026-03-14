"""ERP finance service: cashboxes CRUD and financial transactions creation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.interfaces.repositories.finance_repository import (
    CashboxRepository,
    FinancialTransactionRepository,
)
from src.infrastructure.database.finance_repo_impl import (
    CashboxRepositoryImpl,
    FinancialTransactionRepositoryImpl,
)


@dataclass
class CreateFinancialTransactionInput:
  clinic_id: UUID
  cashbox_id: UUID
  type: str  # income|expense|transfer
  amount: Decimal
  currency: str
  happened_at: datetime
  description: str | None
  booking_id: UUID | None
  payment_id: UUID | None
  source: str
  lead_id: UUID | None = None
  visit_attribution_id: UUID | None = None


class FinanceService:
    """Application service for ERP finance operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cashbox_repository: CashboxRepository = CashboxRepositoryImpl(session)
        self.tx_repository: FinancialTransactionRepository = FinancialTransactionRepositoryImpl(
            session
        )

    # Cashboxes
    async def create_cashbox(
        self,
        clinic_id: UUID,
        name: str,
        type: str,
        currency: str = "RUB",
        is_default: bool = False,
        is_active: bool = True,
    ) -> Cashbox:
        cashbox = Cashbox(
            clinic_id=clinic_id,
            name=name,
            type=type,
            currency=currency,
            is_default=is_default,
            is_active=is_active,
        )
        return await self.cashbox_repository.create(cashbox)

    async def update_cashbox(self, cashbox: Cashbox) -> Cashbox:
        return await self.cashbox_repository.update(cashbox)

    async def get_cashbox(self, cashbox_id: UUID) -> Cashbox | None:
        return await self.cashbox_repository.get_by_id(cashbox_id)

    async def list_cashboxes(self, clinic_id: UUID) -> list[Cashbox]:
        return list(await self.cashbox_repository.get_for_clinic(clinic_id))

    async def delete_cashbox(self, cashbox_id: UUID) -> None:
        await self.cashbox_repository.delete(cashbox_id)

    async def get_default_cashbox(self, clinic_id: UUID) -> Cashbox | None:
        return await self.cashbox_repository.get_default_for_clinic(clinic_id)

    # Financial transactions
    async def create_transaction(
        self,
        data: CreateFinancialTransactionInput,
    ) -> FinancialTransaction:
        tx = FinancialTransaction(
            clinic_id=data.clinic_id,
            cashbox_id=data.cashbox_id,
            type=data.type,
            amount=data.amount,
            currency=data.currency,
            happened_at=data.happened_at,
            description=data.description,
            booking_id=data.booking_id,
            payment_id=data.payment_id,
            lead_id=data.lead_id,
            visit_attribution_id=data.visit_attribution_id,
            source=data.source,
        )
        return await self.tx_repository.create(tx)

    async def list_transactions(
        self,
        clinic_id: UUID,
        cashbox_id: UUID | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FinancialTransaction]:
        return list(
            await self.tx_repository.list_for_clinic(
                clinic_id=clinic_id,
                cashbox_id=cashbox_id,
                type_filter=type_filter,
                date_from=date_from,
                date_to=date_to,
                skip=skip,
                limit=limit,
            )
        )

    async def get_cashbox_balance(
        self,
        clinic_id: UUID,
        cashbox_id: UUID,
    ) -> Decimal:
        return await self.tx_repository.get_balance_for_cashbox(
            clinic_id=clinic_id,
            cashbox_id=cashbox_id,
        )

