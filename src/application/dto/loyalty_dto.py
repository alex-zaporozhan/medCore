"""DTOs for loyalty (subscription packages, customer subscriptions, wallets)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# B6.4: API uses COUNT_BASED | BALANCE_BASED; DB may use visits | balance | mixed
KIND_COUNT_BASED = "COUNT_BASED"
KIND_BALANCE_BASED = "BALANCE_BASED"
KIND_VISITS_ALIAS = "visits"
KIND_BALANCE_ALIAS = "balance"


class SubscriptionPackageBase(BaseModel):
    code: str = Field(..., description="Internal package code")
    name: str
    description: str | None = None
    kind: Literal["COUNT_BASED", "BALANCE_BASED"] = Field(
        ...,
        description="COUNT_BASED requires total_visits; BALANCE_BASED requires total_amount",
    )
    services_included: list[UUID] = Field(default_factory=list)
    total_visits: int | None = None
    total_amount: Decimal | None = None
    price: Decimal
    validity_days: int | None = None
    is_active: bool = True


class SubscriptionPackageCreate(SubscriptionPackageBase):
    @model_validator(mode="after")
    def validate_kind_fields(self) -> "SubscriptionPackageCreate":
        if self.kind == "COUNT_BASED":
            if self.total_visits is None or self.total_visits <= 0:
                raise ValueError("total_visits is required and must be > 0 when kind is COUNT_BASED")
        elif self.kind == "BALANCE_BASED":
            if self.total_amount is None or self.total_amount <= 0:
                raise ValueError("total_amount is required and must be > 0 when kind is BALANCE_BASED")
        return self


class SubscriptionPackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    kind: Literal["COUNT_BASED", "BALANCE_BASED"] | None = None
    services_included: list[UUID] | None = None
    total_visits: int | None = None
    total_amount: Decimal | None = None
    price: Decimal | None = None
    validity_days: int | None = None
    is_active: bool | None = None


class SubscriptionPackageRead(SubscriptionPackageBase):
    id: UUID
    clinic_id: UUID
    # Override: DB stores "visits"/"balance"; API may expose COUNT_BASED/BALANCE_BASED
    kind: str = Field(description="Package kind (COUNT_BASED, BALANCE_BASED, or DB values visits/balance)")

    class Config:
        from_attributes = True


class CustomerSubscriptionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    subscription_package_id: UUID
    status: str
    purchased_at: datetime
    activated_at: datetime | None
    expires_at: datetime | None
    remaining_visits: int | None
    remaining_amount: Decimal | None
    payment_id: UUID | None
    notes: str | None = None

    class Config:
        from_attributes = True


class SharedWithItem(BaseModel):
    """B6.1 FamilyLink: family member who can use the subscription."""
    patient_id: UUID
    patient_name: str


class CustomerSubscriptionWithSharedRead(CustomerSubscriptionRead):
    """Customer subscription with shared_with list (for GET by id)."""
    shared_with: list[SharedWithItem] = []


class WalletRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    balance: Decimal
    currency: str
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    wallet_id: UUID
    type: str
    amount: Decimal
    happened_at: datetime
    booking_id: UUID | None = None
    subscription_id: UUID | None = None
    description: str | None = None
    beneficiary_patient_id: UUID | None = None
    family_link_id: UUID | None = None

    class Config:
        from_attributes = True


class SubscriptionUsageRead(BaseModel):
    id: UUID
    clinic_id: UUID
    customer_subscription_id: UUID
    booking_id: UUID
    used_visits: int | None
    used_amount: Decimal | None
    used_at: datetime
    beneficiary_patient_id: UUID | None = None
    family_link_id: UUID | None = None

    class Config:
        from_attributes = True


class PatientSubscriptionCard(BaseModel):
    """B6.5 Digital Pass: one subscription with package details for PWA card and 'Записаться по абонементу'."""
    id: UUID
    patient_id: UUID
    subscription_package_id: UUID
    status: str
    name: str = Field(..., description="Package name")
    remaining_visits: int | None = None
    total_visits: int | None = None
    remaining_amount: Decimal | None = None
    total_amount: Decimal | None = None
    expires_at: datetime | None = None
    services_included: list[UUID] = Field(default_factory=list, description="Service IDs for filter in booking wizard")
    purchased_at: datetime = Field(..., description="For ordering")


class PatientLoyaltyMeResponse(BaseModel):
    subscriptions: list[CustomerSubscriptionRead]
    wallet: WalletRead | None
    wallet_transactions: list[WalletTransactionRead]


class PatientLoyaltyMeResponseDigitalPass(BaseModel):
    """B6.5: Same as me but subscriptions are full cards for Digital Pass (name, totals, expires_at, services_included)."""
    subscriptions: list[PatientSubscriptionCard]
    wallet: WalletRead | None
    wallet_transactions: list[WalletTransactionRead]


class PatientLoyaltyHistoryItem(BaseModel):
    """Unified view of subscription usages and wallet transactions for history timeline."""

    kind: str
    happened_at: datetime
    details: dict[str, Any]


class PatientLoyaltyHistoryResponse(BaseModel):
    items: list[PatientLoyaltyHistoryItem]


class LoyaltyWriteOffRequest(BaseModel):
    """Facade-level request DTO for Loyalty write-off on booking completion.

    This is the contract that BookingCompletionService (or ERP/Loyalty nodes)
    can use to describe how a visit should consume subscription balance/visits.
    """

    clinic_id: UUID
    patient_id: UUID
    booking_id: UUID
    subscription_id: UUID
    used_visits: int | None = None
    used_amount: Decimal | None = None
    used_at: datetime


class LoyaltyWriteOffResult(BaseModel):
    """Facade-level result DTO for Loyalty write-off on booking completion.

    Designed to be embeddable into BookingCompletionResult.loyalty_summary.
    """

    success: bool
    booking_id: UUID
    subscription_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    remaining_visits: int | None = None
    remaining_amount: Decimal | None = None

