"""Repository interfaces for loyalty subscriptions and wallets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.entities.wallet import Wallet
from src.domain.entities.wallet_transaction import WalletTransaction


class SubscriptionPackageRepository(ABC):
    """Repository interface for SubscriptionPackage entity."""

    @abstractmethod
    async def create(self, package: SubscriptionPackage) -> SubscriptionPackage:
        ...

    @abstractmethod
    async def update(self, package: SubscriptionPackage) -> SubscriptionPackage:
        ...

    @abstractmethod
    async def delete(self, package_id: UUID) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, package_id: UUID) -> SubscriptionPackage | None:
        ...

    @abstractmethod
    async def list_for_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ) -> Sequence[SubscriptionPackage]:
        ...


class CustomerSubscriptionRepository(ABC):
    """Repository interface for CustomerSubscription entity."""

    @abstractmethod
    async def create(
        self,
        subscription: CustomerSubscription,
    ) -> CustomerSubscription:
        ...

    @abstractmethod
    async def update(
        self,
        subscription: CustomerSubscription,
    ) -> CustomerSubscription:
        ...

    @abstractmethod
    async def get_by_id(
        self,
        subscription_id: UUID,
    ) -> CustomerSubscription | None:
        ...

    @abstractmethod
    async def list_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        only_active: bool = False,
    ) -> Sequence[CustomerSubscription]:
        ...


class SubscriptionUsageRepository(ABC):
    """Repository interface for SubscriptionUsage entity."""

    @abstractmethod
    async def create(self, usage: SubscriptionUsage) -> SubscriptionUsage:
        ...

    @abstractmethod
    async def list_for_subscription(
        self,
        customer_subscription_id: UUID,
    ) -> Sequence[SubscriptionUsage]:
        ...


class WalletRepository(ABC):
    """Repository interface for Wallet entity."""

    @abstractmethod
    async def get_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
    ) -> Wallet | None:
        ...

    @abstractmethod
    async def create(self, wallet: Wallet) -> Wallet:
        ...

    @abstractmethod
    async def update(self, wallet: Wallet) -> Wallet:
        ...


class WalletTransactionRepository(ABC):
    """Repository interface for WalletTransaction entity."""

    @abstractmethod
    async def create(
        self,
        tx: WalletTransaction,
    ) -> WalletTransaction:
        ...

    @abstractmethod
    async def list_for_wallet(
        self,
        wallet_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Sequence[WalletTransaction]:
        ...

    @abstractmethod
    async def get_balance_for_wallet(
        self,
        wallet_id: UUID,
    ) -> Decimal:
        ...

