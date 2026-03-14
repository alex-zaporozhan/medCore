"""Task service: high-level operations for creating and managing tasks."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment
from src.domain.interfaces.repositories.task_repository import TaskRepository


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    async def create_task(
        self,
        *,
        clinic_id: UUID,
        title: str,
        description: str | None = None,
        status: str = "open",
        priority: str = "medium",
        creator_id: UUID | None = None,
        assignee_id: UUID | None = None,
        role_assignee: str | None = None,
        due_at: datetime | None = None,
        booking_id: UUID | None = None,
        patient_id: UUID | None = None,
        lead_id: UUID | None = None,
        inventory_product_id: UUID | None = None,
        source: str = "manual",
        source_event_id: UUID | None = None,
    ) -> Task:
        task = Task(
            clinic_id=clinic_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            creator_id=creator_id,
            assignee_id=assignee_id,
            role_assignee=role_assignee,
            due_at=due_at,
            booking_id=booking_id,
            patient_id=patient_id,
            lead_id=lead_id,
            inventory_product_id=inventory_product_id,
            source=source,
            source_event_id=source_event_id,
        )
        return await self._repo.create_task(task)

    async def update_task_status(
        self,
        *,
        task_id: UUID,
        status: str,
        completed_at: datetime | None = None,
    ) -> Task:
        task = await self._require_task(task_id)
        task.status = status
        if completed_at is not None:
            task.completed_at = completed_at
        return await self._repo.save_task(task)

    async def reassign_task(
        self,
        *,
        task_id: UUID,
        assignee_id: UUID | None,
        role_assignee: str | None,
    ) -> Task:
        task = await self._require_task(task_id)
        task.assignee_id = assignee_id
        task.role_assignee = role_assignee
        return await self._repo.save_task(task)

    async def add_comment(
        self,
        *,
        task_id: UUID,
        author_id: UUID,
        text: str,
    ) -> TaskComment:
        task = await self._require_task(task_id)
        comment = TaskComment(
            task_id=task.id,
            author_id=author_id,
            text=text,
        )
        return await self._repo.add_comment(comment)

    async def get_task_details(self, task_id: UUID) -> Task:
        return await self._require_task(task_id)

    async def _require_task(self, task_id: UUID) -> Task:
        task = await self._repo.get_task(task_id)
        if not task:
            raise LookupError(f"Task {task_id} not found")
        return task

