"""Payments API router."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_request_context, get_session, get_session_payment_webhook
from src.core.metrics import payment_webhook_failures_total
from src.core.payment_webhook_governance import (
    PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER,
    verify_patient_payment_webhook_secret,
)
from src.core.config import settings
from src.core.request_ip import client_ip_for_public_rate_limit
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter
from src.application.dto.payment_dto import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentWebhookOkResponse,
)
from src.application.dto.booking_dto import BookingErrorResponse
from src.application.booking_error_observability import record_booking_error_event
from src.core.context import RequestContext
from src.application.services.payment_service import PaymentService
from src.application.webhook_provider_verify import PaymentWebhookProviderVerifyError
from src.application.errors import (
    payment_error_from_lookup_error,
    payment_error_from_value_error,
)
from src.domain.entities.booking import Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

PAYMENT_ERROR_OPENAPI = {
    400: {"model": BookingErrorResponse, "description": "Payment / booking business error"},
    404: {"model": BookingErrorResponse, "description": "Booking not found"},
}


@router.post("", response_model=CreatePaymentResponse, responses=PAYMENT_ERROR_OPENAPI)
async def create_payment(
    data: CreatePaymentRequest,
    return_url: str | None = None,
    session: AsyncSession = Depends(get_session),
    context: RequestContext = Depends(get_request_context),
):
    """Create payment in YooKassa for booking; returns payment_url for redirect."""
    service = PaymentService(session)
    try:
        result = await service.create_payment(
            booking_id=data.booking_id,
            return_url=return_url,
            gateway_id=data.gateway_id,
        )
    except LookupError as exc:
        error = payment_error_from_lookup_error(exc, context)
        row = await session.get(Booking, data.booking_id)
        if row is not None:
            await record_booking_error_event(
                clinic_id=row.clinic_id,
                code=error.code,
                source="api",
                trace_id=error.trace_id,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.model_dump(),
        ) from exc
    except ValueError as exc:
        error = payment_error_from_value_error(exc, context)
        row = await session.get(Booking, data.booking_id)
        if row is not None:
            await record_booking_error_event(
                clinic_id=row.clinic_id,
                code=error.code,
                source="api",
                trace_id=error.trace_id,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.model_dump(),
        ) from exc

    # Нормализуем ответ к CreatePaymentResponse, чтобы избежать неожиданных типов
    # (например, MagicMock в тестах, когда PaymentService замокан).
    if isinstance(result, CreatePaymentResponse):
        return result

    payment_url = getattr(result, "payment_url", "") or ""
    provider_payment_id = getattr(result, "provider_payment_id", "") or ""
    prepayment_required = getattr(result, "prepayment_required", True)

    return CreatePaymentResponse(
        payment_url=str(payment_url),
        provider_payment_id=str(provider_payment_id),
        prepayment_required=bool(prepayment_required),
        # В сценариях без скидок (и при моканном сервисе) дополнительные поля не заполняем.
        original_amount=None,
        discount_amount=None,
        final_amount=None,
    )


@router.post(
    "/webhook",
    response_model=PaymentWebhookOkResponse,
    summary="YooKassa webhook (contour A — tenant booking payments)",
    responses={
        400: {"description": "Malformed JSON body (`code`: `invalid_json`)"},
        403: {
            "description": (
                "Missing or invalid **X-Patient-Payment-Webhook-Secret** when "
                "`PATIENT_PAYMENT_WEBHOOK_SECRET` is configured (`code`: `webhook_forbidden`)"
            ),
        },
        429: {"description": "Per-IP rate limit (contour A; `code`: `rate_limited`)"},
        500: {"description": "Processing error after body parse (`code`: `webhook_processing_failed`)"},
        502: {
            "description": (
                "YooKassa ``get_payment`` failed for a **known** local payment row — no state change; "
                "PSP should retry (`code`: `provider_verify_failed`)"
            ),
        },
    },
)
async def payments_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session_payment_webhook),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PaymentWebhookOkResponse:
    """
    Webhook endpoint for YooKassa notifications (contour A — tenant booking payments).

    When `PATIENT_PAYMENT_WEBHOOK_SECRET` is set, the request must include header
    **X-Patient-Payment-Webhook-Secret** with the same value (constant-time compare).
    Contour B uses `/platform/billing/webhooks/...` and **PLATFORM_BILLING_WEBHOOK_SECRET** — never reuse the same secret (U-006).
    """
    trace_id = getattr(request.state, "trace_id", None)
    if (settings.patient_payment_webhook_secret or "").strip():
        hdr = request.headers.get(PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER)
        if not verify_patient_payment_webhook_secret(hdr):
            payment_webhook_failures_total.labels(reason="invalid_secret").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "webhook_forbidden",
                    "message": "Invalid or missing patient payment webhook secret",
                    "trace_id": trace_id,
                },
            )
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_patient_payment_webhook_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:patient_payment_webhook:ip:{client_ip}",
                limit=settings.rate_patient_payment_webhook_ip_limit,
                window=settings.rate_patient_payment_webhook_ip_window_seconds,
            )
        except RateLimitExceeded:
            payment_webhook_failures_total.labels(reason="rate_limited").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Too many payment webhook requests",
                    "trace_id": trace_id,
                },
            ) from None
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as e:
        payment_webhook_failures_total.labels(reason="invalid_json").inc()
        logger.warning("Webhook invalid JSON", extra={"error": str(e), "trace_id": trace_id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_json",
                "message": "Invalid JSON",
                "trace_id": trace_id,
            },
        ) from e

    service = PaymentService(session)
    try:
        await service.handle_webhook(payload)
    except PaymentWebhookProviderVerifyError:
        payment_webhook_failures_total.labels(reason="provider_unavailable").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "provider_verify_failed",
                "message": "Payment provider could not be reached to verify this notification; retry later",
                "trace_id": trace_id,
            },
        ) from None
    except Exception as e:
        payment_webhook_failures_total.labels(reason="processing_error").inc()
        logger.exception(
            "Webhook processing failed",
            extra={"payload_keys": list(payload.keys()), "trace_id": trace_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "webhook_processing_failed",
                "message": "Webhook processing failed",
                "trace_id": trace_id,
            },
        ) from e

    return PaymentWebhookOkResponse()
