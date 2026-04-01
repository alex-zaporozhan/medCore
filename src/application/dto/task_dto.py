"""DTOs for Task and TaskComment API (admin tasks)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.domain.entities.task import Task
    from src.domain.entities.task_comment import TaskComment


# --- Request DTOs ---


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    stream_id: UUID | None = None
    """Если не задан — поток ``general`` клиники (или первый активный)."""
    tag_ids: list[UUID] | None = None
    assignee_id: UUID | None = None
    """Один исполнитель (совместимо со старыми клиентами); приоритет ниже assignee_ids."""
    assignee_ids: list[UUID] | None = None
    """Несколько исполнителей (коробка). Если задано, формирует строки в task_assignees."""
    role_assignee: str | None = None
    due_at: datetime | None = None
    booking_id: UUID | None = None
    patient_id: UUID | None = None
    lead_id: UUID | None = None
    inventory_product_id: UUID | None = None


class TaskUpdate(BaseModel):
    """Request body for PATCH task (partial update)."""

    status: str | None = Field(
        None, pattern="^(open|in_progress|on_hold|review|done|cancelled)$"
    )
    stream_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    assignee_id: UUID | None = None
    assignee_ids: list[UUID] | None = None
    role_assignee: str | None = None
    due_at: datetime | None = None
    rank: int | None = None
    blocked: bool | None = None
    blocked_reason: str | None = None
    checklist_done: bool | None = None
    transition_reason: str | None = None


class TaskCommentCreate(BaseModel):
    """Request body for adding a comment to a task."""

    text: str = Field(..., min_length=1)


# --- Response DTOs ---


class TaskResponse(BaseModel):
    """Single task in list or detail response."""

    id: UUID
    clinic_id: UUID
    stream_id: UUID
    tag_ids: list[UUID] = Field(default_factory=list)
    title: str
    description: str | None
    status: str
    priority: str
    creator_id: UUID | None
    assignee_id: UUID | None
    assignee_ids: list[UUID] = Field(default_factory=list)
    role_assignee: str | None
    due_at: datetime | None
    completed_at: datetime | None
    booking_id: UUID | None
    patient_id: UUID | None
    lead_id: UUID | None
    inventory_product_id: UUID | None
    source: str
    trace_id: str | None = None
    rank: int
    blocked: bool
    blocked_reason: str | None = None
    checklist_done: bool = False
    stage_entered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCommentResponse(BaseModel):
    """Single comment in response."""

    id: UUID
    task_id: UUID
    author_id: UUID
    author_full_name: str | None = None
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- List filters (for query params; not a Pydantic body) ---

TASK_STATUSES = ("open", "in_progress", "on_hold", "review", "done", "cancelled")
TASK_PRIORITIES = ("low", "medium", "high", "urgent")


def task_entity_to_response(
    task: "Task",
    *,
    assignee_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
) -> TaskResponse:
    """Build TaskResponse from domain Task entity."""
    aids = assignee_ids if assignee_ids is not None else []
    tids = tag_ids if tag_ids is not None else []
    return TaskResponse(
        id=task.id,
        clinic_id=task.clinic_id,
        stream_id=task.stream_id,
        tag_ids=tids,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        assignee_ids=aids,
        role_assignee=task.role_assignee,
        due_at=task.due_at,
        completed_at=task.completed_at,
        booking_id=task.booking_id,
        patient_id=task.patient_id,
        lead_id=task.lead_id,
        inventory_product_id=task.inventory_product_id,
        source=task.source,
        trace_id=task.trace_id,
        rank=task.rank,
        blocked=task.blocked,
        blocked_reason=task.blocked_reason,
        checklist_done=task.checklist_done,
        stage_entered_at=task.stage_entered_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def task_comment_entity_to_response(
    comment: "TaskComment",
    *,
    author_full_name: str | None = None,
) -> TaskCommentResponse:
    """Build TaskCommentResponse from domain TaskComment entity."""
    return TaskCommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        author_full_name=author_full_name,
        text=comment.text,
        created_at=comment.created_at,
    )
