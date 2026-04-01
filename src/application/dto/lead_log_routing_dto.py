"""DTOs for lead-log routing rules."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LeadLogRoutingRuleDto(BaseModel):
    id: UUID
    channel_type: str | None = None
    source_key: str | None = None
    target_stream_id: UUID
    is_active: bool = True
    sort_order: int = 0

    model_config = {"from_attributes": True}


class LeadLogRoutingRuleUpsertItem(BaseModel):
    channel_type: str | None = Field(None, max_length=64)
    source_key: str | None = Field(None, max_length=128)
    target_stream_id: UUID
    is_active: bool = True
    sort_order: int = 0


class ReplaceLeadLogRoutingRulesRequest(BaseModel):
    rules: list[LeadLogRoutingRuleUpsertItem] = Field(default_factory=list)


class SimulateLeadLogRoutingRequest(BaseModel):
    channel_type: str | None = Field(None, max_length=64)
    source_key: str | None = Field(None, max_length=128)


class SimulateLeadLogRoutingResponse(BaseModel):
    matched_rule_id: UUID | None = None
    target_stream_id: UUID | None = None

