"""Auth API router for patient SMS-based auth."""

import json
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.agreement_dto import AgreementSettingsRead
from src.application.dto.auth_dto import AuthTokenResponse, SendCodeRequest, VerifyCodeRequest
from src.application.services.auth_service import AuthService
from src.application.services.oauth_auth_service import OAuthAuthService
from src.application.services.patient_entry_clinic import resolve_clinic_for_patient_entry
from src.core.config import settings
from src.core.patient_messages import AUTH_CLINIC_SLUG_REQUIRED, AUTH_UNKNOWN_CLINIC_SLUG
from src.core.user_messages import EMPTY_DB_NO_CLINIC
from src.domain.entities.agreement_settings import AgreementSettings
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter
from src.application.services.turnstile_service import verify_turnstile
from src.core.metrics import auth_captcha_required_total, auth_captcha_verified_total

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


OAUTH_STATE_TTL_SECONDS = 600


async def _guard_unknown_clinic_slug_probe_or_raise(
    rate_limiter: RateLimiter,
    client_ip: str,
) -> None:
    """Anti-enumeration: each 400 UNKNOWN_CLINIC_SLUG counts toward per-IP bucket; 429 when exceeded."""
    if settings.rate_auth_unknown_clinic_slug_ip_limit <= 0:
        return
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:auth:unknown_clinic_slug:ip:{client_ip}",
            limit=settings.rate_auth_unknown_clinic_slug_ip_limit,
            window=settings.rate_auth_unknown_clinic_slug_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов с неверной ссылкой клиники. Попробуйте позже.",
        ) from None


async def _oauth_unknown_slug_probe_redirect_or_none(
    rate_limiter: RateLimiter,
    client_ip: str,
    redirect_path: str,
    oauth_provider: str,
) -> Response | None:
    if settings.rate_auth_unknown_clinic_slug_ip_limit <= 0:
        return None
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:auth:unknown_clinic_slug:ip:{client_ip}",
            limit=settings.rate_auth_unknown_clinic_slug_ip_limit,
            window=settings.rate_auth_unknown_clinic_slug_ip_window_seconds,
        )
    except RateLimitExceeded:
        return RedirectResponse(
            url=f"{redirect_path}?oauth={oauth_provider}&status=rate_limited",
            status_code=status.HTTP_302_FOUND,
        )
    return None


def _is_safe_redirect_path(value: str | None) -> bool:
    if not value:
        return False
    if value.startswith("//"):
        return False
    if "://" in value:
        return False
    return value.startswith("/")


def _oauth_state_blob(*, redirect_path: str, clinic_slug: str | None) -> str:
    return json.dumps({"redirect": redirect_path, "clinic_slug": clinic_slug})


