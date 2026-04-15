"""SQLAlchemy implementations for ERP finance repositories."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.interfaces.repositories.finance_repository import (
    CashboxRepository,
    FinancialTransactionRepository,
)

logger = logging.getLogger(__name__)


class CashboxRepositoryImpl(CashboxRepository):
    """SQLAlchemy implementation of CashboxRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, cashbox: Cashbox) -> Cashbox:
        self.session.add(cashbox)
        await self.session.flush()
        await self.session.refresh(cashbox)
        logger.info(
            "Cashbox created",
            extra={"cashbox_id": str(cashbox.id), "clinic_id": str(cashbox.clinic_id)},
        )
        return cashbox

    async def get_by_id(self, cashbox_id: UUID) -> Cashbox | None:
        result = await self.session.execute(
            select(Cashbox).where(Cashbox.id == cashbox_id)
        )
        return result.scalar_one_or_none()

    async def get_for_clinic(self, clinic_id: UUID):
        result = await self.session.execute(
            select(Cashbox).where(Cashbox.clinic_id == clinic_id)
        )
        return list(result.scalars().all())

    async def get_default_for_clinic(self, clinic_id: UUID) -> Cashbox | None:
        result = await self.session.execute(
            select(Cashbox)
            .where(
                Cashbox.clinic_id == clinic_id,
                Cashbox.is_default.is_(True),
            )
            .order_by(Cashbox.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, cashbox: Cashbox) -> Cashbox:
        await self.session.flush()
        await self.session.refresh(cashbox)
        logger.info(
            "Cashbox updated",
            extra={"cashbox_id": str(cashbox.id), "clinic_id": str(cashbox.clinic_id)},
        )
        return cashbox

    async def delete(self, cashbox_id: UUID) -> None:
        cashbox = await self.get_by_id(cashbox_id)
        if cashbox:
            await self.session.delete(cashbox)
            await self.session.flush()
            logger.info("Cashbox deleted", extra={"cashbox_id": str(cashbox_id)})


class FinancialTransactionRepositoryImpl(FinancialTransactionRepository):
    """SQLAlchemy implementation of FinancialTransactionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tx: FinancialTransaction) -> FinancialTransaction:
        self.session.add(tx)
        await self.session.flush()
        await self.session.refresh(tx)
        logger.info(
            "Financial transaction created",
            extra={
                "tx_id": str(tx.id),
                "clinic_id": str(tx.clinic_id),
                "cashbox_id": str(tx.cashbox_id),
                "type": tx.type,
            },
        )
        return tx

    async def get_by_id(self, tx_id: UUID) -> FinancialTransaction | None:
        result = await self.session.execute(
            select(FinancialTransaction).where(FinancialTransaction.id == tx_id)
        )
        return result.scalar_one_or_none()

    async def list_for_clinic(
        self,
        clinic_id: UUID,
        cashbox_id: UUID | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        query: Select[tuple[FinancialTransaction]] = select(FinancialTransaction).where(
            FinancialTransaction.clinic_id == clinic_id,
        )
        if cashbox_id:
            query = query.where(FinancialTransaction.cashbox_id == cashbox_id)
        if type_filter:
            query = query.where(FinancialTransaction.type == type_filter)
        if date_from:
            query = query.where(FinancialTransaction.happened_at >= date_from)
        if date_to:
            query = query.where(FinancialTransaction.happened_at <= date_to)

        query = query.order_by(
            FinancialTransaction.happened_at.desc(),
        ).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_balance_for_cashbox(
        self,
        clinic_id: UUID,
        cashbox_id: UUID,
    ) -> Decimal:
        amount_case = func.sum(
            case(
                (FinancialTransaction.type == "income", FinancialTransaction.amount),
                else_=-FinancialTransaction.amount,
            )
        )
        result = await self.session.execute(
            select(func.coalesce(amount_case, 0)).where(
                FinancialTransaction.clinic_id == clinic_id,
                FinancialTransaction.cashbox_id == cashbox_id,
            )
        )
        return Decimal(result.scalar() or 0)

