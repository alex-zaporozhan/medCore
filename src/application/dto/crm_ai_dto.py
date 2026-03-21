"""DTOs for CRM AI tools (CRM_AI_009).

Key constraints:
- External AI calls must not receive personal data (names/phones) unless explicitly allowed by policy.
- Prefer opaque tokens (LEAD#<uuid>) over raw UUIDs when passing entity references into AI layer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LeadSummary(BaseModel):
    """Safe minimal lead representation for AI layer."""

    lead_token: str = Field(description="Opaque lead token LEAD#<uuid>.")
    clinic_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    status: str
    title: str
    source: str
    estimated_value: Decimal = Field(default=Decimal("0.00"))
    actual_value: Decimal = Field(default=Decimal("0.00"))
    created_at: datetime | None = None
    closed_at: datetime | None = None


class LeadContextForAi(BaseModel):
    """Aggregated lead context for AI prompts (no personal data)."""

    lead: LeadSummary
    notes_preview: list[str] = Field(default_factory=list, description="Last notes/messages preview without personal data.")
    open_tasks_count: int = 0
    in_progress_tasks_count: int = 0
    done_tasks_count: int = 0


class SuggestNextStageInput(BaseModel):
    clinic_id: UUID
    lead_token: str | None = Field(default=None, description="Preferred. LEAD#<uuid>.")
    lead_id: UUID | None = Field(default=None, description="DEPRECATED. Use lead_token.")
    trace_id: str | None = None


class SuggestNextStageOutput(BaseModel):
    suggested_stage_id: UUID | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, max_length=2000)
    ai_status: str | None = None
    trace_id: str | None = None


class SummarizeLeadContextInput(BaseModel):
    clinic_id: UUID
    lead_token: str | None = Field(default=None, description="Preferred. LEAD#<uuid>.")
    lead_id: UUID | None = Field(default=None, description="DEPRECATED. Use lead_token.")
    trace_id: str | None = None


class SummarizeLeadContextOutput(BaseModel):
    summary: str
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    ai_status: str | None = None
    trace_id: str | None = None


class UpdateLeadStageInput(BaseModel):
    clinic_id: UUID
    lead_token: str | None = Field(default=None, description="Preferred. LEAD#<uuid>.")
    lead_id: UUID | None = Field(default=None, description="DEPRECATED. Use lead_token.")
    target_stage_id: UUID
    reason: str | None = Field(default=None, max_length=500)
    initiated_by_ai: bool = Field(default=True)
    trace_id: str | None = None


class UpdateLeadStageOutput(BaseModel):
    success: bool
    lead: LeadSummary | None = None
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str | None = None


class CreateLeadTaskInput(BaseModel):
    clinic_id: UUID
    lead_token: str | None = Field(default=None, description="Preferred. LEAD#<uuid>.")
    lead_id: UUID | None = Field(default=None, description="DEPRECATED. Use lead_token.")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", description="low|medium|high")
    due_at: datetime | None = None
    # Optional attention linkage if the task is created as a follow-up to an attention item.
    attention_kind: str | None = None
    attention_ref_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=500)
    initiated_by_ai: bool = Field(default=True)
    trace_id: str | None = None


class CreateLeadTaskOutput(BaseModel):
    success: bool
    task_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str | None = None


class IgnoreLeadRecommendationInput(BaseModel):
    clinic_id: UUID
    kind: str = Field(description="stage|task|summary (what was ignored)")
    reason: str | None = Field(default=None, max_length=500)
    trace_id: str | None = None


class IgnoreLeadRecommendationOutput(BaseModel):
    success: bool = True
    trace_id: str | None = None

