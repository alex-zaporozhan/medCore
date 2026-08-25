"""Admin auth: login with email + password (min 8 chars), JWT."""

import logging
from datetime import timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.services.organization_entitlement_access import session_entitlement_view
from src.application.services.platform_billing_access import organization_has_platform_billing_revoked
from src.core.config import settings
from src.core.metrics import record_tenant_jwt_claim_reject
from src.core.security import JwtClaimValidationError, create_access_token, parse_access_token
from src.core.user_messages import (
    ADMIN_ORG_PLATFORM_BILLING_REVOKED,
    AUTH_REQUIRED,
    CLINIC_CONTEXT_REQUIRED,
    INVALID_CREDENTIALS,
    LOGIN_RATE_LIMITED,
    TOKEN_INVALID_OR_EXPIRED,
)
from src.core.industry_profile import INDUSTRY_PROFILE_DENTAL
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.clinic import Clinic
from src.domain.entities.organization import Organization
from src.infrastructure.database import base as db_base
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

MIN_PASSWORD_LENGTH = 8


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)


class AdminLoginResponse(BaseModel):
    access_token: str
    admin_id: str
    clinic_id: str
    full_name: str | None


class AdminSessionResponse(BaseModel):
    """Текущая сессия: RBAC для UI (P1 лента, staff collab и т.д.)."""

    clinic_id: str
    permissions: list[str]
    roles: list[str]
    organization_id: str | None = None
    accessible_clinic_ids: list[str] = Field(default_factory=list)
    #: True when org has rows in organization_entitlements — UI скрывает опции вне списка.
    entitlement_enforced: bool = False
    entitlement_keys: list[str] = Field(default_factory=list)
    #: Профиль отрасли организации клиники (МП §14); legacy без org — dental по умолчанию.
    industry_profile: str = INDUSTRY_PROFILE_DENTAL


def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(plain, hashed)


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    data: AdminLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter=Depends(get_rate_limiter),
) -> AdminLoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    email_norm = data.email.strip().lower()
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:admin_login:ip:{client_ip}",
            limit=settings.rate_admin_login_ip_limit,
            window=settings.rate_admin_login_ip_window_seconds,
        )
        await rate_limiter.check_or_raise(
            key=f"rate:admin_login:email:{email_norm}",
            limit=settings.rate_admin_login_email_limit,
            window=settings.rate_admin_login_email_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=LOGIN_RATE_LIMITED,
        )

    result = await session.execute(
        select(AdminUser).where(
            AdminUser.email == email_norm,
            AdminUser.deleted_at.is_(None),
        ).limit(1)
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )
    if admin.employment_status != EMPLOYMENT_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )
    if admin.organization_id is not None and await organization_has_platform_billing_revoked(
        session, admin.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ORG_PLATFORM_BILLING_REVOKED,
        )
    # Admin access token: short-lived; explicit token revocation (version/blacklist) — отдельная задача харднинга.
    token = create_access_token(
        data={
            "sub": str(admin.id),
            "clinic_id": str(admin.clinic_id),
            "type": "admin",
        },
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_admin),
    )
    return AdminLoginResponse(
        access_token=token,
        admin_id=str(admin.id),
        clinic_id=str(admin.clinic_id),
        full_name=admin.full_name,
    )


