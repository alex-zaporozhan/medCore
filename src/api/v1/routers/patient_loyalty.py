"""Patient Loyalty API: view own subscriptions and wallet."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.application.dto.loyalty_dto import (
    PatientLoyaltyHistoryItem,
    PatientLoyaltyHistoryResponse,
    PatientLoyaltyMeResponseDigitalPass,
    PatientSubscriptionCard,
    WalletRead,
    WalletTransactionRead,
)
from src.application.services.loyalty_service import LoyaltyService
from src.domain.entities.patient import Patient
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.interfaces.repositories.loyalty_repository import (
    WalletRepository,
    WalletTransactionRepository,
)
from src.infrastructure.database.loyalty_repo_impl import (
    WalletRepositoryImpl,
    WalletTransactionRepositoryImpl,
)


router = APIRouter(
    prefix="/patient/loyalty",
    tags=["patient-loyalty"],
)


@router.get(
    "/me",
    response_model=PatientLoyaltyMeResponseDigitalPass,
)
async def get_my_loyalty(
    session: AsyncSession = Depends(get_session),
    current_patient: Patient = Depends(get_current_patient),
) -> PatientLoyaltyMeResponseDigitalPass:
    """Return active/expired subscriptions (with package details for Digital Pass) and wallet for current patient. B6.5."""
    from sqlalchemy import select

    loyalty_service = LoyaltyService(session)
    wallet_repo: WalletRepository = WalletRepositoryImpl(session)
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)

    subs = await loyalty_service.customer_repo.list_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
        only_active=False,
    )
    package_ids = [s.subscription_package_id for s in subs]
    packages: dict = {}
    if package_ids:
        pkg_result = await session.execute(
            select(SubscriptionPackage).where(SubscriptionPackage.id.in_(package_ids))
        )
        packages = {p.id: p for p in pkg_result.scalars().all()}
    cards: list[PatientSubscriptionCard] = []
    for s in subs:
        pkg = packages.get(s.subscription_package_id)
        cards.append(
            PatientSubscriptionCard(
                id=s.id,
                patient_id=s.patient_id,
                subscription_package_id=s.subscription_package_id,
                status=s.status,
                name=pkg.name if pkg else "",
                remaining_visits=s.remaining_visits,
                total_visits=pkg.total_visits if pkg else None,
                remaining_amount=s.remaining_amount,
                total_amount=pkg.total_amount if pkg else None,
                expires_at=s.expires_at,
                services_included=list(pkg.services_included) if pkg else [],
                purchased_at=s.purchased_at,
            )
        )
    wallet = await wallet_repo.get_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
    )
    wallet_txs: list[WalletTransactionRead] = []
    if wallet:
        txs = await tx_repo.list_for_wallet(wallet.id)
        wallet_txs = [WalletTransactionRead.model_validate(t) for t in txs]

    return PatientLoyaltyMeResponseDigitalPass(
        subscriptions=cards,
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
    """Return chronological history: own subscription/wallet usage plus owner's subscriptions when FamilyLink allows."""
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)
    wallet_repo: WalletRepository = WalletRepositoryImpl(session)

    loyalty_service = LoyaltyService(session)
    usage_rows = await loyalty_service.get_subscription_usages_for_patient_timeline(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
    )

    wallet = await wallet_repo.get_for_patient(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
    )
    wallet_txs = []
    if wallet:
        wallet_txs = await tx_repo.list_for_wallet(wallet.id)

    history_items: list[PatientLoyaltyHistoryItem] = []
    for u, meta in usage_rows:
        history_items.append(
            PatientLoyaltyHistoryItem(
                kind="subscription_usage",
                happened_at=u.used_at,
                details={
                    "subscription_id": str(u.customer_subscription_id),
                    "booking_id": str(u.booking_id),
                    "used_visits": u.used_visits,
                    "used_amount": str(u.used_amount) if u.used_amount is not None else None,
                    "beneficiary_patient_id": str(u.beneficiary_patient_id)
                    if u.beneficiary_patient_id
                    else None,
                    "family_link_id": str(u.family_link_id) if u.family_link_id else None,
                    "timeline_view": meta.get("timeline_view"),
                    "subscription_owner_patient_id": meta.get(
                        "subscription_owner_patient_id"
                    ),
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
                    "beneficiary_patient_id": str(tx.beneficiary_patient_id)
                    if getattr(tx, "beneficiary_patient_id", None)
                    else None,
                    "family_link_id": str(tx.family_link_id)
                    if getattr(tx, "family_link_id", None)
                    else None,
                },
            )
        )

    history_items.sort(key=lambda x: x.happened_at, reverse=True)
    return PatientLoyaltyHistoryResponse(items=history_items)

