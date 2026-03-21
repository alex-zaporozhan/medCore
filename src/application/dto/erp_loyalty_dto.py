"""DTOs for ERP loyalty obligations and write-offs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ErpLoyaltyObligationSnapshot(BaseModel):
    """Minimal snapshot of ERP loyalty obligation for reporting/ERP node."""

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    customer_subscription_id: UUID
    initial_amount: Decimal
    remaining_amount: Decimal
    status: str


class ErpLoyaltyWriteOffSummary(BaseModel):
    """Aggregated info about write-off movements for a visit."""

    booking_id: UUID
    clinic_id: UUID
    total_write_off_amount: Decimal
    obligation_ids: list[UUID]
    remaining_amounts: dict[UUID, Decimal]
    warnings: list[str] = []


class CreateObligationFromSaleInput(BaseModel):
    """Input payload to create ERP loyalty obligation from subscription sale."""

    clinic_id: UUID
    patient_id: UUID
    customer_subscription_id: UUID
    package_price: Decimal
    kind: str
    total_visits: int | None = None
    total_amount: Decimal | None = None
    created_at: datetime


class RegisterWriteOffForVisitInput(BaseModel):
    """Input payload to register write-off on visit for loyalty subscription."""

    clinic_id: UUID
    booking_id: UUID
    customer_subscription_id: UUID
    subscription_usage_id: UUID
    used_visits: int | None = None
    used_amount: Decimal | None = None
    happened_at: datetime
    beneficiary_patient_id: UUID | None = None
    family_link_id: UUID | None = None

