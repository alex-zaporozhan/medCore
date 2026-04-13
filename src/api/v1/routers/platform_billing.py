"""Platform SaaS billing API (contour B) — separate from patient payments."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.platform_billing_dto import (
    PlatformBillingWebhookErrorDetail,
    PlatformBillingWebhookOkResponse,
)
from src.application.services.platform_billing_service import (
    WEBHOOK_SECRET_HEADER,
    handle_platform_billing_webhook_two_phase,
    verify_platform_billing_webhook_secret,
)
from src.application.webhook_provider_verify import PlatformBillingWebhookProviderVerifyError
from src.core.config import settings
from src.core.metrics import platform_billing_webhook_total
from src.core.request_ip import client_ip_for_public_rate_limit
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform/billing", tags=["platform-billing"])

PLATFORM_BILLING_WEBHOOK_OPENAPI = {
    200: {
        "model": PlatformBillingWebhookOkResponse,
        "description": "Notification accepted (idempotent ok paths return 200 as well)",
    },
    400: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Malformed JSON body",
    },
    403: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Missing or invalid X-Platform-Billing-Webhook-Secret",
    },
    404: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Unknown provider slug in path",
    },
    429: {"description": "Per-IP rate limit"},
    500: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "Processing error after secret verification",
    },
    502: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": (
            "YooKassa ``get_payment`` failed for a **known** platform subscription payment — "
            "no commit of derived state; PSP should retry (`code`: `provider_verify_failed`)"
        ),
    },
    503: {
        "model": PlatformBillingWebhookErrorDetail,
        "description": "PLATFORM_BILLING_WEBHOOK_SECRET not configured",
    },
}


@router.post(
    "/webhooks/{provider}",
    response_model=PlatformBillingWebhookOkResponse,
    responses=PLATFORM_BILLING_WEBHOOK_OPENAPI,
    summary="Platform subscription webhook (contour B)",
    description=(
        "YooKassa (and future providers) notifications for **SaaS subscription** payments. "
        f"Requires header **{WEBHOOK_SECRET_HEADER}** matching `PLATFORM_BILLING_WEBHOOK_SECRET`. "
        "**Not** the patient booking payment webhook.\n\n"
        "**YooKassa matrix (notification `event` → behavior):** handler always re-fetches payment via "
        "`GET /v3/payments/{id}`; webhook body supplies `object.id` only.\n"
        "- `payment.succeeded` → update row, tariff gate, enqueue provision (outbox) when applicable.\n"
        "- `payment.waiting_for_capture` / `payment.canceled` → payment row status only.\n"
        "- `refund.succeeded` (legacy examples may show `payment.refunded`) → if API `status=refunded`, "
        "ADR-012 billing revocation.\n"
        "- Unknown `object.id` → 200 + metric `unknown_payment` (provider retry safe).\n"
        "- Known `object.id` but YooKassa API error on re-fetch → **502** + `provider_verify_failed` "
        "(no silent 2xx; P0-3).\n\n"
        "**Prometheus `platform_billing_webhook_total{result}`** (low cardinality): "
        "success, invalid_secret, rate_limited, processing_error, unknown_payment, "
        "provider_unavailable (YooKassa re-fetch failed for known payment), "
        "refund_reconciled, skipped_billing_revoked, idempotent_ok, … — see handler."
    ),
)
async def platform_billing_webhook(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    payload: Annotated[
        dict[str, Any],
        Body(
            openapi_examples={
                "yookassa_payment_succeeded": {
                    "summary": "payment.succeeded",
                    "description": "Subset of YooKassa notification; `object.id` is provider payment id.",
                    "value": {
                        "type": "notification",
                        "event": "payment.succeeded",
                        "object": {"id": "2c1b5f00-000f-5000-9000-1b2c3d4e5f00"},
                    },
                },
                "yookassa_payment_canceled": {
                    "summary": "payment.canceled",
                    "description": "Payment canceled by user or provider; updates `platform_subscription_payments.status`.",
                    "value": {
                        "type": "notification",
                        "event": "payment.canceled",
                        "object": {"id": "2c1b5f00-000f-5000-9000-1b2c3d4e5f00"},
                    },
                },
                "yookassa_refund_succeeded": {
                    "summary": "refund.succeeded",
                    "description": "Refund reconciled when API returns `status=refunded` (ADR-012).",
                    "value": {
                        "type": "notification",
                        "event": "refund.succeeded",
                        "object": {"id": "2c1b5f00-000f-5000-9000-1b2c3d4e5f00"},
                    },
                },
                "yookassa_payment_refunded_legacy_event": {
                    "summary": "payment.refunded (legacy event name)",
                    "description": "Same handling — `object.id` is resolved via YooKassa GET payment.",
                    "value": {
                        "type": "notification",
                        "event": "payment.refunded",
                        "object": {"id": "2c1b5f00-000f-5000-9000-1b2c3d4e5f00"},
                    },
                },
                "yookassa_payment_waiting_for_capture": {
                    "summary": "payment.waiting_for_capture",
                    "description": (
                        "Authorized, capture pending; updates `platform_subscription_payments.status` only "
                        "(no provisioning until `succeeded`)."
                    ),
                    "value": {
                        "type": "notification",
                        "event": "payment.waiting_for_capture",
                        "object": {"id": "2c1b5f00-000f-5000-9000-1b2c3d4e5f00"},
                    },
                },
            },
        ),
    ] = ...,
):
    trace_id = getattr(request.state, "trace_id", None)

    if not (settings.platform_billing_webhook_secret or "").strip():
        platform_billing_webhook_total.labels(result="not_configured").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "platform_webhook_not_configured",
                "message": "Platform billing webhook secret is not configured",
                "trace_id": trace_id,
            },
        )

    header_secret = request.headers.get(WEBHOOK_SECRET_HEADER)
    if not verify_platform_billing_webhook_secret(header_secret):
        platform_billing_webhook_total.labels(result="invalid_secret").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "platform_webhook_invalid_signature",
                "message": "Invalid or missing webhook secret",
                "trace_id": trace_id,
            },
        )

    if provider != "yookassa":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "unknown_provider", "message": provider, "trace_id": trace_id},
        )

    if not isinstance(payload, dict):
        platform_billing_webhook_total.labels(result="invalid_json").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_json",
                "message": "Invalid JSON",
                "trace_id": trace_id,
            },
        )

    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_platform_billing_webhook_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:platform_billing_webhook:ip:{client_ip}",
                limit=settings.rate_platform_billing_webhook_ip_limit,
                window=settings.rate_platform_billing_webhook_ip_window_seconds,
            )
        except RateLimitExceeded:
            platform_billing_webhook_total.labels(result="rate_limited").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limited", "message": "Too many webhook requests", "trace_id": trace_id},
            ) from None

    try:
        await handle_platform_billing_webhook_two_phase(session, payload)
    except PlatformBillingWebhookProviderVerifyError:
        await session.rollback()
        platform_billing_webhook_total.labels(result="provider_unavailable").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "provider_verify_failed",
                "message": "Payment provider could not be reached to verify this notification; retry later",
                "trace_id": trace_id,
            },
        ) from None
    except Exception:
        await session.rollback()
        platform_billing_webhook_total.labels(result="processing_error").inc()
        logger.exception(
            "Platform billing webhook processing failed",
            extra={"trace_id": trace_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "webhook_processing_failed",
                "message": "Webhook processing failed",
                "trace_id": trace_id,
            },
        ) from None

    return PlatformBillingWebhookOkResponse()
