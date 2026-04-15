"""SQLAlchemy implementations for loyalty subscription and wallet repositories."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.entities.wallet import Wallet
from src.domain.entities.wallet_transaction import WalletTransaction
from src.domain.interfaces.repositories.loyalty_repository import (
    CustomerSubscriptionRepository,
    SubscriptionPackageRepository,
    SubscriptionUsageRepository,
    WalletRepository,
    WalletTransactionRepository,
)


class SubscriptionPackageRepositoryImpl(SubscriptionPackageRepository):
    """SQLAlchemy implementation of SubscriptionPackageRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, package: SubscriptionPackage) -> SubscriptionPackage:
        self.session.add(package)
        await self.session.flush()
        await self.session.refresh(package)
        return package

    async def update(self, package: SubscriptionPackage) -> SubscriptionPackage:
        await self.session.flush()
        await self.session.refresh(package)
        return package

    async def delete(self, package_id: UUID) -> None:
        obj = await self.get_by_id(package_id)
        if obj is not None:
            await self.session.delete(obj)
            await self.session.flush()

    async def get_by_id(self, package_id: UUID) -> SubscriptionPackage | None:
        result = await self.session.execute(
            select(SubscriptionPackage).where(SubscriptionPackage.id == package_id)
        )
        return result.scalar_one_or_none()

    async def list_for_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ) -> list[SubscriptionPackage]:
        query: Select[tuple[SubscriptionPackage]] = select(SubscriptionPackage).where(
            SubscriptionPackage.clinic_id == clinic_id
        )
        if is_active is not None:
            query = query.where(SubscriptionPackage.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class CustomerSubscriptionRepositoryImpl(CustomerSubscriptionRepository):
    """SQLAlchemy implementation of CustomerSubscriptionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        subscription: CustomerSubscription,
    ) -> CustomerSubscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def update(
        self,
        subscription: CustomerSubscription,
    ) -> CustomerSubscription:
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def get_by_id(
        self,
        subscription_id: UUID,
    ) -> CustomerSubscription | None:
        result = await self.session.execute(
            select(CustomerSubscription).where(CustomerSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        only_active: bool = False,
    ) -> list[CustomerSubscription]:
        query: Select[tuple[CustomerSubscription]] = select(CustomerSubscription).where(
            CustomerSubscription.clinic_id == clinic_id,
            CustomerSubscription.patient_id == patient_id,
        )
        if only_active:
            query = query.where(CustomerSubscription.status == "active")
        result = await self.session.execute(query)
        return list(result.scalars().all())


class SubscriptionUsageRepositoryImpl(SubscriptionUsageRepository):
    """SQLAlchemy implementation of SubscriptionUsageRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, usage: SubscriptionUsage) -> SubscriptionUsage:
        self.session.add(usage)
        await self.session.flush()
        await self.session.refresh(usage)
        return usage

    async def list_for_subscription(
        self,
        customer_subscription_id: UUID,
    ) -> list[SubscriptionUsage]:
        result = await self.session.execute(
            select(SubscriptionUsage).where(
                SubscriptionUsage.customer_subscription_id == customer_subscription_id
            )
        )
        return list(result.scalars().all())


class WalletRepositoryImpl(WalletRepository):
    """SQLAlchemy implementation of WalletRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
    ) -> Wallet | None:
        result = await self.session.execute(
            select(Wallet).where(
                Wallet.clinic_id == clinic_id,
                Wallet.patient_id == patient_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, wallet: Wallet) -> Wallet:
        self.session.add(wallet)
        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet

    async def update(self, wallet: Wallet) -> Wallet:
        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet


class WalletTransactionRepositoryImpl(WalletTransactionRepository):
    """SQLAlchemy implementation of WalletTransactionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        tx: WalletTransaction,
    ) -> WalletTransaction:
        self.session.add(tx)
        await self.session.flush()
        await self.session.refresh(tx)
        return tx

    async def list_for_wallet(
        self,
        wallet_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[WalletTransaction]:
        query: Select[tuple[WalletTransaction]] = select(WalletTransaction).where(
            WalletTransaction.wallet_id == wallet_id,
        )
        if date_from:
            query = query.where(WalletTransaction.happened_at >= date_from)
        if date_to:
            query = query.where(WalletTransaction.happened_at <= date_to)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_balance_for_wallet(
        self,
        wallet_id: UUID,
    ) -> Decimal:
        # Acquire row-level lock on wallet to prevent concurrent balance races
        await self.session.execute(
            select(Wallet.id).where(Wallet.id == wallet_id).with_for_update()
        )

        amount_case = func.sum(
            case(
                (WalletTransaction.type == "earn", WalletTransaction.amount),
                else_=-WalletTransaction.amount,
            )
        )
        result = await self.session.execute(
            select(func.coalesce(amount_case, 0)).where(
                WalletTransaction.wallet_id == wallet_id,
            )
        )
        return Decimal(result.scalar() or 0)

