"""DTOs for clinic-scoped FamilyLink (loyalty spend / history)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


RelationType = Literal["parent", "child", "spouse", "guardian", "other"]


class FamilyLinkCreate(BaseModel):
    primary_patient_id: UUID
    related_patient_id: UUID
    relation_type: RelationType = Field(
        default="other",
        description="Directed relationship label (validated set).",
    )
    can_spend_from_owner_loyalty: bool = False
    can_view_owner_history: bool = False
    spending_limit_total: Decimal | None = None
    spending_limit_periodic: Decimal | None = None
    valid_until: datetime | None = None


class FamilyLinkUpdate(BaseModel):
    relation_type: RelationType | None = None
    can_spend_from_owner_loyalty: bool | None = None
    can_view_owner_history: bool | None = None
    spending_limit_total: Decimal | None = None
    spending_limit_periodic: Decimal | None = None
    valid_until: datetime | None = None


class FamilyLinkRead(BaseModel):
    id: UUID
    clinic_id: UUID
    primary_patient_id: UUID
    related_patient_id: UUID
    # DB may contain legacy strings; writes are constrained to RelationType.
    relation_type: str
    can_spend_from_owner_loyalty: bool
    can_view_owner_history: bool
    spending_limit_total: Decimal | None = None
    spending_limit_periodic: Decimal | None = None
    valid_until: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    is_active: bool

    class Config:
        from_attributes = True
