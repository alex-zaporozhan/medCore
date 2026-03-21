"""Application service for loyalty wallet operations (cashback/points)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.family_link_service import FamilyLinkService
from src.core.metrics import loyalty_family_spend_denied_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.wallet import Wallet
from src.domain.entities.wallet_transaction import WalletTransaction
from src.domain.interfaces.repositories.loyalty_repository import (
    WalletRepository,
    WalletTransactionRepository,
)
from src.infrastructure.database.loyalty_repo_impl import (
    WalletRepositoryImpl,
    WalletTransactionRepositoryImpl,
)
from src.application.loyalty_completion_errors import LoyaltyVisitCompletionBlocked


class InsufficientWalletBalance(LoyaltyVisitCompletionBlocked):
    """Raised when wallet does not have enough points/balance for spending."""

    code = "insufficient_wallet_balance"


class WalletFamilySpendDenied(LoyaltyVisitCompletionBlocked):
    """Raised when spending for another patient is not allowed via FamilyLink or limits."""

    code = "wallet_family_spend_denied"


@dataclass
class EarnPointsInput:
    clinic_id: UUID
    patient_id: UUID
    amount: Decimal
    happened_at: datetime
    booking_id: UUID | None = None
    subscription_id: UUID | None = None
    description: str | None = None


@dataclass
class SpendPointsInput:
    clinic_id: UUID
    patient_id: UUID
    amount: Decimal
    happened_at: datetime
    booking_id: UUID | None = None
    description: str | None = None
    # Patient who receives the benefit; defaults to wallet owner. Requires FamilyLink if different.
    beneficiary_patient_id: UUID | None = None


@dataclass
class ExpirePointsInput:
    wallet_id: UUID
    amount: Decimal
    happened_at: datetime
    description: str | None = None


class WalletService:
    """Service for loyalty wallet (points/cashback) operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.wallet_repo: WalletRepository = WalletRepositoryImpl(session)
        self.tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(
            session
        )

    async def get_or_create_wallet(
        self,
        clinic_id: UUID,
        patient_id: UUID,
    ) -> Wallet:
        """Idempotent wallet creation for given clinic and patient."""
        wallet = await self.wallet_repo.get_for_patient(
            clinic_id=clinic_id,
            patient_id=patient_id,
        )
        if wallet is not None:
            return wallet
        wallet = Wallet(
            clinic_id=clinic_id,
            patient_id=patient_id,
        )
        wallet = await self.wallet_repo.create(wallet)
        return wallet

    async def earn_points(self, data: EarnPointsInput) -> WalletTransaction:
        """Accrue points/cashback to patient wallet."""
        wallet = await self.get_or_create_wallet(
            clinic_id=data.clinic_id,
            patient_id=data.patient_id,
        )
        tx = WalletTransaction(
            clinic_id=data.clinic_id,
            wallet_id=wallet.id,
            type="earn",
            amount=data.amount,
            happened_at=data.happened_at,
            booking_id=data.booking_id,
            subscription_id=data.subscription_id,
            description=data.description,
        )
        tx = await self.tx_repo.create(tx)

        # Sync cached balance field on wallet
        wallet.balance = await self.tx_repo.get_balance_for_wallet(wallet.id)
        wallet.updated_at = data.happened_at
        await self.wallet_repo.update(wallet)

        return tx

    async def spend_points(self, data: SpendPointsInput) -> WalletTransaction:
        """Spend points from patient wallet with limit check.

        If ``beneficiary_patient_id`` is set and differs from wallet owner, an active
        FamilyLink with spend permission and shared limits (subscription + wallet) applies.
        """
        wallet = await self.get_or_create_wallet(
            clinic_id=data.clinic_id,
            patient_id=data.patient_id,
        )
        current_balance = await self.tx_repo.get_balance_for_wallet(wallet.id)
        if data.amount > current_balance:
            raise InsufficientWalletBalance("Not enough points in wallet")

        beneficiary = (
            data.beneficiary_patient_id
            if data.beneficiary_patient_id is not None
            else data.patient_id
        )
        family_link_id = None
        if beneficiary != data.patient_id:
            fls = FamilyLinkService(self.session)
            link = await fls.get_active_spend_link(
                data.clinic_id,
                data.patient_id,
                beneficiary,
                data.happened_at,
            )
            if link is None:
                loyalty_family_spend_denied_total.labels(
                    clinic_bucket=clinic_bucket_label(data.clinic_id),
                    reason="wallet_not_linked",
                ).inc()
                raise WalletFamilySpendDenied(
                    "Beneficiary is not allowed to spend from this wallet"
                )
            try:
                await fls.assert_spend_within_limits(
                    link,
                    used_amount=data.amount,
                    used_visits=None,
                    at_time=data.happened_at,
                )
            except ValueError as e:
                msg = str(e)
                if "family_spend_limit_total" in msg:
                    loyalty_family_spend_denied_total.labels(
                        clinic_bucket=clinic_bucket_label(data.clinic_id),
                        reason="limit_total",
                    ).inc()
                elif "family_spend_limit_periodic" in msg:
                    loyalty_family_spend_denied_total.labels(
                        clinic_bucket=clinic_bucket_label(data.clinic_id),
                        reason="limit_periodic",
                    ).inc()
                else:
                    loyalty_family_spend_denied_total.labels(
                        clinic_bucket=clinic_bucket_label(data.clinic_id),
                        reason="limit",
                    ).inc()
                raise WalletFamilySpendDenied(msg) from e
            family_link_id = link.id

        tx = WalletTransaction(
            clinic_id=data.clinic_id,
            wallet_id=wallet.id,
            type="spend",
            amount=data.amount,
            happened_at=data.happened_at,
            booking_id=data.booking_id,
            description=data.description,
            beneficiary_patient_id=beneficiary
            if beneficiary != data.patient_id
            else None,
            family_link_id=family_link_id,
        )
        tx = await self.tx_repo.create(tx)

        wallet.balance = await self.tx_repo.get_balance_for_wallet(wallet.id)
        wallet.updated_at = data.happened_at
        await self.wallet_repo.update(wallet)

        return tx

    async def expire_points(self, data: ExpirePointsInput) -> WalletTransaction:
        """Expire points from wallet (periodic job)."""
        current_balance = await self.tx_repo.get_balance_for_wallet(data.wallet_id)
        amount_to_expire = min(current_balance, data.amount)
        tx = WalletTransaction(
            clinic_id=None,  # will be set from existing wallet
            wallet_id=data.wallet_id,
            type="expire",
            amount=amount_to_expire,
            happened_at=data.happened_at,
            description=data.description,
        )
        # Load wallet to get clinic_id and update balance
        wallet = None
        # NOTE: using get_for_patient is not suitable here; we rely on direct session.get
        wallet = await self.session.get(Wallet, data.wallet_id)
        if wallet is None:
            raise ValueError("Wallet not found")
        tx.clinic_id = wallet.clinic_id
        tx = await self.tx_repo.create(tx)

        wallet.balance = await self.tx_repo.get_balance_for_wallet(wallet.id)
        wallet.updated_at = data.happened_at
        await self.wallet_repo.update(wallet)

        return tx

