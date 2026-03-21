"""Admin Loyalty API: subscription packages, customer subscriptions and wallets."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.family_link_dto import (
    FamilyLinkCreate,
    FamilyLinkRead,
    FamilyLinkUpdate,
)
from src.application.dto.loyalty_dto import (
    CustomerSubscriptionRead,
    CustomerSubscriptionWithSharedRead,
    SharedWithItem,
    SubscriptionPackageCreate,
    SubscriptionPackageRead,
    SubscriptionPackageUpdate,
    WalletRead,
    WalletTransactionRead,
    SubscriptionUsageRead,
)
from src.application.dto.loyalty_campaign_dto import (
    LoyaltyCampaignRunResult,
    LoyaltyCampaignSettingsRead,
    LoyaltyCampaignSettingsUpdate,
    default_loyalty_campaign_settings_read,
)
from src.application.services.family_link_service import FamilyLinkService
from src.application.services.loyalty_campaign_engine import (
    get_or_create_loyalty_campaign_settings,
    run_campaigns_for_clinic,
)
from src.domain.entities.loyalty_campaign_settings import LoyaltyCampaignSettings
from src.application.services.loyalty_service import LoyaltyService
from src.application.services.wallet_service import WalletService
from src.domain.entities.loyalty_policy import LoyaltyPolicy
from src.domain.entities.wallet import Wallet
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.package_family_link import PackageFamilyLink
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.loyalty_repository import (
    CustomerSubscriptionRepository,
    WalletRepository,
    WalletTransactionRepository,
)
from src.infrastructure.database.loyalty_repo_impl import (
    CustomerSubscriptionRepositoryImpl,
    WalletRepositoryImpl,
    WalletTransactionRepositoryImpl,
)


router = APIRouter(
    prefix="/admin/loyalty",
    tags=["admin-loyalty"],
    dependencies=[Depends(require_permissions("view_loyalty"))],
)


@router.get(
    "/packages",
    response_model=list[SubscriptionPackageRead],
)
async def list_subscription_packages(
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[SubscriptionPackageRead]:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LoyaltyService(session)
    packages = await service.list_packages_for_clinic(
        clinic_id=context.clinic_id,
        is_active=is_active,
    )
    return [SubscriptionPackageRead.model_validate(p) for p in packages]


@router.post(
    "/packages",
    response_model=SubscriptionPackageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def create_subscription_package(
    body: SubscriptionPackageCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> SubscriptionPackageRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LoyaltyService(session)
    try:
        package = await service.create_package(
            clinic_id=context.clinic_id,
            code=body.code,
            name=body.name,
            kind=body.kind,
            price=body.price,
            services_included=body.services_included,
            total_visits=body.total_visits,
            total_amount=body.total_amount,
            validity_days=body.validity_days,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    await session.commit()
    return SubscriptionPackageRead.model_validate(package)


@router.patch(
    "/packages/{package_id}",
    response_model=SubscriptionPackageRead,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def update_subscription_package(
    package_id: UUID,
    body: SubscriptionPackageUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> SubscriptionPackageRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LoyaltyService(session)
    package = await service.get_package(package_id)
    if not package or package.clinic_id != context.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription package not found",
        )

    if body.name is not None:
        package.name = body.name
    if body.description is not None:
        package.description = body.description
    if body.kind is not None:
        package.kind = body.kind
    if body.services_included is not None:
        package.services_included = body.services_included
    if body.total_visits is not None:
        package.total_visits = body.total_visits
    if body.total_amount is not None:
        package.total_amount = body.total_amount
    if body.price is not None:
        package.price = body.price
    if body.validity_days is not None:
        package.validity_days = body.validity_days
    if body.is_active is not None:
        package.is_active = body.is_active

    # G3: validate kind-specific fields before save
    effective_kind = package.kind or ""
    if effective_kind in ("COUNT_BASED", "visits"):
        if package.total_visits is None or package.total_visits <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="total_visits is required and must be > 0 when kind is COUNT_BASED",
            )
    elif effective_kind in ("BALANCE_BASED", "balance"):
        if package.total_amount is None or package.total_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="total_amount is required and must be > 0 when kind is BALANCE_BASED",
            )

    package = await service.update_package(package)
    await session.commit()
    return SubscriptionPackageRead.model_validate(package)


@router.delete(
    "/packages/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def delete_subscription_package(
    package_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> None:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LoyaltyService(session)
    package = await service.get_package(package_id)
    if not package or package.clinic_id != context.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription package not found",
        )
    await service.delete_package(package_id)
    await session.commit()


@router.get(
    "/customer-subscriptions",
    response_model=list[CustomerSubscriptionRead],
)
async def list_customer_subscriptions(
    patient_id: UUID | None = Query(None),
    only_active: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[CustomerSubscriptionRead]:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    # Use repository directly for flexible listing.
    repo: CustomerSubscriptionRepository = CustomerSubscriptionRepositoryImpl(session)
    if not patient_id:
        # For Phase 1, require patient_id to avoid heavy scans.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id is required for now",
        )
    items = await repo.list_for_patient(
        clinic_id=context.clinic_id,
        patient_id=patient_id,
        only_active=only_active,
    )
    return [CustomerSubscriptionRead.model_validate(s) for s in items]


@router.get(
    "/customer-subscriptions/{subscription_id}",
    response_model=CustomerSubscriptionWithSharedRead,
)
async def get_customer_subscription(
    subscription_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> CustomerSubscriptionWithSharedRead:
    """Get one customer subscription with shared_with (B6.1 FamilyLink)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    repo: CustomerSubscriptionRepository = CustomerSubscriptionRepositoryImpl(session)
    sub = await repo.get_by_id(subscription_id)
    if not sub or sub.clinic_id != context.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    # Load family members (shared_with)
    family_result = await session.execute(
        sa.select(PackageFamilyLink.patient_id).where(
            PackageFamilyLink.customer_subscription_id == subscription_id,
        )
    )
    family_ids = [row[0] for row in family_result.all()]
    shared_with: list[SharedWithItem] = []
    if family_ids:
        patients_result = await session.execute(
            sa.select(Patient.id, Patient.full_name).where(
                Patient.id.in_(family_ids),
                Patient.clinic_id == context.clinic_id,
            )
        )
        name_by_id = {row[0]: (row[1] or "") for row in patients_result.all()}
        for pid in family_ids:
            shared_with.append(
                SharedWithItem(patient_id=pid, patient_name=name_by_id.get(pid, "")),
            )
    base = CustomerSubscriptionRead.model_validate(sub)
    return CustomerSubscriptionWithSharedRead(**base.model_dump(), shared_with=shared_with)


