"""DTOs for ERP payroll (policies and salary transactions)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PayrollPolicyRead(BaseModel):
    id: UUID
    clinic_id: UUID
    doctor_id: UUID | None
    role: str | None
    fixed_per_shift: Decimal
    percent_from_services: Decimal
    percent_from_products: Decimal
    created_at: datetime
    updated_at: datetime


class PayrollPolicyCreate(BaseModel):
    doctor_id: UUID | None = None
    role: str | None = None
    fixed_per_shift: Decimal = Decimal("0.00")
    percent_from_services: Decimal = Decimal("0.0000")
    percent_from_products: Decimal = Decimal("0.0000")


class PayrollPolicyUpdate(BaseModel):
    doctor_id: UUID | None = None
    role: str | None = None
    fixed_per_shift: Decimal | None = None
    percent_from_services: Decimal | None = None
    percent_from_products: Decimal | None = None


class SalaryTransactionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    doctor_id: UUID
    booking_id: UUID | None
    amount: Decimal
    type: str
    period_start: date | None
    period_end: date | None
    description: str | None
    created_at: datetime


