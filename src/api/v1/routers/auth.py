"""Auth API router for patient SMS-based auth."""

import logging
import secrets
from typing import Any

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_default_clinic_id, get_session
from src.application.dto.agreement_dto import AgreementSettingsRead
from src.application.dto.auth_dto import AuthTokenResponse, SendCodeRequest, VerifyCodeRequest
from src.application.services.auth_service import AuthService
from src.application.services.oauth_auth_service import OAuthAuthService
from src.core.config import settings
from src.core.user_messages import EMPTY_DB_NO_CLINIC
from src.domain.entities.agreement_settings import AgreementSettings
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.application.services.turnstile_service import verify_turnstile
from src.core.metrics import auth_captcha_required_total, auth_captcha_verified_total

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


OAUTH_STATE_TTL_SECONDS = 600


def _is_safe_redirect_path(value: str | None) -> bool:
    if not value:
        return False
    if value.startswith("//"):
        return False
    if "://" in value:
        return False
    return value.startswith("/")


@router.post(
    "/send-code",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def send_code(
    data: SendCodeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter=Depends(get_rate_limiter),
) -> Response:
    """Send SMS code to patient phone number."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        # Soft threshold: require captcha before we start hard-denying traffic.
        if settings.turnstile_enabled:
            try:
                await rate_limiter.check_or_raise(
                    key=f"rate:auth_send_code:captcha_soft:ip:{client_ip}",
                    limit=settings.rate_auth_send_code_captcha_soft_ip_limit,
                    window=settings.rate_auth_captcha_soft_window_seconds,
                )
            except RateLimitExceeded:
                auth_captcha_required_total.labels(reason="auth_send_code_soft_limit").inc()
                vr = await verify_turnstile(data.turnstile_token, remote_ip=client_ip)
                auth_captcha_verified_total.labels(status="ok" if vr.ok else "denied").inc()
                if not vr.ok:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "code": "CAPTCHA_REQUIRED",
                            "site_key": settings.turnstile_site_key,
                        },
                    ) from None
        await rate_limiter.check_or_raise(
            key=f"rate:auth_send_code:ip:{client_ip}",
            limit=settings.rate_auth_send_code_ip_limit,
            window=settings.rate_auth_send_code_ip_window_seconds,
        )
        normalized_phone = AuthService._normalize_phone(data.phone)
        await rate_limiter.check_or_raise(
            key=f"rate:auth_send_code:phone:{normalized_phone}",
            limit=settings.rate_auth_send_code_phone_limit,
            window=settings.rate_auth_send_code_phone_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток. Попробуйте позже.",
        )

    service = AuthService(session)
    try:
        await service.send_code(phone=data.phone)
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        logger.exception("Failed to send auth code")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/verify-code",
    response_model=AuthTokenResponse,
)
async def verify_code(
    data: VerifyCodeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter=Depends(get_rate_limiter),
) -> AuthTokenResponse:
    """Verify SMS code and return access token."""
    client_ip = request.client.host if request.client else "unknown"
    if settings.turnstile_enabled:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:auth_verify_code:captcha_soft:ip:{client_ip}",
                limit=settings.rate_auth_verify_code_captcha_soft_ip_limit,
                window=settings.rate_auth_captcha_soft_window_seconds,
            )
        except RateLimitExceeded:
            auth_captcha_required_total.labels(reason="auth_verify_code_soft_limit").inc()
            vr = await verify_turnstile(data.turnstile_token, remote_ip=client_ip)
            auth_captcha_verified_total.labels(status="ok" if vr.ok else "denied").inc()
            if not vr.ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "CAPTCHA_REQUIRED",
                        "site_key": settings.turnstile_site_key,
                    },
                ) from None
    service = AuthService(session)
    try:
        token, patient_id = await service.verify_code(
            phone=data.phone,
            code=data.code,
            consent_pd=data.consent_pd,
            consent_mailing=data.consent_mailing,
            full_name=data.full_name,
            birth_date=data.birth_date,
            session_id=data.session_id,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
            utm_content=data.utm_content,
            utm_term=data.utm_term,
            landing_page=data.landing_page,
            anchor=data.anchor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        logger.exception("Failed to verify auth code")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return AuthTokenResponse(access_token=token, token_type="bearer", patient_id=patient_id)


@router.get("/agreement", response_model=AgreementSettingsRead)
async def get_agreement_for_login(
    session: AsyncSession = Depends(get_session),
    clinic_id: UUID = Depends(get_default_clinic_id),
) -> AgreementSettingsRead:
    """Return agreement settings for the default clinic (for login/registration form)."""
    result = await session.execute(
        select(AgreementSettings).where(AgreementSettings.clinic_id == clinic_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return AgreementSettingsRead(
            clinic_id=clinic_id,
            pd_agreement_text=None,
            allow_registration_without_mailing_consent=True,
        )
    return AgreementSettingsRead(
        clinic_id=row.clinic_id,
        pd_agreement_text=row.pd_agreement_text,
        allow_registration_without_mailing_consent=row.allow_registration_without_mailing_consent,
    )


@router.get("/oauth/vk/start")
async def oauth_vk_start(redirect: str | None = None) -> Response:
    """Start VK OAuth flow by redirecting to VK authorize URL.

    This is a skeleton; @ARCH/@DEV should complete scopes and state handling.
    """
    if not settings.vk_client_id or not settings.vk_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VK OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    redirect_path = redirect if _is_safe_redirect_path(redirect) else "/app"

    redis = await get_redis()
    await redis.setex(
        f"auth:vk:state:{state}",
        OAUTH_STATE_TTL_SECONDS,
        '{"redirect": "' + redirect_path + '"}',
    )

    params = [
        f"client_id={settings.vk_client_id}",
        "response_type=code",
        f"redirect_uri={settings.vk_redirect_uri}",
        "scope=email",
        f"state={state}",
    ]
    url = "https://oauth.vk.com/authorize?" + "&".join(params)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/yandex/start")
async def oauth_yandex_start(redirect: str | None = None) -> Response:
    """Start Yandex OAuth flow by redirecting to Yandex authorize URL.

    This is a skeleton; @ARCH/@DEV should complete scopes and state handling.
    """
    if not settings.yandex_client_id or not settings.yandex_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Yandex OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    redirect_path = redirect if _is_safe_redirect_path(redirect) else "/app"

    redis = await get_redis()
    await redis.setex(
        f"auth:yandex:state:{state}",
        OAUTH_STATE_TTL_SECONDS,
        '{"redirect": "' + redirect_path + '"}',
    )

    params = [
        f"client_id={settings.yandex_client_id}",
        "response_type=code",
        f"redirect_uri={settings.yandex_redirect_uri}",
        "response_type=code",
        "scope=login:email login:info",
        f"state={state}",
    ]
    url = "https://oauth.yandex.ru/authorize?" + "&".join(params)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/vk/callback")
async def oauth_vk_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """VK OAuth callback skeleton.

    @ARCH: описать маппинг VK-профиля → Patient.
    @DEV: реализовать обмен code→token, загрузку профиля, поиск/создание пациента и выдачу JWT.
    """
    redis = await get_redis()

    redirect_path = "/app/login"
    state_key = None
    if state:
        state_key = f"auth:vk:state:{state}"
        raw = await redis.get(state_key)
        if raw:
            await redis.delete(state_key)
            try:
                if '"redirect": "' in raw:
                    redirect_path = raw.split('"redirect": "')[1].split('"', 1)[0]
            except Exception:  # noqa: BLE001
                logger.exception("Failed to parse VK state payload", extra={"raw": raw})

    if error:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or not state_key or not await redis.exists(state_key):
        return RedirectResponse(
            url="/app/login?oauth=vk&status=state_invalid",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=error",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://oauth.vk.com/access_token",
                params={
                    "client_id": settings.vk_client_id,
                    "client_secret": settings.vk_client_secret,
                    "redirect_uri": settings.vk_redirect_uri,
                    "code": code,
                },
            )
        if response.status_code != 200:
            logger.error(
                "VK access_token request failed",
                extra={"status_code": response.status_code, "text": response.text},
            )
            return RedirectResponse(
                url=f"{redirect_path}?oauth=vk&status=provider_error",
                status_code=status.HTTP_302_FOUND,
            )
        data: dict[str, Any] = response.json()
    except Exception:
        logger.exception("VK access_token request error")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=provider_error",
            status_code=status.HTTP_302_FOUND,
        )

    user_id = data.get("user_id")
    email = data.get("email")
    if not user_id:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=provider_error",
            status_code=status.HTTP_302_FOUND,
        )

    service = OAuthAuthService(session)
    try:
        vk_profile = {
            "user_id": str(user_id),
            "email": email or None,
        }
        token, patient_id = await service.authenticate_vk(vk_profile)
    except Exception:
        logger.exception("Failed to authenticate VK user")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=error",
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=f"{redirect_path}?oauth=vk&status=ok&token={token}&patient_id={patient_id}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/oauth/yandex/callback")
async def oauth_yandex_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Yandex OAuth callback skeleton.

    @ARCH: описать маппинг Яндекс-профиля → Patient.
    @DEV: реализовать обмен code→token, загрузку профиля, поиск/создания пациента и выдачу JWT.
    """
    redis = await get_redis()

    redirect_path = "/app/login"
    state_key = None
    if state:
        state_key = f"auth:yandex:state:{state}"
        raw = await redis.get(state_key)
        if raw:
            await redis.delete(state_key)
            try:
                if '"redirect": "' in raw:
                    redirect_path = raw.split('"redirect": "')[1].split('"', 1)[0]
            except Exception:  # noqa: BLE001
                logger.exception("Failed to parse Yandex state payload", extra={"raw": raw})

    if error:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or not state_key or not await redis.exists(state_key):
        return RedirectResponse(
            url="/app/login?oauth=yandex&status=state_invalid",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=error",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                "https://oauth.yandex.ru/token",
                data={
                    "client_id": settings.yandex_client_id,
                    "client_secret": settings.yandex_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
        if token_response.status_code != 200:
            logger.error(
                "Yandex token request failed",
                extra={"status_code": token_response.status_code, "text": token_response.text},
            )
            return RedirectResponse(
                url=f"{redirect_path}?oauth=yandex&status=provider_error",
                status_code=status.HTTP_302_FOUND,
            )
        token_data: dict[str, Any] = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(
                url=f"{redirect_path}?oauth=yandex&status=provider_error",
                status_code=status.HTTP_302_FOUND,
            )

        async with httpx.AsyncClient(timeout=10) as client:
            profile_response = await client.get(
                "https://login.yandex.ru/info",
                headers={"Authorization": f"OAuth {access_token}"},
            )
        if profile_response.status_code != 200:
            logger.error(
                "Yandex profile request failed",
                extra={"status_code": profile_response.status_code, "text": profile_response.text},
            )
            return RedirectResponse(
                url=f"{redirect_path}?oauth=yandex&status=provider_error",
                status_code=status.HTTP_302_FOUND,
            )
        profile: dict[str, Any] = profile_response.json()
    except Exception:
        logger.exception("Yandex OAuth request error")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=provider_error",
            status_code=status.HTTP_302_FOUND,
        )

    user_id = profile.get("id")
    email = profile.get("default_email") or (profile.get("emails") or [None])[0]
    login_value = profile.get("login")
    if not user_id:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=provider_error",
            status_code=status.HTTP_302_FOUND,
        )

    service = OAuthAuthService(session)
    try:
        yandex_profile = {
            "id": str(user_id),
            "email": email or None,
            "login": login_value or None,
        }
        token, patient_id = await service.authenticate_yandex(yandex_profile)
    except Exception:
        logger.exception("Failed to authenticate Yandex user")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=error",
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=f"{redirect_path}?oauth=yandex&status=ok&token={token}&patient_id={patient_id}",
        status_code=status.HTTP_302_FOUND,
    )

