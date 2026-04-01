"""DTOs for resolving omni chat into immutable lead log."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class OmniChatResolveResponseDto(BaseModel):
    lead_log_id: UUID = Field(..., description="Created (or existing) omni lead log id")
    task_id: UUID | None = Field(None, description="Task artifact id (done) in leads-log stream")
    outcome: str | None = Field(None, description="BOOKED | NOT_BOOKED | UNKNOWN")

