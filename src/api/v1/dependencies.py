"""API dependencies."""

import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    JwtClaimValidationError,
    is_platform_founder_jwt_configured,
    parse_access_token,
    parse_tenant_access_token_for_request_context,
)
from src.core.user_messages import (
    ADMIN_ORG_PLATFORM_BILLING_REVOKED,
    AUTH_REQUIRED,
    EMPTY_DB_NO_CLINIC,
    LOGIN_RATE_LIMITED,
    PLATFORM_FOUNDER_TOKEN_REQUIRED,
    TOKEN_INVALID_OR_EXPIRED,
)
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.platform_founder_user import PlatformFounderUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database import base as db_base
from src.infrastructure.database.base import get_db, get_db_reporting
from src.core.config import settings
from src.core.context import RequestContext
from src.core.metrics import (
    domain_outbox_post_commit_dispatch_failures_total,
    platform_founder_auth_total,
    platform_founder_jwt_reject_total,
    record_tenant_jwt_claim_reject,
)
from src.application.services.platform_billing_access import organization_has_platform_billing_revoked
from src.application.services.rbac_service import RbacServiceImpl
from src.infrastructure.database.rbac_repo_impl import RbacRepositoryImpl
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter
from src.core.request_ip import client_ip_for_public_rate_limit

logger = logging.getLogger(__name__)


class AdminContext(RequestContext):
    """Typed alias for admin request context."""

    pass


@dataclass(frozen=True, slots=True)
class PlatformFounderPrincipal:
    """Authenticated platform operator (Основатель) from JWT — not a clinic AdminUser."""

    id: UUID


async def get_session() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db():
        yield session


async def require_platform_founder_login_ip_rate_limit(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """
    Per-IP Redis buckets for ``POST /platform/auth/login``.
    Per-email buckets run in the route after the body is parsed (same keys as before).
    """
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_platform_founder_login_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:platform_founder_login:ip:{client_ip}",
                limit=settings.rate_platform_founder_login_ip_limit,
                window=settings.rate_platform_founder_login_ip_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=LOGIN_RATE_LIMITED,
            )


async def _resolve_platform_founder_principal(
    *,
    request: Request,
    session: AsyncSession,
    rate_limiter: RateLimiter,
    authorization: str | None,
    enforce_totp_enrolled_if_required: bool,
) -> PlatformFounderPrincipal:
    """
    Shared: validate founder JWT + load active PlatformFounderUser.
    When ``enforce_totp_enrolled_if_required`` and ``platform_founder_totp_required``, reject if TOTP not enabled
    (bootstrap: use ``get_current_platform_founder_allow_bootstrap_totp`` for /platform/auth/totp/*).
    """
    if not is_platform_founder_jwt_configured():
        platform_founder_auth_total.labels(result="not_configured").inc()
        trace_id = getattr(request.state, "trace_id", None)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "platform_founder_jwt_not_configured",
                "message": "PLATFORM_FOUNDER_JWT_SECRET is not set; platform operator routes are disabled",
                "trace_id": trace_id,
            },
        )

    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:platform_founder_auth:ip:{client_ip}",
            limit=settings.rate_platform_founder_auth_ip_limit,
            window=settings.rate_platform_founder_auth_ip_window_seconds,
        )
    except RateLimitExceeded:
        platform_founder_auth_total.labels(result="rate_limited").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=LOGIN_RATE_LIMITED,
        )

    if not authorization or not authorization.startswith("Bearer "):
        platform_founder_auth_total.labels(result="missing_bearer").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_REQUIRED,
        )
    token = authorization[7:].strip()
    try:
        from src.core.security import parse_platform_founder_access_token

        payload = parse_platform_founder_access_token(token)
    except JwtClaimValidationError as e:
        reason = (
            "issuer"
            if e.code == "invalid_token_issuer"
            else "audience"
            if e.code == "invalid_token_audience"
            else "claims"
        )
        platform_founder_jwt_reject_total.labels(reason=reason).inc()
        platform_founder_auth_total.labels(result="invalid_token").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": "Invalid token (issuer/audience)",
            },
        )
    except jwt.exceptions.InvalidTokenError:
        platform_founder_auth_total.labels(result="invalid_token").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=TOKEN_INVALID_OR_EXPIRED,
        )
    if payload.get("type") != "platform_founder":
        platform_founder_auth_total.labels(result="wrong_token_type").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "platform_founder_token_required",
                "message": PLATFORM_FOUNDER_TOKEN_REQUIRED["message"],
            },
        )
    sub = payload.get("sub")
    if not sub:
        platform_founder_auth_total.labels(result="invalid_sub").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "platform_token_invalid", "message": "Invalid platform token"},
        )
    try:
        uid = UUID(str(sub))
    except ValueError:
        platform_founder_auth_total.labels(result="invalid_sub").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "platform_token_invalid", "message": "Invalid platform token"},
        )

    res = await session.execute(
        select(PlatformFounderUser).where(
            PlatformFounderUser.id == uid,
            PlatformFounderUser.is_active.is_(True),
        ).limit(1)
    )
    founder_row = res.scalar_one_or_none()
    if founder_row is None:
        platform_founder_auth_total.labels(result="unknown_or_inactive_user").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "platform_founder_inactive_or_unknown",
                "message": "Platform operator not found or disabled",
            },
        )

    if (
        enforce_totp_enrolled_if_required
        and settings.platform_founder_totp_required
        and not founder_row.totp_enabled
    ):
        platform_founder_auth_total.labels(result="totp_enrollment_required").inc()
        trace_id = getattr(request.state, "trace_id", None)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "platform_founder_totp_enrollment_required",
                "message": "TOTP enrollment required: POST /platform/auth/totp/enroll then confirm",
                "trace_id": trace_id,
            },
        )

    platform_founder_auth_total.labels(result="ok").inc()
    return PlatformFounderPrincipal(id=uid)


