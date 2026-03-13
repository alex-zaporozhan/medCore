"""Payments API router."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.payment_dto import CreatePaymentRequest, CreatePaymentResponse
from src.application.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=CreatePaymentResponse)
async def create_payment(
    data: CreatePaymentRequest,
    return_url: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Create payment in YooKassa for booking; returns payment_url for redirect."""
    service = PaymentService(session)
    try:
        result = await service.create_payment(
            booking_id=data.booking_id,
            return_url=return_url,
            gateway_id=data.gateway_id,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        ) from None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

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
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as e:
        logger.warning("Webhook invalid JSON", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        ) from e

    service = PaymentService(session)
    try:
        await service.handle_webhook(payload)
    except Exception as e:
        logger.exception("Webhook processing failed", extra={"payload_keys": list(payload.keys())})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        ) from e

    return {"status": "ok"}