def get_current_admin_dependency():
    """Dependency that extracts Bearer token and returns AdminUser."""
    from fastapi import Depends, Header

    async def _get_current_admin(
        authorization: str | None = Header(None),
        session: AsyncSession = Depends(get_session),
    ) -> AdminUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTH_REQUIRED,
            )
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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        result = await session.execute(
            select(AdminUser).where(
                AdminUser.id == UUID(admin_id),
                AdminUser.deleted_at.is_(None),
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            ).limit(1)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
        if admin.organization_id is not None and await organization_has_platform_billing_revoked(
            session, admin.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ADMIN_ORG_PLATFORM_BILLING_REVOKED,
            )
        return admin

    return _get_current_admin


get_current_admin = get_current_admin_dependency()


@router.get("/session", response_model=AdminSessionResponse)
async def admin_session(
    admin_ctx: AdminContext = Depends(require_permissions()),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSessionResponse:
    """Права и роли текущего администратора (без отдельной проверки permission — любой валидный admin JWT)."""
    cid = admin_ctx.clinic_id
    if cid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CLINIC_CONTEXT_REQUIRED,
        )
    clinic_row = await session.get(Clinic, cid)
    effective_org_id: UUID | None = current_admin.organization_id
    if effective_org_id is None and clinic_row and clinic_row.organization_id is not None:
        effective_org_id = clinic_row.organization_id

    accessible: list[str] = [str(cid)]
    org_id: str | None = None
    if effective_org_id and "owner" in set(admin_ctx.roles):
        org_id = str(effective_org_id)
        res = await session.execute(
            select(Clinic.id)
            .where(
                Clinic.organization_id == effective_org_id,
                Clinic.deleted_at.is_(None),
            )
            .order_by(Clinic.name.asc())
        )
        accessible = [str(r[0]) for r in res.all()]
    elif effective_org_id:
        org_id = str(effective_org_id)
    enforced, ent_keys = await session_entitlement_view(session, current_admin)
    industry_profile = INDUSTRY_PROFILE_DENTAL
    if clinic_row and clinic_row.organization_id is not None:
        org_row = await session.get(Organization, clinic_row.organization_id)
        if org_row is not None:
            industry_profile = org_row.industry_profile
    return AdminSessionResponse(
        clinic_id=str(cid),
        permissions=sorted(admin_ctx.permissions),
        roles=sorted(admin_ctx.roles),
        organization_id=org_id,
        accessible_clinic_ids=accessible,
        entitlement_enforced=enforced,
        entitlement_keys=ent_keys,
        industry_profile=industry_profile,
    )


def get_current_admin_sse_dependency():
    """Bearer or query `access_token` (for EventSource which cannot set headers)."""

    async def _get_current_admin_sse(
        access_token: str | None = Query(None, description="JWT for SSE clients"),
        authorization: str | None = Header(None),
    ) -> AdminUser:
        token = (access_token or "").strip() or None
        if not token and authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTH_REQUIRED,
            )
        try:
            payload = parse_access_token(token, expected_audience=settings.jwt_audience_admin)
        except JwtClaimValidationError as e:
            record_tenant_jwt_claim_reject(code=e.code)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.code, "message": "Invalid token (issuer/audience)"},
            ) from None
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=TOKEN_INVALID_OR_EXPIRED,
            ) from None
        if payload.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # Short-lived session: SSE streams must not hold Depends(get_session) open for the whole response.
        async with db_base.AsyncSessionLocal() as session:
            result = await session.execute(
                select(AdminUser).where(
                    AdminUser.id == UUID(admin_id),
                    AdminUser.deleted_at.is_(None),
                    AdminUser.employment_status == EMPLOYMENT_ACTIVE,
                ).limit(1)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
            if admin.organization_id is not None and await organization_has_platform_billing_revoked(
                session, admin.organization_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ADMIN_ORG_PLATFORM_BILLING_REVOKED,
                )
            return admin

    return _get_current_admin_sse


get_current_admin_sse = get_current_admin_sse_dependency()


def get_current_admin_optional_dependency():
    """Returns AdminUser if valid token present, else None (no 401)."""
    from fastapi import Depends, Header

    async def _get(
        authorization: str | None = Header(None),
        session: AsyncSession = Depends(get_session),
    ) -> AdminUser | None:
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
        admin_id = payload.get("sub")
        if not admin_id:
            return None
        result = await session.execute(
            select(AdminUser).where(
                AdminUser.id == UUID(admin_id),
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

    return _get


get_current_admin_optional = get_current_admin_optional_dependency()