async def get_current_platform_founder_allow_bootstrap_totp(
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    authorization: str | None = Header(None),
) -> PlatformFounderPrincipal:
    """Founder JWT for TOTP enroll/confirm — skips prod TOTP-enrolled gate so bootstrap can complete."""
    return await _resolve_platform_founder_principal(
        request=request,
        session=session,
        rate_limiter=rate_limiter,
        authorization=authorization,
        enforce_totp_enrolled_if_required=False,
    )


async def get_current_platform_founder(
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    authorization: str | None = Header(None),
) -> PlatformFounderPrincipal:
    """
    Bearer JWT with `type=platform_founder`, signed with platform founder key (see settings.platform_founder_jwt_secret).
    Rate-limited per IP (Redis). Do not use for clinic admin or patient routes.
    When ``platform_founder_totp_required``, user must have completed TOTP enroll.
    """
    return await _resolve_platform_founder_principal(
        request=request,
        session=session,
        rate_limiter=rate_limiter,
        authorization=authorization,
        enforce_totp_enrolled_if_required=True,
    )


async def get_current_platform_founder_user(
    principal: PlatformFounderPrincipal = Depends(get_current_platform_founder_allow_bootstrap_totp),
    session: AsyncSession = Depends(get_session),
) -> PlatformFounderUser:
    """ORM row for mutating platform-founder profile (e.g. TOTP enroll)."""
    row = await session.get(PlatformFounderUser, principal.id)
    if row is None or not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "platform_founder_inactive_or_unknown",
                "message": "Platform operator not found or disabled",
            },
        )
    return row


async def get_session_booking_domain_outbox() -> AsyncGenerator[AsyncSession, None]:
    """
    DB session for booking mutations: commit then drain domain_outbox (ADR-009 / 2-E2).
    When ``domain_outbox_booking_events_enabled`` is false, matches standard ``get_session``.
    """
    if db_base.AsyncSessionLocal is None:
        async for session in get_db():
            yield session
        return

    from src.application.services.domain_outbox_service import dispatch_domain_outbox_batch

    async with db_base.AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            if settings.domain_outbox_booking_events_enabled:
                try:
                    await dispatch_domain_outbox_batch()
                except Exception:
                    domain_outbox_post_commit_dispatch_failures_total.labels(dependency="booking_routes").inc()
                    logger.exception(
                        "domain_outbox post-commit dispatch failed after booking session commit "
                        "(transaction already committed; Celery domain_outbox.dispatch_pending should drain)"
                    )
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_payment_webhook() -> AsyncGenerator[AsyncSession, None]:
    """
    DB session for POST /payments/webhook: commit then dispatch domain_outbox (ADR-009).
    When ``domain_outbox_payment_webhook_enabled`` is false, matches standard get_session behavior.
    """
    if db_base.AsyncSessionLocal is None:
        async for session in get_db():
            yield session
        return

    from src.application.services.domain_outbox_service import dispatch_domain_outbox_batch

    async with db_base.AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            if settings.domain_outbox_payment_webhook_enabled:
                try:
                    await dispatch_domain_outbox_batch()
                except Exception:
                    domain_outbox_post_commit_dispatch_failures_total.labels(dependency="payment_webhook").inc()
                    logger.exception(
                        "domain_outbox post-commit dispatch failed after payment webhook commit "
                        "(transaction already committed; Celery domain_outbox.dispatch_pending should drain)"
                    )
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_reporting_session() -> AsyncSession:
    """Reporting GETs: optional replica + statement_timeout (ADR-005)."""
    async for session in get_db_reporting():
        yield session


async def get_default_clinic(session: AsyncSession) -> Clinic:
    """Get the default (first) clinic for single-clinic instance. Raises 404 if none."""
    result = await session.execute(select(Clinic).limit(1))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EMPTY_DB_NO_CLINIC)
    return clinic


