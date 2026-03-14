"""Application service for loyalty subscriptions (packages and customer subscriptions)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.interfaces.repositories.loyalty_repository import (
    CustomerSubscriptionRepository,
    SubscriptionPackageRepository,
    SubscriptionUsageRepository,
)
from src.infrastructure.database.loyalty_repo_impl import (
    CustomerSubscriptionRepositoryImpl,
    SubscriptionPackageRepositoryImpl,
    SubscriptionUsageRepositoryImpl,
)


class SubscriptionBusinessError(Exception):
    """Base class for subscription-related business errors with code attribute."""

    code: str = "subscription_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InsufficientSubscriptionBalance(SubscriptionBusinessError):
    """Raised when subscription does not have enough remaining balance/visits."""

    code = "insufficient_subscription_balance"


class SubscriptionExpired(SubscriptionBusinessError):
    """Raised when trying to use an expired subscription."""

    code = "subscription_expired"


@dataclass
class PurchaseSubscriptionInput:
    clinic_id: UUID
    patient_id: UUID
    package_id: UUID
    payment_id: UUID | None
    purchased_at: datetime


@dataclass
class UseSubscriptionForBookingInput:
    clinic_id: UUID
    booking_id: UUID
    subscription_id: UUID
    used_visits: int | None
    used_amount: Decimal | None
    used_at: datetime


class LoyaltyService:
    """Service encapsulating core loyalty subscription flows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.package_repo: SubscriptionPackageRepository = SubscriptionPackageRepositoryImpl(
            session
        )
        self.customer_repo: CustomerSubscriptionRepository = CustomerSubscriptionRepositoryImpl(
            session
        )
        self.usage_repo: SubscriptionUsageRepository = SubscriptionUsageRepositoryImpl(
            session
        )

    async def select_subscription_for_booking(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        booking_id: UUID | None,
        on_date: datetime,
    ) -> CustomerSubscription | None:
        """Select best active subscription for patient by deterministic priority.

        Priority strategy (Phase 1, kept simple and documented here):
        - only subscriptions in given clinic, for patient, status=active;
        - only subscriptions that are not expired on on_date;
        - sort by:
          1) earlier expires_at (sooner to burn) first, treating NULL as far future;
          2) more specific packages (with non-empty services_included) before generic ones;
          3) higher remaining_visits then higher remaining_amount;
          4) older purchased_at first for stability.
        """
        stmt = select(CustomerSubscription).where(
            CustomerSubscription.clinic_id == clinic_id,
            CustomerSubscription.patient_id == patient_id,
            CustomerSubscription.status == "active",
        )
        result = await self.session.execute(stmt)
        subs: list[CustomerSubscription] = list(result.scalars().all())
        if not subs:
            return None

        active: list[CustomerSubscription] = []
        for s in subs:
            if s.expires_at is not None and s.expires_at < on_date:
                continue
            active.append(s)
        if not active:
            return None

        # Load packages for priority calculation.
        package_ids = {s.subscription_package_id for s in active}
        pkg_stmt = select(SubscriptionPackage).where(
            SubscriptionPackage.id.in_(list(package_ids))
        )
        pkg_result = await self.session.execute(pkg_stmt)
        packages = {p.id: p for p in pkg_result.scalars().all()}

        def _priority_key(s: CustomerSubscription) -> tuple:
            pkg = packages.get(s.subscription_package_id)
            expires = s.expires_at or (on_date + timedelta(days=3650))
            has_services = bool(pkg and pkg.services_included)
            remaining_visits = s.remaining_visits or 0
            remaining_amount = s.remaining_amount or Decimal("0")
            return (
                expires,
                0 if has_services else 1,
                -remaining_visits,
                -remaining_amount,
                s.purchased_at,
            )

        active.sort(key=_priority_key)
        return active[0]

    # Packages CRUD
    async def create_package(
        self,
        clinic_id: UUID,
        code: str,
        name: str,
        kind: str,
        price: Decimal,
        services_included: list[UUID],
        total_visits: int | None = None,
        total_amount: Decimal | None = None,
        validity_days: int | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> SubscriptionPackage:
        package = SubscriptionPackage(
            clinic_id=clinic_id,
            code=code,
            name=name,
            description=description,
            kind=kind,
            services_included=services_included,
            total_visits=total_visits,
            total_amount=total_amount,
            price=price,
            validity_days=validity_days,
            is_active=is_active,
        )
        return await self.package_repo.create(package)

    async def update_package(
        self,
        package: SubscriptionPackage,
    ) -> SubscriptionPackage:
        return await self.package_repo.update(package)

    async def delete_package(self, package_id: UUID) -> None:
        await self.package_repo.delete(package_id)

    async def get_package(self, package_id: UUID) -> SubscriptionPackage | None:
        return await self.package_repo.get_by_id(package_id)

    async def list_packages_for_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ) -> list[SubscriptionPackage]:
        return list(
            await self.package_repo.list_for_clinic(
                clinic_id=clinic_id,
                is_active=is_active,
            )
        )

    # Purchase / activation
    async def purchase_subscription(
        self,
        data: PurchaseSubscriptionInput,
    ) -> CustomerSubscription:
        # Idempotency guard for payment-linked purchases: if we already created
        # a subscription for this clinic/patient/package/payment_id, return it.
        if data.payment_id is not None:
            existing_stmt = select(CustomerSubscription).where(
                CustomerSubscription.clinic_id == data.clinic_id,
                CustomerSubscription.patient_id == data.patient_id,
                CustomerSubscription.subscription_package_id == data.package_id,
                CustomerSubscription.payment_id == data.payment_id,
            )
            existing_result = await self.session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                return existing

        package = await self.package_repo.get_by_id(data.package_id)
        if package is None or package.clinic_id != data.clinic_id:
            raise ValueError("Subscription package not found for clinic")

        now = data.purchased_at
        activated_at = now
        expires_at: datetime | None = None
        if package.validity_days is not None:
            expires_at = activated_at + timedelta(days=package.validity_days)

        subscription = CustomerSubscription(
            clinic_id=data.clinic_id,
            patient_id=data.patient_id,
            subscription_package_id=package.id,
            status="active",
            purchased_at=now,
            activated_at=activated_at,
            expires_at=expires_at,
            remaining_visits=package.total_visits,
            remaining_amount=package.total_amount,
            payment_id=data.payment_id,
        )
        return await self.customer_repo.create(subscription)

    async def mark_subscription_expired(self, subscription: CustomerSubscription) -> CustomerSubscription:
        subscription.status = "expired"
        return await self.customer_repo.update(subscription)

    # Usage for booking
    async def use_subscription_for_booking(
        self,
        data: UseSubscriptionForBookingInput,
    ) -> SubscriptionUsage:
        subscription = await self.customer_repo.get_by_id(data.subscription_id)
        if (
            subscription is None
            or subscription.clinic_id != data.clinic_id
            or subscription.status != "active"
        ):
            raise ValueError("Active customer subscription not found for clinic")

        if subscription.expires_at is not None and subscription.expires_at < data.used_at:
            raise SubscriptionExpired("Subscription expired")

        if data.used_visits is None and data.used_amount is None:
            raise InsufficientSubscriptionBalance(
                "Either used_visits or used_amount must be provided"
            )

        # Check remaining balance/visits
        if data.used_visits is not None:
            if subscription.remaining_visits is None:
                raise InsufficientSubscriptionBalance(
                    "Subscription does not support visit-based usage"
                )
            if data.used_visits > subscription.remaining_visits:
                raise InsufficientSubscriptionBalance("Not enough remaining visits")
            subscription.remaining_visits -= data.used_visits

        if data.used_amount is not None:
            if subscription.remaining_amount is None:
                raise InsufficientSubscriptionBalance(
                    "Subscription does not support amount-based usage"
                )
            if data.used_amount > subscription.remaining_amount:
                raise InsufficientSubscriptionBalance("Not enough remaining amount")
            subscription.remaining_amount -= data.used_amount

        # Update status if fully used
        if (
            subscription.remaining_visits is not None
            and subscription.remaining_visits <= 0
        ) or (
            subscription.remaining_amount is not None
            and subscription.remaining_amount <= Decimal("0.00")
        ):
            subscription.status = "used_up"

        await self.customer_repo.update(subscription)

        usage = SubscriptionUsage(
            clinic_id=data.clinic_id,
            customer_subscription_id=subscription.id,
            booking_id=data.booking_id,
            used_visits=data.used_visits,
            used_amount=data.used_amount,
            used_at=data.used_at,
        )
        return await self.usage_repo.create(usage)