def _parse_oauth_state(raw: bytes | str | None) -> tuple[str, str | None]:
    """Returns (redirect_path, clinic_slug)."""
    if raw is None:
        return "/app/login", None
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            r = obj.get("redirect")
            if isinstance(r, str) and _is_safe_redirect_path(r):
                redir = r
            else:
                redir = "/app/login"
            c = obj.get("clinic_slug")
            if isinstance(c, str) and c.strip():
                return redir, c.strip()
            return redir, None
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    if '"redirect": "' in text:
        try:
            redirect_path = text.split('"redirect": "')[1].split('"', 1)[0]
            if _is_safe_redirect_path(redirect_path):
                return redirect_path, None
        except (IndexError, ValueError):
            pass
    return "/app/login", None


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
                            "code": "captcha_required",
                            "message": "Требуется подтверждение Turnstile.",
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
        await service.send_code(phone=data.phone, clinic_slug=data.clinic_slug)
    except ValueError as exc:
        if str(exc) == AUTH_CLINIC_SLUG_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CLINIC_SLUG_REQUIRED", "message": str(exc)},
            ) from exc
        if str(exc) == AUTH_UNKNOWN_CLINIC_SLUG:
            await _guard_unknown_clinic_slug_probe_or_raise(rate_limiter, client_ip)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "UNKNOWN_CLINIC_SLUG", "message": str(exc)},
            ) from exc
        raise
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
                        "code": "captcha_required",
                        "message": "Требуется подтверждение Turnstile.",
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
            clinic_slug=data.clinic_slug,
        )
    except ValueError as exc:
        if str(exc) == AUTH_CLINIC_SLUG_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CLINIC_SLUG_REQUIRED", "message": str(exc)},
            ) from exc
        if str(exc) == AUTH_UNKNOWN_CLINIC_SLUG:
            await _guard_unknown_clinic_slug_probe_or_raise(rate_limiter, client_ip)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "UNKNOWN_CLINIC_SLUG", "message": str(exc)},
            ) from exc
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
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    clinic_slug: str | None = Query(
        None,
        max_length=120,
        description="Публичный slug клиники; если не задан — первая клиника в БД (legacy).",
    ),
) -> AgreementSettingsRead:
    """Return agreement settings for patient login/registration (per clinic slug or default)."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        clinic = await resolve_clinic_for_patient_entry(session, clinic_slug)
    except ValueError as exc:
        if str(exc) == AUTH_CLINIC_SLUG_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "CLINIC_SLUG_REQUIRED", "message": str(exc)},
            ) from exc
        if str(exc) == AUTH_UNKNOWN_CLINIC_SLUG:
            await _guard_unknown_clinic_slug_probe_or_raise(rate_limiter, client_ip)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "UNKNOWN_CLINIC_SLUG", "message": str(exc)},
            ) from exc
        raise
    except RuntimeError as exc:
        if "No clinic" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPTY_DB_NO_CLINIC,
            ) from exc
        raise
    clinic_id = clinic.id
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
async def oauth_vk_start(
    redirect: str | None = None,
    clinic_slug: str | None = Query(None, max_length=120),
) -> Response:
    """Start VK OAuth flow by redirecting to VK authorize URL.

    Skeleton: extend scopes, state handling, and token exchange as needed.
    """
    if not settings.vk_client_id or not settings.vk_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VK OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    redirect_path = redirect if _is_safe_redirect_path(redirect) else "/app"
    slug = clinic_slug.strip() if clinic_slug and clinic_slug.strip() else None

    redis = await get_redis()
    await redis.setex(
        f"auth:vk:state:{state}",
        OAUTH_STATE_TTL_SECONDS,
        _oauth_state_blob(redirect_path=redirect_path, clinic_slug=slug),
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
async def oauth_yandex_start(
    redirect: str | None = None,
    clinic_slug: str | None = Query(None, max_length=120),
) -> Response:
    """Start Yandex OAuth flow by redirecting to Yandex authorize URL.

    Skeleton: extend scopes, state handling, and token exchange as needed.
    """
    if not settings.yandex_client_id or not settings.yandex_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Yandex OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    redirect_path = redirect if _is_safe_redirect_path(redirect) else "/app"
    slug = clinic_slug.strip() if clinic_slug and clinic_slug.strip() else None

    redis = await get_redis()
    await redis.setex(
        f"auth:yandex:state:{state}",
        OAUTH_STATE_TTL_SECONDS,
        _oauth_state_blob(redirect_path=redirect_path, clinic_slug=slug),
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
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Response:
    """VK OAuth callback (complete token exchange and patient mapping as needed)."""
    redis = await get_redis()

    redirect_path = "/app/login"
    oauth_clinic_slug: str | None = None
    state_key = f"auth:vk:state:{state}" if state else None
    raw = await redis.get(state_key) if state_key else None
    if state_key and raw is not None:
        await redis.delete(state_key)
        redirect_path, oauth_clinic_slug = _parse_oauth_state(raw)

    if error:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or raw is None:
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
        token, patient_id = await service.authenticate_vk(vk_profile, clinic_slug=oauth_clinic_slug)
    except ValueError as exc:
        client_ip = request.client.host if request.client else "unknown"
        if str(exc) == AUTH_CLINIC_SLUG_REQUIRED:
            return RedirectResponse(
                url=f"{redirect_path}?oauth=vk&status=error&code=CLINIC_SLUG_REQUIRED",
                status_code=status.HTTP_302_FOUND,
            )
        if str(exc) == AUTH_UNKNOWN_CLINIC_SLUG:
            rate_redirect = await _oauth_unknown_slug_probe_redirect_or_none(
                rate_limiter, client_ip, redirect_path, "vk"
            )
            if rate_redirect is not None:
                return rate_redirect
            return RedirectResponse(
                url=f"{redirect_path}?oauth=vk&status=error&code=UNKNOWN_CLINIC_SLUG",
                status_code=status.HTTP_302_FOUND,
            )
        logger.exception("Failed to authenticate VK user")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=vk&status=error",
            status_code=status.HTTP_302_FOUND,
        )
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
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Response:
    """Yandex OAuth callback (complete token exchange and patient mapping as needed)."""
    redis = await get_redis()

    redirect_path = "/app/login"
    oauth_clinic_slug: str | None = None
    state_key = f"auth:yandex:state:{state}" if state else None
    raw = await redis.get(state_key) if state_key else None
    if state_key and raw is not None:
        await redis.delete(state_key)
        redirect_path, oauth_clinic_slug = _parse_oauth_state(raw)

    if error:
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    if not state or raw is None:
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
        token, patient_id = await service.authenticate_yandex(yandex_profile, clinic_slug=oauth_clinic_slug)
    except ValueError as exc:
        client_ip = request.client.host if request.client else "unknown"
        if str(exc) == AUTH_CLINIC_SLUG_REQUIRED:
            return RedirectResponse(
                url=f"{redirect_path}?oauth=yandex&status=error&code=CLINIC_SLUG_REQUIRED",
                status_code=status.HTTP_302_FOUND,
            )
        if str(exc) == AUTH_UNKNOWN_CLINIC_SLUG:
            rate_redirect = await _oauth_unknown_slug_probe_redirect_or_none(
                rate_limiter, client_ip, redirect_path, "yandex"
            )
            if rate_redirect is not None:
                return rate_redirect
            return RedirectResponse(
                url=f"{redirect_path}?oauth=yandex&status=error&code=UNKNOWN_CLINIC_SLUG",
                status_code=status.HTTP_302_FOUND,
            )
        logger.exception("Failed to authenticate Yandex user")
        return RedirectResponse(
            url=f"{redirect_path}?oauth=yandex&status=error",
            status_code=status.HTTP_302_FOUND,
        )
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