@router.post(
    "/customer-subscriptions/{subscription_id}/family-members",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def add_family_member(
    subscription_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    """B6.1: Add family member who can use this subscription. Body: { \"patient_id\": \"uuid\" }."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    patient_id = body.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patient_id required")
    try:
        pid = UUID(patient_id) if isinstance(patient_id, str) else patient_id
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid patient_id")
    service = LoyaltyService(session)
    try:
        await service.add_family_member(
            clinic_id=context.clinic_id,
            subscription_id=subscription_id,
            patient_id=pid,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await session.commit()
    return {"ok": True}


@router.delete(
    "/customer-subscriptions/{subscription_id}/family-members/{patient_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def remove_family_member(
    subscription_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    """B6.1: Remove family member from subscription."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = LoyaltyService(session)
    try:
        await service.remove_family_member(
            clinic_id=context.clinic_id,
            subscription_id=subscription_id,
            patient_id=patient_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    await session.commit()
    return {"ok": True}


@router.get(
    "/family-links",
    response_model=list[FamilyLinkRead],
)
async def list_family_links_for_patient(
    patient_id: UUID = Query(..., description="Primary or related patient"),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[FamilyLinkRead]:
    """Clinic-scoped family links where the patient is primary or related (LOY_FAMILY_013)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = FamilyLinkService(session)
    rows = await service.list_for_patient(context.clinic_id, patient_id)
    return [FamilyLinkRead.model_validate(r) for r in rows]


@router.post(
    "/family-links",
    response_model=FamilyLinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def create_family_link_row(
    body: FamilyLinkCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> FamilyLinkRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = FamilyLinkService(session)
    try:
        row = await service.create_family_link(
            context.clinic_id,
            primary_patient_id=body.primary_patient_id,
            related_patient_id=body.related_patient_id,
            relation_type=body.relation_type,
            can_spend_from_owner_loyalty=body.can_spend_from_owner_loyalty,
            can_view_owner_history=body.can_view_owner_history,
            spending_limit_total=body.spending_limit_total,
            spending_limit_periodic=body.spending_limit_periodic,
            valid_until=body.valid_until,
            created_by=context.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await session.commit()
    await session.refresh(row)
    return FamilyLinkRead.model_validate(row)


@router.patch(
    "/family-links/{link_id}",
    response_model=FamilyLinkRead,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def update_family_link_row(
    link_id: UUID,
    body: FamilyLinkUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> FamilyLinkRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = FamilyLinkService(session)
    try:
        row = await service.update_family_link(
            context.clinic_id,
            link_id,
            body.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    await session.commit()
    await session.refresh(row)
    return FamilyLinkRead.model_validate(row)


@router.post(
    "/family-links/{link_id}/deactivate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def deactivate_family_link_row(
    link_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = FamilyLinkService(session)
    try:
        await service.deactivate_family_link(context.clinic_id, link_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    await session.commit()
    return {"ok": True}


@router.get(
    "/wallets",
    response_model=list[WalletRead],
)
async def list_wallets(
    patient_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[WalletRead]:
    """Phase 1: simple lookup by patient, no global search index."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    repo: WalletRepository = WalletRepositoryImpl(session)
    items: list[WalletRead] = []
    if patient_id:
        wallet = await repo.get_for_patient(
            clinic_id=context.clinic_id,
            patient_id=patient_id,
        )
        if wallet:
            items.append(WalletRead.model_validate(wallet))
        return items

    # No list-all implementation yet to avoid scanning all wallets.
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Specify patient_id to search wallet",
    )


@router.get(
    "/wallets/{wallet_id}/transactions",
    response_model=list[WalletTransactionRead],
)
async def list_wallet_transactions(
    wallet_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[WalletTransactionRead]:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    # Ensure wallet belongs to current clinic.
    wallet = await session.get(Wallet, wallet_id)
    if not wallet or wallet.clinic_id != context.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)
    txs = await tx_repo.list_for_wallet(wallet_id=wallet_id)
    return [WalletTransactionRead.model_validate(t) for t in txs]


@router.get(
    "/subscription-usages",
    response_model=list[SubscriptionUsageRead],
)
async def list_subscription_usages(
    patient_id: UUID = Query(...),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[SubscriptionUsageRead]:
    """List subscription usages for a patient in the clinic."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    query = (
        sa.select(SubscriptionUsage)
        .join(
            CustomerSubscription,
            SubscriptionUsage.customer_subscription_id == CustomerSubscription.id,
        )
        .where(
            SubscriptionUsage.clinic_id == context.clinic_id,
            sa.or_(
                CustomerSubscription.patient_id == patient_id,
                SubscriptionUsage.beneficiary_patient_id == patient_id,
            ),
        )
    )
    if date_from is not None:
        query = query.where(SubscriptionUsage.used_at >= date_from)
    if date_to is not None:
        query = query.where(SubscriptionUsage.used_at <= date_to)

    result = await session.execute(query)
    usages = list(result.scalars().all())
    return [SubscriptionUsageRead.model_validate(u) for u in usages]


@router.get(
    "/summary-by-contact",
)
async def get_loyalty_summary_by_contact(
    contact_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    """Return loyalty snapshot for contact: mapped patient + subscriptions + wallet."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    contact = await session.get(OmniContact, contact_id)
    if not contact or contact.business_account_id != context.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found for clinic",
        )

    phone = contact.primary_phone
    if not phone:
        return {
            "patient_id": None,
            "patient_full_name": None,
            "patient_phone": None,
            "subscriptions": [],
            "wallet": None,
            "wallet_transactions": [],
        }

    patient_result = await session.execute(
        sa.select(Patient).where(
            Patient.clinic_id == context.clinic_id,
            Patient.phone == phone,
            Patient.deleted_at.is_(None),
        ).limit(1)
    )
    patient: Patient | None = patient_result.scalar_one_or_none()
    if not patient:
        return {
            "patient_id": None,
            "patient_full_name": None,
            "patient_phone": phone,
            "subscriptions": [],
            "wallet": None,
            "wallet_transactions": [],
        }

    loyalty_service = LoyaltyService(session)
    wallet_repo: WalletRepository = WalletRepositoryImpl(session)
    tx_repo: WalletTransactionRepository = WalletTransactionRepositoryImpl(session)

    subs = await loyalty_service.customer_repo.list_for_patient(
        clinic_id=context.clinic_id,
        patient_id=patient.id,
        only_active=False,
    )
    wallet = await wallet_repo.get_for_patient(
        clinic_id=context.clinic_id,
        patient_id=patient.id,
    )
    wallet_txs: list[WalletTransactionRead] = []
    if wallet:
        txs = await tx_repo.list_for_wallet(wallet.id)
        wallet_txs = [WalletTransactionRead.model_validate(t) for t in txs]

    return {
        "patient_id": str(patient.id),
        "patient_full_name": patient.full_name,
        "patient_phone": patient.phone,
        "subscriptions": [CustomerSubscriptionRead.model_validate(s) for s in subs],
        "wallet": WalletRead.model_validate(wallet) if wallet else None,
        "wallet_transactions": wallet_txs,
    }


@router.get(
    "/policy",
)
async def get_loyalty_policy(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    """Return loyalty policy for clinic (or defaults if not configured)."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    result = await session.execute(
        sa.select(LoyaltyPolicy).where(
            LoyaltyPolicy.clinic_id == context.clinic_id,
        )
    )
    policy: LoyaltyPolicy | None = result.scalar_one_or_none()
    if not policy:
        # Default policy: no cashback, no points usage.
        return {
            "clinic_id": str(context.clinic_id),
            "cashback_percent": "0.00",
            "min_check_for_cashback": None,
            "allow_pay_with_points": False,
            "max_points_share": None,
            "points_expire_days": None,
        }
    return {
        "clinic_id": str(policy.clinic_id),
        "cashback_percent": str(policy.cashback_percent),
        "min_check_for_cashback": (
            str(policy.min_check_for_cashback)
            if policy.min_check_for_cashback is not None
            else None
        ),
        "allow_pay_with_points": policy.allow_pay_with_points,
        "max_points_share": (
            str(policy.max_points_share) if policy.max_points_share is not None else None
        ),
        "points_expire_days": policy.points_expire_days,
    }


@router.post(
    "/policy",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def create_loyalty_policy(
    body: dict,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    """Create loyalty policy for clinic. Only one policy per clinic is allowed."""
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    existing = await session.execute(
        sa.select(LoyaltyPolicy).where(
            LoyaltyPolicy.clinic_id == context.clinic_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loyalty policy already exists for clinic",
        )
    policy = LoyaltyPolicy(
        clinic_id=context.clinic_id,
        cashback_percent=body.get("cashback_percent", 0),
        min_check_for_cashback=body.get("min_check_for_cashback"),
        allow_pay_with_points=bool(body.get("allow_pay_with_points", False)),
        max_points_share=body.get("max_points_share"),
        points_expire_days=body.get("points_expire_days"),
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return await get_loyalty_policy(session=session, context=context)


@router.patch(
    "/policy",
    dependencies=[Depends(require_permissions("manage_loyalty"))],
)
async def update_loyalty_policy(
    body: dict,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    """Update existing loyalty policy for clinic or create if missing."""
    result = await session.execute(
        sa.select(LoyaltyPolicy).where(
            LoyaltyPolicy.clinic_id == context.clinic_id,
        )
    )
    policy: LoyaltyPolicy | None = result.scalar_one_or_none()
    if not policy:
        return await create_loyalty_policy(
            body=body,
            session=session,
            context=context,
        )

    for field in (
        "cashback_percent",
        "min_check_for_cashback",
        "allow_pay_with_points",
        "max_points_share",
        "points_expire_days",
    ):
        if field in body:
            setattr(policy, field, body[field])
    await session.commit()
    await session.refresh(policy)
    return await get_loyalty_policy(session=session, context=context)


@router.get(
    "/campaign-settings",
    response_model=LoyaltyCampaignSettingsRead,
    dependencies=[Depends(require_permissions("view_loyalty"))],
)
async def get_loyalty_campaign_settings(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LoyaltyCampaignSettingsRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    result = await session.execute(
        sa.select(LoyaltyCampaignSettings).where(
            LoyaltyCampaignSettings.clinic_id == context.clinic_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return default_loyalty_campaign_settings_read(context.clinic_id)
    return LoyaltyCampaignSettingsRead.model_validate(row)


@router.patch(
    "/campaign-settings",
    response_model=LoyaltyCampaignSettingsRead,
    dependencies=[Depends(require_permissions("manage_loyalty_campaigns"))],
)
async def patch_loyalty_campaign_settings(
    body: LoyaltyCampaignSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LoyaltyCampaignSettingsRead:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    row = await get_or_create_loyalty_campaign_settings(session, context.clinic_id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return LoyaltyCampaignSettingsRead.model_validate(row)


@router.post(
    "/campaigns/run",
    response_model=LoyaltyCampaignRunResult,
    dependencies=[Depends(require_permissions("run_loyalty_campaigns"))],
)
async def post_run_loyalty_campaigns(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> LoyaltyCampaignRunResult:
    if context.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    result = await run_campaigns_for_clinic(session, context.clinic_id)
    await session.commit()
    return result

