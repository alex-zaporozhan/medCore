"""DTOs for Task and TaskComment API (admin tasks)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request DTOs ---


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    assignee_id: UUID | None = None
    role_assignee: str | None = None
    due_at: datetime | None = None
    booking_id: UUID | None = None
    patient_id: UUID | None = None
    lead_id: UUID | None = None
    inventory_product_id: UUID | None = None


class TaskUpdate(BaseModel):
    """Request body for PATCH task (partial update)."""

    status: str | None = Field(None, pattern="^(open|in_progress|done|cancelled)$")
    assignee_id: UUID | None = None
    role_assignee: str | None = None
    due_at: datetime | None = None


class TaskCommentCreate(BaseModel):
    """Request body for adding a comment to a task."""

    text: str = Field(..., min_length=1)


# --- Response DTOs ---


class TaskResponse(BaseModel):
    """Single task in list or detail response."""

    id: UUID
    clinic_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    creator_id: UUID | None
    assignee_id: UUID | None
    role_assignee: str | None
    due_at: datetime | None
    completed_at: datetime | None
    booking_id: UUID | None
    patient_id: UUID | None
    lead_id: UUID | None
    inventory_product_id: UUID | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCommentResponse(BaseModel):
    """Single comment in response."""

    id: UUID
    task_id: UUID
    author_id: UUID
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- List filters (for query params; not a Pydantic body) ---

TASK_STATUSES = ("open", "in_progress", "done", "cancelled")
TASK_PRIORITIES = ("low", "medium", "high", "urgent")


def task_entity_to_response(task: "Task") -> TaskResponse:
    """Build TaskResponse from domain Task entity."""
    return TaskResponse(
        id=task.id,
        clinic_id=task.clinic_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        role_assignee=task.role_assignee,
        due_at=task.due_at,
        completed_at=task.completed_at,
        booking_id=task.booking_id,
        patient_id=task.patient_id,
        lead_id=task.lead_id,
        inventory_product_id=task.inventory_product_id,
        source=task.source,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def task_comment_entity_to_response(comment: "TaskComment") -> TaskCommentResponse:
    """Build TaskCommentResponse from domain TaskComment entity."""
    return TaskCommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        text=comment.text,
        created_at=comment.created_at,
    )
