"""DTOs for ERP finance (cashboxes and financial transactions)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CashboxRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    type: str
    currency: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CashboxCreate(BaseModel):
    name: str
    type: str
    currency: str = "RUB"
    is_default: bool = False
    is_active: bool = True


class CashboxUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    currency: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class FinancialTransactionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    cashbox_id: UUID
    type: str
    amount: Decimal
    currency: str
    happened_at: datetime
    description: str | None
    booking_id: UUID | None
    payment_id: UUID | None
    source: str
    created_at: datetime
    updated_at: datetime


