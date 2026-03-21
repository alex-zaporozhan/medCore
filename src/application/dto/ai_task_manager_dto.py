"""DTOs for AI Task Manager (TASKS_AI_021)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


TASK_SOURCES_AI_SUGGESTED = "ai_suggested"
TASK_SOURCES_AI_AUTO = "ai_auto"


class ProposedTask(BaseModel):
    """Task proposal produced by analyzer before applying settings/limits."""

    clinic_id: UUID
    task_class: str = Field(..., min_length=1, max_length=64)

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    role_assignee: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None

    # Domain links
    booking_id: UUID | None = None
    patient_id: UUID | None = None
    lead_id: UUID | None = None

    # Optional attention linkage for dedup / UI navigation
    attention_kind: str | None = Field(default=None, max_length=32)
    attention_ref_id: UUID | None = None

    requires_confirmation: bool = True
    initiated_by_ai: bool = True


class CreatedTaskResult(BaseModel):
    """Result of creating a real Task from a proposal."""

    task_id: UUID
    source: str
    clinic_id: UUID
    created_at: datetime
    proposal_class: str


class AnalysisContext(BaseModel):
    """Aggregated input for analyzer (no personal data required)."""

    clinic_id: UUID
    attention_items_total: int = 0
    # A compact representation of signals for deterministic rules.
    signals: dict = Field(default_factory=dict)

