"""Platform founder login: email + password + optional TOTP (1a-E2, 1a-E3, ADR-007)."""

from datetime import timedelta
from uuid import UUID

import jwt
import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import (
    get_current_platform_founder_user,
    get_session,
    require_platform_founder_login_ip_rate_limit,
)
from src.api.v1.routers.admin_auth import verify_password
from src.core.config import settings
from src.core.platform_audit import log_platform_audit
from src.core.security import (
    create_platform_founder_access_token,
    create_platform_founder_mfa_token,
    is_platform_founder_jwt_configured,
    parse_platform_founder_mfa_token,
)
from src.domain.entities.platform_founder_user import PlatformFounderUser
from src.infrastructure.crypto.platform_founder_totp_crypto import (
    decrypt_totp_secret,
    encrypt_totp_secret,
)
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

router = APIRouter(prefix="/platform/auth", tags=["platform-auth"])

MIN_PASSWORD_LENGTH = 8


class PlatformFounderLoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)
    totp_code: str | None = Field(None, min_length=6, max_length=8)


class PlatformFounderLoginResponse(BaseModel):
    access_token: str | None = None
    founder_id: str | None = None
    mfa_required: bool = False
    mfa_token: str | None = None


class PlatformFounderTotpConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class PlatformFounderTotpEnrollResponse(BaseModel):
    otpauth_uri: str
    issuer: str
    account_email: str


class PlatformFounderLoginMfaRequest(BaseModel):
    mfa_token: str = Field(..., min_length=10)
    totp_code: str = Field(..., min_length=6, max_length=8)


async def _apply_platform_founder_login_email_rate_limit(
    *,
    email_norm: str,
    rate_limiter: RateLimiter,
) -> None:
    if settings.rate_platform_founder_login_email_limit > 0:
        await rate_limiter.check_or_raise(
            key=f"rate:platform_founder_login:email:{email_norm}",
            limit=settings.rate_platform_founder_login_email_limit,
            window=settings.rate_platform_founder_login_email_window_seconds,
        )


@router.post(
    "/login",
    response_model=PlatformFounderLoginResponse,
    responses={
        401: {"description": "Неверный email/пароль или неверный TOTP при включённом 2FA"},
        429: {"description": "Слишком много попыток (Redis; IP и/или email)"},
        503: {
            "description": "В production при пустом PLATFORM_FOUNDER_JWT_SECRET — вход отключён (нет fallback на JWT_SECRET_KEY)"
        },
    },
)
async def platform_founder_login(
    data: PlatformFounderLoginRequest,
    _login_ip_rl: None = Depends(require_platform_founder_login_ip_rate_limit),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlatformFounderLoginResponse:
    if not is_platform_founder_jwt_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "platform_founder_jwt_not_configured",
                "message": "PLATFORM_FOUNDER_JWT_SECRET is not set; platform operator login is disabled",
            },
        )

    email_norm = data.email.strip().lower()
    try:
        await _apply_platform_founder_login_email_rate_limit(
            email_norm=email_norm, rate_limiter=rate_limiter
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток. Попробуйте позже.",
        ) from None

    result = await session.execute(
        select(PlatformFounderUser).where(PlatformFounderUser.email == email_norm).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row or not row.is_active or not verify_password(data.password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if row.totp_enabled and row.totp_secret_ciphertext:
        secret = decrypt_totp_secret(row.totp_secret_ciphertext)
        totp = pyotp.TOTP(secret)
        if data.totp_code:
            if not totp.verify(data.totp_code.strip(), valid_window=1):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверный код двухфакторной аутентификации",
                )
        else:
            mfa = create_platform_founder_mfa_token(subject=row.id)
            log_platform_audit(
                action="platform_founder_login_mfa_challenge",
                actor_founder_id=row.id,
                resource_type="platform_founder_user",
                resource_id=str(row.id),
            )
            return PlatformFounderLoginResponse(
                mfa_required=True,
                mfa_token=mfa,
                access_token=None,
                founder_id=None,
            )

    token = create_platform_founder_access_token(
        subject=row.id,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_platform_founder),
    )
    log_platform_audit(
        action="platform_founder_login_success",
        actor_founder_id=row.id,
        resource_type="platform_founder_user",
        resource_id=str(row.id),
        extra={"totp_used": bool(row.totp_enabled)},
    )
    return PlatformFounderLoginResponse(
        access_token=token,
        founder_id=str(row.id),
        mfa_required=False,
        mfa_token=None,
    )


