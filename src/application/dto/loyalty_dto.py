"""DTOs for loyalty (subscription packages, customer subscriptions, wallets)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionPackageBase(BaseModel):
    code: str = Field(..., description="Internal package code")
    name: str
    description: str | None = None
    kind: str = Field(..., description="visits|balance|mixed")
    services_included: list[UUID] = Field(default_factory=list)
    total_visits: int | None = None
    total_amount: Decimal | None = None
    price: Decimal
    validity_days: int | None = None
    is_active: bool = True


class SubscriptionPackageCreate(SubscriptionPackageBase):
    pass


class SubscriptionPackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    kind: str | None = None
    services_included: list[UUID] | None = None
    total_visits: int | None = None
    total_amount: Decimal | None = None
    price: Decimal | None = None
    validity_days: int | None = None
    is_active: bool | None = None


class SubscriptionPackageRead(SubscriptionPackageBase):
    id: UUID
    clinic_id: UUID

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

    class Config:
        from_attributes = True


class PatientLoyaltyMeResponse(BaseModel):
    subscriptions: list[CustomerSubscriptionRead]
    wallet: WalletRead | None
    wallet_transactions: list[WalletTransactionRead]


class PatientLoyaltyHistoryItem(BaseModel):
    """Unified view of subscription usages and wallet transactions for history timeline."""

    kind: str
    happened_at: datetime
    details: dict[str, Any]


class PatientLoyaltyHistoryResponse(BaseModel):
    items: list[PatientLoyaltyHistoryItem]

