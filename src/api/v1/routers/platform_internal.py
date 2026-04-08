"""Internal platform-operator API (Основатель) — separate from tenant /admin routes (ADR-007, Phase 1a)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import (
    PlatformFounderPrincipal,
    get_current_platform_founder,
    get_session,
)
from src.application.dto.platform_billing_dto import (
    PlatformCatalogPlanInternal,
    PlatformCatalogPlanUpsertRequest,
    PlatformProvisionQueueItem,
)
from src.application.services.platform_catalog_service import (
    list_catalog_plans_all,
    plan_to_internal_dto,
    upsert_catalog_plan,
)
from src.application.services.platform_billing_service import (
    PlatformProvisionRetryNotAllowed,
    admin_mark_platform_provision_closed,
    admin_force_retry_platform_provision,
    list_platform_provision_queue,
    rotate_platform_owner_invite_token,
)
from src.core.metrics import platform_provision_manual_close_total
from src.core.platform_audit import log_platform_audit
from src.domain.entities.platform_signup_intent import PlatformSignupIntent

router = APIRouter(prefix="/platform/internal", tags=["platform-internal"])


class PlatformInternalHealthResponse(BaseModel):
    """Contract for platform-internal health (no tenant/clinic fields)."""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["platform"] = Field(description="Fixed scope discriminator for clients")
    status: Literal["ok"] = Field(description="JWT validated for platform_founder principal")


class PlatformOwnerInviteMintResponse(BaseModel):
    """One-time token for owner password setup (deliver via secure channel)."""

    model_config = ConfigDict(extra="forbid")

    token: str
    expires_at: str = Field(description="ISO-8601 UTC")


class PlatformRetryProvisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class PlatformManualCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=1000)


def _provision_queue_item(row: PlatformSignupIntent) -> PlatformProvisionQueueItem:
    return PlatformProvisionQueueItem(
        intent_id=str(row.id),
        status=row.status,
        email=row.email,
        organization_id=str(row.organization_id) if row.organization_id else None,
        provision_retry_count=int(row.provision_retry_count or 0),
        provision_next_attempt_at=row.provision_next_attempt_at.isoformat()
        if row.provision_next_attempt_at
        else None,
        provision_last_error=row.provision_last_error,
        provision_dead_letter=bool(row.provision_dead_letter),
        paid_at=row.paid_at.isoformat() if row.paid_at else None,
        billing_revoked_at=row.billing_revoked_at.isoformat() if row.billing_revoked_at else None,
    )


@router.get(
    "/health",
    response_model=PlatformInternalHealthResponse,
    summary="Platform founder JWT check",
    responses={
        401: {
            "description": (
                "Missing/invalid Bearer, expired token, or wrong issuer/audience for founder realm (1a-E6)"
            )
        },
        403: {
            "description": "Inactive/unknown user, or TOTP not enrolled while PLATFORM_FOUNDER_TOTP_REQUIRED=true"
        },
        429: {"description": "Per-IP rate limit (Redis)"},
        503: {"description": "Production without PLATFORM_FOUNDER_JWT_SECRET — route disabled"},
    },
)
async def platform_internal_health(
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
) -> PlatformInternalHealthResponse:
    """Validates Bearer signed with platform founder key — not a substitute for unauthenticated k8s liveness."""
    return PlatformInternalHealthResponse(scope="platform", status="ok")


@router.get(
    "/catalog/plans",
    response_model=list[PlatformCatalogPlanInternal],
    summary="List SaaS catalog plans (Основатель)",
    description="Includes inactive plans and subscription prices for constructor / ops.",
)
async def platform_list_catalog_plans(
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformCatalogPlanInternal]:
    rows = await list_catalog_plans_all(session)
    return [plan_to_internal_dto(r) for r in rows]


@router.put(
    "/catalog/plans/{slug}",
    response_model=PlatformCatalogPlanInternal,
    summary="Create or update a catalog plan (Основатель)",
    description="Upsert by slug: bundle of option_keys plus optional monthly/annual subscription prices (RUB).",
    responses={
        400: {"description": "Invalid slug or body"},
    },
)
async def platform_upsert_catalog_plan(
    slug: str,
    body: PlatformCatalogPlanUpsertRequest,
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> PlatformCatalogPlanInternal:
    try:
        row = await upsert_catalog_plan(
            session,
            slug=slug,
            display_name=body.display_name,
            description=body.description,
            option_keys=body.option_keys,
            is_active=body.is_active,
            sort_order=body.sort_order,
            price_monthly_rub=body.price_monthly_rub,
            price_annual_rub=body.price_annual_rub,
            audit_actor_id=_principal.id,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        msg = str(exc)
        if msg == "invalid_plan_slug":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_plan_slug",
                    "message": "Slug must match ^[a-z0-9][a-z0-9_-]{0,63}$",
                },
            ) from None
        if msg.startswith("unknown_option_keys:"):
            bad_key = msg.split(":", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "unknown_option_keys",
                    "message": f"Unknown catalog option key: {bad_key}",
                },
            ) from None
        raise
    except Exception:
        await session.rollback()
        raise
    await session.refresh(row)
    log_platform_audit(
        action="platform_catalog_plan_upsert",
        actor_founder_id=_principal.id,
        resource_type="platform_catalog_plan",
        resource_id=slug,
    )
    return plan_to_internal_dto(row)


@router.get(
    "/provision-queue",
    response_model=list[PlatformProvisionQueueItem],
    summary="Signup intents for reconcile (Основатель)",
)
async def platform_provision_queue(
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformProvisionQueueItem]:
    rows = await list_platform_provision_queue(session, limit=100)
    return [_provision_queue_item(r) for r in rows]


@router.post(
    "/signup-intents/{intent_id}/retry-provision",
    response_model=PlatformRetryProvisionResponse,
    summary="Force provisioning retry (Основатель)",
    responses={
        404: {"description": "Intent not found"},
        409: {"description": "Intent lifecycle or payment does not allow retry"},
    },
)
async def platform_retry_provision(
    intent_id: UUID,
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> PlatformRetryProvisionResponse:
    try:
        await admin_force_retry_platform_provision(session, intent_id)
        await session.commit()
    except LookupError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "intent_not_found", "message": "Signup intent not found"},
        ) from None
    except PlatformProvisionRetryNotAllowed as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": exc.code,
                "message": "Provisioning retry is not allowed for this intent",
            },
        ) from None
    except Exception:
        await session.rollback()
        raise
    log_platform_audit(
        action="platform_signup_intent_retry_provision",
        actor_founder_id=_principal.id,
        resource_type="platform_signup_intent",
        resource_id=str(intent_id),
    )
    return PlatformRetryProvisionResponse()


@router.post(
    "/signup-intents/{intent_id}/manual-close",
    response_model=PlatformRetryProvisionResponse,
    summary="Mark reconcile as manually closed (Основатель)",
    responses={
        404: {"description": "Intent not found"},
        409: {"description": "Intent lifecycle does not allow manual close"},
    },
)
async def platform_manual_close_reconcile(
    intent_id: UUID,
    body: PlatformManualCloseRequest,
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> PlatformRetryProvisionResponse:
    try:
        outcome = await admin_mark_platform_provision_closed(
            session,
            intent_id,
            note=body.note,
        )
        await session.commit()
        platform_provision_manual_close_total.labels(
            result="applied" if outcome == "applied" else "noop",
        ).inc()
    except LookupError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "intent_not_found", "message": "Signup intent not found"},
        ) from None
    except PlatformProvisionRetryNotAllowed as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": exc.code,
                "message": "Manual close is not allowed for this intent",
            },
        ) from None
    except Exception:
        await session.rollback()
        raise
    if outcome == "applied":
        log_platform_audit(
            action="platform_signup_intent_manual_close",
            actor_founder_id=_principal.id,
            resource_type="platform_signup_intent",
            resource_id=str(intent_id),
        )
    return PlatformRetryProvisionResponse()


@router.post(
    "/signup-intents/{intent_id}/owner-invite-token",
    response_model=PlatformOwnerInviteMintResponse,
    summary="Mint or rotate owner invite token (Основатель)",
    description=(
        "Returns a fresh one-time token for the provisioned owner admin until email automation exists. "
        "Invalidates any previous invite hash for this intent."
    ),
    responses={
        404: {"description": "Intent not found or owner not provisioned yet"},
    },
)
async def platform_mint_owner_invite_token(
    intent_id: UUID,
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> PlatformOwnerInviteMintResponse:
    try:
        raw, exp = await rotate_platform_owner_invite_token(session, intent_id)
        await session.commit()
    except LookupError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "intent_not_ready", "message": "Intent not found or owner not provisioned"},
        ) from None
    except Exception:
        await session.rollback()
        raise
    log_platform_audit(
        action="platform_owner_invite_token_mint",
        actor_founder_id=_principal.id,
        resource_type="platform_signup_intent",
        resource_id=str(intent_id),
    )
    exp_str = exp.isoformat() if exp else ""
    return PlatformOwnerInviteMintResponse(token=raw, expires_at=exp_str)