@router.post(
    "/login/mfa",
    response_model=PlatformFounderLoginResponse,
    responses={
        401: {"description": "Недействительный MFA-токен, пользователь, или неверный TOTP"},
        429: {"description": "Слишком много попыток (Redis; per-IP)"},
        503: {"description": "Production без PLATFORM_FOUNDER_JWT_SECRET — вход отключён"},
    },
)
async def platform_founder_login_mfa(
    data: PlatformFounderLoginMfaRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlatformFounderLoginResponse:
    if not is_platform_founder_jwt_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "platform_founder_jwt_not_configured",
                "message": "PLATFORM_FOUNDER_JWT_SECRET is not set; platform operator login is disabled",
            },
        )

    client_ip = request.client.host if request.client else "unknown"
    if settings.rate_platform_founder_mfa_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:platform_founder_mfa:ip:{client_ip}",
                limit=settings.rate_platform_founder_mfa_ip_limit,
                window=settings.rate_platform_founder_mfa_ip_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток. Попробуйте позже.",
            ) from None

    try:
        payload = parse_platform_founder_mfa_token(data.mfa_token.strip())
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный MFA-токен",
        ) from None

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный MFA-токен")

    try:
        uid = UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный MFA-токен",
        ) from exc

    result = await session.execute(
        select(PlatformFounderUser).where(PlatformFounderUser.id == uid).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row or not row.is_active or not row.totp_enabled or not row.totp_secret_ciphertext:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный MFA-токен")

    secret = decrypt_totp_secret(row.totp_secret_ciphertext)
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.totp_code.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный код двухфакторной аутентификации",
        )

    token = create_platform_founder_access_token(
        subject=row.id,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_platform_founder),
    )
    log_platform_audit(
        action="platform_founder_login_mfa_success",
        actor_founder_id=row.id,
        resource_type="platform_founder_user",
        resource_id=str(row.id),
    )
    return PlatformFounderLoginResponse(
        access_token=token,
        founder_id=str(row.id),
        mfa_required=False,
        mfa_token=None,
    )


@router.post("/totp/enroll", response_model=PlatformFounderTotpEnrollResponse)
async def platform_founder_totp_enroll(
    session: AsyncSession = Depends(get_session),
    principal: PlatformFounderUser = Depends(get_current_platform_founder_user),
) -> PlatformFounderTotpEnrollResponse:
    if principal.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "platform_founder_totp_already_enabled", "message": "TOTP уже включён"},
        )

    secret = pyotp.random_base32()
    principal.totp_secret_ciphertext = encrypt_totp_secret(secret)
    principal.totp_enabled = False
    await session.flush()

    issuer = (settings.app_name or "dental-booking").replace(":", " ")
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=principal.email, issuer_name=issuer)
    log_platform_audit(
        action="platform_founder_totp_enroll",
        actor_founder_id=principal.id,
        resource_type="platform_founder_user",
        resource_id=str(principal.id),
    )
    return PlatformFounderTotpEnrollResponse(
        otpauth_uri=uri,
        issuer=issuer,
        account_email=principal.email,
    )


@router.post("/totp/confirm", response_model=PlatformFounderLoginResponse)
async def platform_founder_totp_confirm(
    data: PlatformFounderTotpConfirmRequest,
    session: AsyncSession = Depends(get_session),
    principal: PlatformFounderUser = Depends(get_current_platform_founder_user),
) -> PlatformFounderLoginResponse:
    if principal.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "platform_founder_totp_already_enabled", "message": "TOTP уже включён"},
        )
    if not principal.totp_secret_ciphertext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "platform_founder_totp_not_enrolled", "message": "Сначала вызовите enroll"},
        )

    secret = decrypt_totp_secret(principal.totp_secret_ciphertext)
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "platform_founder_totp_invalid_code", "message": "Неверный код"},
        )

    principal.totp_enabled = True
    await session.flush()

    token = create_platform_founder_access_token(
        subject=principal.id,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_platform_founder),
    )
    log_platform_audit(
        action="platform_founder_totp_confirm",
        actor_founder_id=principal.id,
        resource_type="platform_founder_user",
        resource_id=str(principal.id),
    )
    return PlatformFounderLoginResponse(
        access_token=token,
        founder_id=str(principal.id),
        mfa_required=False,
        mfa_token=None,
    )
