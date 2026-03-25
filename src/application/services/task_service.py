"""Task service: high-level operations for creating and managing tasks."""

from datetime import datetime
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.core.metrics import tasks_created_total, task_time_to_close_seconds
from src.core.prometheus_labels import clinic_bucket_label


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
        assignee_ids: list[UUID] | None = None,
        role_assignee: str | None = None,
        due_at: datetime | None = None,
        booking_id: UUID | None = None,
        patient_id: UUID | None = None,
        lead_id: UUID | None = None,
        inventory_product_id: UUID | None = None,
        source: str = "manual",
        source_event_id: UUID | None = None,
        attention_kind: str | None = None,
        attention_ref_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> Task:
        ids: list[UUID] = list(assignee_ids) if assignee_ids else []
        if not ids and assignee_id is not None:
            ids = [assignee_id]
        primary = ids[0] if ids else None
        task = Task(
            clinic_id=clinic_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            creator_id=creator_id,
            assignee_id=primary,
            role_assignee=role_assignee if not ids else None,
            due_at=due_at,
            booking_id=booking_id,
            patient_id=patient_id,
            lead_id=lead_id,
            inventory_product_id=inventory_product_id,
            source=source,
            source_event_id=source_event_id,
            attention_kind=attention_kind,
            attention_ref_id=attention_ref_id,
            trace_id=trace_id,
        )
        created = await self._repo.create_task(task)
        if ids:
            await self._repo.replace_task_assignees(created.id, ids)
        tasks_created_total.labels(
            clinic_bucket=clinic_bucket_label(created.clinic_id),
            source=created.source,
            attention_kind=created.attention_kind or "none",
        ).inc()
        return created

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
        saved = await self._repo.save_task(task)
        if saved.status == "done" and saved.completed_at is not None:
            delta = (saved.completed_at - saved.created_at).total_seconds()
            if delta >= 0:
                task_time_to_close_seconds.labels(
                    clinic_bucket=clinic_bucket_label(saved.clinic_id),
                    source=saved.source,
                    attention_kind=saved.attention_kind or "none",
                ).observe(delta)
        return saved

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
        saved = await self._repo.save_task(task)
        if assignee_id is not None:
            await self._repo.replace_task_assignees(task_id, [assignee_id])
        else:
            await self._repo.replace_task_assignees(task_id, [])
        return saved

    async def set_task_assignees(self, task_id: UUID, admin_ids: list[UUID]) -> Task:
        """Полная замена списка исполнителей; первый в списке — primary assignee_id."""
        task = await self._require_task(task_id)
        task.assignee_id = admin_ids[0] if admin_ids else None
        task.role_assignee = None if admin_ids else task.role_assignee
        await self._repo.save_task(task)
        await self._repo.replace_task_assignees(task_id, admin_ids)
        return await self._require_task(task_id)

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

    async def list_comments_for_task(self, task_id: UUID) -> list[TaskComment]:
        await self._require_task(task_id)
        return await self._repo.list_comments_for_task(task_id)

    async def get_task_details(self, task_id: UUID) -> Task:
        return await self._require_task(task_id)

    async def _require_task(self, task_id: UUID) -> Task:
        task = await self._repo.get_task(task_id)
        if not task:
            raise LookupError(f"Task {task_id} not found")
        return task

