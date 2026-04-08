"""Payment DTOs."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreatePaymentRequest(BaseModel):
    """Request to create payment (patient)."""

    booking_id: UUID
    gateway_id: str | None = None


class CreatePaymentResponse(BaseModel):
    """Response with payment URL and provider id. When prepayment_required is False, payment_url may be empty."""

    payment_url: str
    provider_payment_id: str = ""
    prepayment_required: bool = True
    original_amount: str | None = None
    discount_amount: str | None = None
    final_amount: str | None = None


class PaymentWebhookOkResponse(BaseModel):
    """Contour A: YooKassa booking payment webhook acknowledged."""

    status: Literal["ok"] = "ok"

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})


class PaymentRead(BaseModel):
    """Payment read DTO."""

    id: UUID
    clinic_id: UUID
    booking_id: UUID
    provider: str
    provider_payment_id: str
    amount: Decimal
    currency: str
    status: str

    model_config = ConfigDict(from_attributes=True)
