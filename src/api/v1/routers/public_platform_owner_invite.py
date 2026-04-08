"""Public owner invite accept (SaaS platform provisioning, Phase 1b)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.platform_billing_dto import (
    PlatformOwnerInviteAcceptRequest,
    PlatformOwnerInviteAcceptResponse,
)
from src.application.services.platform_billing_service import accept_platform_owner_invite
from src.core.config import settings
from src.core.request_ip import client_ip_for_public_rate_limit
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/platform", tags=["public-platform"])


@router.post(
    "/owner-invite/accept",
    response_model=PlatformOwnerInviteAcceptResponse,
    summary="Accept owner invite after platform subscription provisioning",
)
async def accept_owner_invite(
    body: PlatformOwnerInviteAcceptRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
):
    """
    Completes first-owner onboarding: sets password for the AdminUser created from webhook B.
    Token is one-time (hash stored on `platform_signup_intents`); delivered via secure product channel (email).
    """
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_platform_owner_invite_accept_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:platform_owner_invite_accept:ip:{client_ip}",
                limit=settings.rate_platform_owner_invite_accept_ip_limit,
                window=settings.rate_platform_owner_invite_accept_ip_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток. Попробуйте позже.",
            ) from None

    try:
        admin_id = await accept_platform_owner_invite(session, token=body.token, password=body.password)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        code = str(exc.args[0]) if exc.args else "invalid_or_expired_token"
        if code == "password_too_short":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": code, "message": "Пароль не короче 8 символов"},
            ) from exc
        # Do not distinguish unknown token vs expired (enumeration hardening).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_or_expired_token", "message": "Недействительный или просроченный токен"},
        ) from exc
    except Exception:
        await session.rollback()
        logger.exception("owner-invite accept failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "invite_accept_failed", "message": "Не удалось завершить приглашение"},
        ) from None

    return PlatformOwnerInviteAcceptResponse(status="ok", admin_id=str(admin_id))
