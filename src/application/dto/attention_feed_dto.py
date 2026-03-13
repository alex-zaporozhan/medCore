"""DTOs for attention feed (owner's attention panel)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttentionItemRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    kind: str  # "follow_up" | "retention_gap" | "conflict"
    title: str
    description: str
    priority: int
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    patient_full_name: str | None
    patient_phone: str
    patient_tags: list[str] = []
    status: str  # "open" | "done"
    assigned_admin_id: UUID | None = None
    assigned_admin_name: str | None = None
    has_comment: bool = False
    last_comment_preview: str | None = None
    conversation_id: UUID | None = None


class AttentionFeedRead(BaseModel):
    follow_up: list[AttentionItemRead]
    retention_gap: list[AttentionItemRead]
    conflicts: list[AttentionItemRead]

