"""DTOs for ERP finance (cashboxes and financial transactions)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from src.application.dto.erp_loyalty_dto import ErpLoyaltyWriteOffSummary


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
    balance: Decimal | None = None  # current balance (income - expense); filled in list endpoint


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


class FinancialTransactionCreate(BaseModel):
    """Body for POST finance/transactions. income/expense: cashbox_id; transfer: from_cashbox_id + to_cashbox_id."""

    type: str  # income | expense | transfer
    amount: Decimal
    category: str = ""  # stored as description
    # For income/expense
    cashbox_id: UUID | None = None
    # For transfer
    from_cashbox_id: UUID | None = None
    to_cashbox_id: UUID | None = None


class ErpVisitServiceItem(BaseModel):
    """Aggregated service item for ERP visit node.

    Decoupled from ORM; used only as part of ErpVisitNodeRequest.
    """

    service_id: UUID
    quantity: Decimal = Decimal("1")
    price: Decimal
    total_amount: Decimal


class ErpVisitPaymentItem(BaseModel):
    """Payment breakdown item for ERP visit node."""

    source: str  # cash | acquiring | package | deposit | discount | other
    amount: Decimal
    external_payment_id: UUID | None = None


class ErpVisitPayrollInput(BaseModel):
    """Input for payroll calculation as part of visit completion."""

    doctor_id: UUID
    role: str | None = None
    services_amount: Decimal
    products_amount: Decimal = Decimal("0")
    period_start: datetime | None = None
    period_end: datetime | None = None


class ErpVisitInventoryItem(BaseModel):
    """Inventory consumption item for ERP visit node."""

    product_id: UUID
    warehouse_id: UUID | None = None
    quantity: Decimal
    unit: str | None = None


class ErpVisitNodeRequest(BaseModel):
    """Canonical request DTO for ERP visit node.

    This is the main entrypoint contract for ERP visit completion logic.
    It is intentionally free of ORM entities and operates on aggregated
    visit data prepared by BookingCompletionService.
    """

    booking_id: UUID
    clinic_id: UUID
    visit_date: datetime
    services: list[ErpVisitServiceItem]
    payments: list[ErpVisitPaymentItem]
    payroll_inputs: list[ErpVisitPayrollInput]
    inventory_items: list[ErpVisitInventoryItem]


class ErpVisitNodeResult(BaseModel):
    """Canonical result DTO from ERP visit node.

    Designed to be embedded into BookingCompletionResult.erp_summary and
    to power future ERP reports.
    """

    success: bool
    finance_ids: list[UUID] = []
    payroll_ids: list[UUID] = []
    inventory_ids: list[UUID] = []
    warnings: list[str] = []
    error_code: str | None = None
    error_message: str | None = None
    loyalty_summary: ErpLoyaltyWriteOffSummary | None = None


class ErpBookingCompletionRequest(BaseModel):
    """Facade-level request DTO for ERP booking completion node.

    Intentionally minimal and decoupled from ORM; details of how these fields
    are mapped to finance/payroll/inventory are owned by BookingErpService
    and related domain services.
    """

    booking_id: UUID
    clinic_id: UUID
    patient_id: UUID
    service_id: UUID
    total_amount: Decimal | None = None
    payment_id: UUID | None = None
    paid_by_subscription: bool = False
    completed_at: datetime | None = None
class ErpBookingCompletionResult(BaseModel):
    """Facade-level result DTO from ERP booking completion node.

    Designed to be embeddable into BookingCompletionResult.erp_summary.
    """

    success: bool
    booking_id: UUID
    error_code: str | None = None
    # High-level ERP error type for observability and tasks:
    # finance | payroll | inventory | validation | unexpected
    error_type: str | None = None
    error_message: str | None = None
    finance_transaction_ids: list[UUID] | None = None
    payroll_transaction_ids: list[UUID] | None = None
    inventory_movement_ids: list[UUID] | None = None
    loyalty_write_off_summary: ErpLoyaltyWriteOffSummary | None = None