async def get_current_admin_optional(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> AdminUser | None:
    """
    Valid admin JWT → AdminUser; no/foreign token type → None.
    Malformed or expired Bearer → 401 (client must not silently fall back to public).
    """

    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    try:
        payload = parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    except JwtClaimValidationError as e:
        record_tenant_jwt_claim_reject(code=e.code)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": "Invalid token (issuer/audience)"},
        )
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=TOKEN_INVALID_OR_EXPIRED,
        )
    if payload.get("type") != "admin":
        return None
    admin_sub = payload.get("sub")
    if not admin_sub:
        return None
    result = await session.execute(
        select(AdminUser).where(
            AdminUser.id == UUID(admin_sub),
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        ).limit(1)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        return None
    if admin.organization_id is not None and await organization_has_platform_billing_revoked(
        session, admin.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ORG_PLATFORM_BILLING_REVOKED,
        )
    return admin


async def get_default_clinic_id(session: AsyncSession = Depends(get_session)) -> UUID:
    """Get default clinic UUID for create operations. Depends on get_session so FastAPI injects it."""
    clinic = await get_default_clinic(session)
    return clinic.id


async def get_current_patient(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Patient:
    """Extract current patient from Bearer token and load entity."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_REQUIRED,
        )
    token = authorization[7:].strip()
    try:
        payload = parse_access_token(token, expected_audience=settings.jwt_audience_patient)
    except JwtClaimValidationError as e:
        record_tenant_jwt_claim_reject(code=e.code)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": "Invalid token (issuer/audience)"},
        )
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=TOKEN_INVALID_OR_EXPIRED,
        )
    if payload.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role")
    patient_sub = payload.get("sub")
    if not patient_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await session.execute(
        select(Patient).where(
            Patient.id == UUID(patient_sub),
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient not found")
    return patient


async def get_request_context(
    # Keep FastAPI's special injection for Request by keeping annotation as `Request`,
    # but allow direct test calls without passing `request`.
    request: Request = None,
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> RequestContext:
    """
    Build RequestContext from current request.

    For now supports:
    - admin JWT (via get_current_admin)
    - patient JWT (via get_current_patient)
    - unauthenticated/system calls (no token).
    """
    # Try admin first
    admin: AdminUser | None = None
    patient: Patient | None = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            payload = parse_tenant_access_token_for_request_context(token)
        except JwtClaimValidationError as e:
            record_tenant_jwt_claim_reject(code=e.code)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.code, "message": "Invalid token (issuer/audience)"},
            )
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=TOKEN_INVALID_OR_EXPIRED,
            )

        token_type = payload.get("type") or payload.get("role")

        if token_type == "admin":
            # Use existing dependency logic to resolve AdminUser (lazy import to avoid circular deps)
            from src.api.v1.routers.admin_auth import get_current_admin

            admin = await get_current_admin(authorization=authorization, session=session)  # type: ignore[arg-type]
        elif token_type == "patient":
            patient = await get_current_patient(authorization=authorization, session=session)  # type: ignore[arg-type]
        else:
            # Unknown type – treat as unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token_type", "message": "Invalid token type"},
            )

    if admin:
        rbac_repo = RbacRepositoryImpl(session)
        rbac_service = RbacServiceImpl(rbac_repo)
        rbac_info = await rbac_service.get_rbac_info_for_user(
            user_id=admin.id,
            clinic_id=admin.clinic_id,
        )
        return RequestContext(
            clinic_id=admin.clinic_id,
            user_id=admin.id,
            user_type="admin",
            trace_id=getattr(getattr(request, "state", None), "trace_id", None),
            roles=set(rbac_info.roles),
            permissions=set(rbac_info.permissions),
        )

    if patient:
        return RequestContext(
            clinic_id=None,
            user_id=patient.id,
            user_type="patient",
            trace_id=getattr(getattr(request, "state", None), "trace_id", None),
            roles=set(),
            permissions=set(),
        )

    # Fallback: system/unauthenticated
    return RequestContext(
        clinic_id=None,
        user_id=None,
        user_type="system",
        trace_id=getattr(getattr(request, "state", None), "trace_id", None),
        roles=set(),
        permissions=set(),
    )


def require_permissions(*permission_codes: str):
    """
    FastAPI dependency factory for RBAC permission checks.

    Usage:
        @router.get("/... ", dependencies=[Depends(require_permissions("view_reports"))])
    """

    async def dependency(context: RequestContext = Depends(get_request_context)) -> AdminContext:
        if context.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        if permission_codes:
            if not any(code in context.permissions for code in permission_codes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden",
                )
        # Cast to AdminContext for downstream type hints
        admin_context = AdminContext(
            clinic_id=context.clinic_id,
            user_id=context.user_id,
            user_type=context.user_type,
            trace_id=context.trace_id,
            roles=context.roles,
            permissions=context.permissions,
        )
        return admin_context

    return dependency

