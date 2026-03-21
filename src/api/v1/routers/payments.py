"""Payments API router."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, get_request_context
from src.core.metrics import payment_webhook_failures_total
from src.application.dto.payment_dto import CreatePaymentRequest, CreatePaymentResponse
from src.application.dto.booking_dto import BookingErrorResponse
from src.application.booking_error_observability import record_booking_error_event
from src.core.context import RequestContext
from src.application.services.payment_service import PaymentService
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


@router.post("/webhook")
async def payments_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Webhook endpoint for YooKassa notifications. No auth in MVP; optionally
    verify signature/secret via request headers or body later.
    """
    trace_id = getattr(request.state, "trace_id", None)
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

    return {"status": "ok"}
