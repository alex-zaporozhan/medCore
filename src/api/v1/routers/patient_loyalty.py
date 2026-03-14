"""Patient Loyalty API: view own subscriptions and wallet."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.application.dto.loyalty_dto import (
    CustomerSubscriptionRead,
    PatientLoyaltyHistoryItem,
    PatientLoyaltyHistoryResponse,
    PatientLoyaltyMeResponse,
    WalletRead,
    WalletTransactionRead,
)
from src.application.services.loyalty_service import LoyaltyService
from src.application.services.wallet_service import WalletService
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.loyalty_repository import (
    SubscriptionUsageRepository,
    WalletRepository,
    WalletTransactionRepository,
)
from src.infrastructure.database.loyalty_repo_impl import (
    SubscriptionUsageRepositoryImpl,
    WalletRepositoryImpl,
    WalletTransactionRepositoryImpl,
)


router = APIRouter(
    prefix="/patient/loyalty",
    tags=["patient-loyalty"],
)


@router.get(
    "/me",
    response_model=PatientLoyaltyMeResponse,
)
async def get_my_loyalty(
    session: AsyncSession = Depends(get_session),
    current_patient: Patient = Depends(get_current_patient),
) -> PatientLoyaltyMeResponse:
    """Return active/expired subscriptions and wallet state for current patient."""
    loyalty_service = LoyaltyService(session)
    wallet_service = WalletService(session)
    wallet_repo: WalletRepository = WalletRepositoryImpl(session)
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)

    subs = await loyalty_service.customer_repo.list_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
        only_active=False,
    )
    wallet = await wallet_repo.get_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
    )
    wallet_txs: list[WalletTransactionRead] = []
    if wallet:
        txs = await tx_repo.list_for_wallet(wallet.id)
        wallet_txs = [WalletTransactionRead.model_validate(t) for t in txs]

    return PatientLoyaltyMeResponse(
        subscriptions=[CustomerSubscriptionRead.model_validate(s) for s in subs],
        wallet=WalletRead.model_validate(wallet) if wallet else None,
        wallet_transactions=wallet_txs,
    )


@router.get(
    "/history",
    response_model=PatientLoyaltyHistoryResponse,
)
async def get_my_loyalty_history(
    session: AsyncSession = Depends(get_session),
    current_patient: Patient = Depends(get_current_patient),
) -> PatientLoyaltyHistoryResponse:
    """Return chronological history of loyalty usage for current patient."""
    usage_repo: SubscriptionUsageRepository = SubscriptionUsageRepositoryImpl(session)
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)
    wallet_repo: WalletRepository = WalletRepositoryImpl(session)

    # Collect all usages for patient's subscriptions
    loyalty_service = LoyaltyService(session)
    subs = await loyalty_service.customer_repo.list_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
        only_active=False,
    )
    usages = []
    for s in subs:
        items = await usage_repo.list_for_subscription(s.id)
        usages.extend(items)

    wallet = await wallet_repo.get_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
    )
    wallet_txs = []
    if wallet:
        wallet_txs = await tx_repo.list_for_wallet(wallet.id)

    history_items: list[PatientLoyaltyHistoryItem] = []
    for u in usages:
        history_items.append(
            PatientLoyaltyHistoryItem(
                kind="subscription_usage",
                happened_at=u.used_at,
                details={
                    "subscription_id": str(u.customer_subscription_id),
                    "booking_id": str(u.booking_id),
                    "used_visits": u.used_visits,
                    "used_amount": str(u.used_amount) if u.used_amount is not None else None,
                },
            )
        )
    for tx in wallet_txs:
        history_items.append(
            PatientLoyaltyHistoryItem(
                kind=f"wallet_{tx.type}",
                happened_at=tx.happened_at,
                details={
                    "wallet_id": str(tx.wallet_id),
                    "amount": str(tx.amount),
                    "booking_id": str(tx.booking_id) if tx.booking_id else None,
                    "subscription_id": str(tx.subscription_id) if tx.subscription_id else None,
                    "description": tx.description,
                },
            )
        )

    history_items.sort(key=lambda x: x.happened_at, reverse=True)
    return PatientLoyaltyHistoryResponse(items=history_items)

