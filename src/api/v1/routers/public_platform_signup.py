"""Public SaaS platform signup checkout (1b-E1 / 1b-F5) — intent + YooKassa payment URL."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.platform_billing_dto import (
    PlatformBillingWebhookErrorDetail,
    PlatformSignupCheckoutRequest,
    PlatformSignupCheckoutResponse,
)
from src.application.services.platform_billing_service import create_public_platform_signup_checkout
from src.application.services.turnstile_service import verify_turnstile
from src.core.config import settings
from src.core.metrics import auth_captcha_required_total, auth_captcha_verified_total
from src.core.request_ip import client_ip_for_public_rate_limit
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

router = APIRouter(prefix="/public/platform/signup", tags=["public-platform-signup"])

PLATFORM_SIGNUP_CHECKOUT_OPENAPI = {
    400: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Validation / unknown plan / invalid billing_period (stable `code` in body)",
    },
    403: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Turnstile required or verification failed when `TURNSTILE_ENABLED`",
    },
    429: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Redis rate limit (per client IP or normalized email)",
    },
    502: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "YooKassa create_payment failed",
    },
    503: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "YooKassa not configured or return URL missing",
    },
}


@router.post(
    "/checkout",
    response_model=PlatformSignupCheckoutResponse,
    responses=PLATFORM_SIGNUP_CHECKOUT_OPENAPI,
    summary="Start SaaS subscription checkout",
    description=(
        "Creates `platform_signup_intent` with catalog-backed `tariff_snapshot` and a pending "
        "YooKassa payment. Requires provider credentials (`YOOKASSA_*`). "
        "When Cloudflare Turnstile is enabled, `turnstile_token` is required on every request (PRC-C1)."
    ),
)
async def public_platform_signup_checkout(
    body: PlatformSignupCheckoutRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlatformSignupCheckoutResponse:
    trace_id = getattr(request.state, "trace_id", None)
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_public_platform_checkout_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:public_platform_checkout:ip:{client_ip}",
                limit=settings.rate_public_platform_checkout_ip_limit,
                window=settings.rate_public_platform_checkout_ip_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Слишком много запросов с этого адреса. Попробуйте позже.",
                    "trace_id": trace_id,
                },
            ) from None

    email_norm = (body.email or "").strip().lower()
    if settings.rate_public_platform_checkout_email_limit > 0 and email_norm and "@" in email_norm:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:public_platform_checkout:email:{email_norm}",
                limit=settings.rate_public_platform_checkout_email_limit,
                window=settings.rate_public_platform_checkout_email_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Слишком много попыток оформления для этого email. Попробуйте позже.",
                    "trace_id": trace_id,
                },
            ) from None

    if settings.turnstile_enabled:
        token = (body.turnstile_token or "").strip()
        if not token:
            auth_captcha_required_total.labels(reason="public_platform_checkout_required").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_required",
                    "message": "Требуется подтверждение Turnstile.",
                    "site_key": settings.turnstile_site_key,
                    "trace_id": trace_id,
                },
            )
        vr = await verify_turnstile(token, remote_ip=client_ip)
        auth_captcha_verified_total.labels(status="ok" if vr.ok else "denied").inc()
        if not vr.ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_required",
                    "message": "Требуется подтверждение Turnstile.",
                    "site_key": settings.turnstile_site_key,
                    "trace_id": trace_id,
                },
            ) from None

    ret = (body.return_url or "").strip() if body.return_url else ""
    if not ret:
        ret = (settings.platform_saas_checkout_return_url or settings.yookassa_return_url or "").strip()
    if not ret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "platform_checkout_return_url_missing",
                "message": "Configure platform_saas_checkout_return_url or yookassa_return_url",
                "trace_id": trace_id,
            },
        )

    try:
        intent_id, pay_url, amount = await create_public_platform_signup_checkout(
            session,
            email=str(body.email),
            plan_slug=body.plan_slug,
            billing_period=body.billing_period,
            return_url=ret,
            extra_entitlement_keys=list(body.extra_entitlement_keys or []),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_email":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_email", "message": "Invalid email", "trace_id": trace_id},
            ) from None
        if code in ("invalid_plan_slug", "unknown_plan_slug"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "unknown_plan_slug",
                    "message": "Unknown or inactive plan",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "invalid_billing_period":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_billing_period",
                    "message": "billing_period must be monthly or annual",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "plan_price_missing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "plan_price_missing",
                    "message": "Plan has no price for selected period",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "extra_entitlement_overlaps_plan":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "extra_entitlement_overlaps_plan",
                    "message": "Module is already included in the selected plan",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "extra_entitlement_unknown":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "extra_entitlement_unknown",
                    "message": "Unknown or inactive add-on module",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "extra_entitlement_no_price":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "extra_entitlement_no_price",
                    "message": "Add-on has no list price in catalog",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "yookassa_not_configured":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "yookassa_not_configured",
                    "message": "Payment provider is not configured",
                    "trace_id": trace_id,
                },
            ) from None
        if code == "yookassa_create_failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "yookassa_create_failed",
                    "message": "Could not create payment with provider",
                    "trace_id": trace_id,
                },
            ) from None
        raise

    return PlatformSignupCheckoutResponse(
        signup_intent_id=str(intent_id),
        payment_url=pay_url,
        amount_rub=format(Decimal(amount), "f") if amount is not None else "0",
        currency="USD",
        charge_currency="RUB",
    )
