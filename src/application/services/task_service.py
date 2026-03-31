"""Task service: high-level operations for creating and managing tasks."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_status_transition import TaskStatusTransition
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.core.metrics import tasks_created_total, task_time_to_close_seconds
from src.core.metrics import (
    task_blocked_events_total,
    task_sla_overdue_total,
    task_status_transitions_total,
)
from src.core.prometheus_labels import clinic_bucket_label

COMMENT_RATE_LIMIT_WINDOW_SECONDS = 60
COMMENT_RATE_LIMIT_PER_WINDOW = 12
SYSTEM_COMMENT_RATE_LIMIT_PER_WINDOW = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskService:
    @staticmethod
    def _status_transition_text(
        *,
        from_status: str,
        to_status: str,
        reason: str | None,
    ) -> str:
        msg = f"Системное событие: статус задачи изменен {from_status} -> {to_status}."
        if reason:
            msg += f" Причина: {reason.strip()}."
        return msg

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
        stream_id: UUID | None = None,
        tag_ids: list[UUID] | None = None,
    ) -> Task:
        ids: list[UUID] = list(assignee_ids) if assignee_ids else []
        if not ids and assignee_id is not None:
            ids = [assignee_id]
        primary = ids[0] if ids else None
        resolved_stream = stream_id
        if resolved_stream is None:
            resolved_stream = await self._repo.get_default_task_stream_id(clinic_id)
        if resolved_stream is None:
            raise ValueError("NO_TASK_STREAM_FOR_CLINIC")
        task = Task(
            clinic_id=clinic_id,
            stream_id=resolved_stream,
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
        ttags = list(dict.fromkeys(tag_ids or []))
        if ttags:
            await self._repo.replace_task_tags(created.id, ttags)
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
        actor_admin_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> Task:
        task = await self._require_task(task_id)
        old_status = task.status
        if status == "done":
            if task.blocked:
                raise ValueError("TASK_BLOCKED")
            if not task.checklist_done:
                raise ValueError("CHECKLIST_REQUIRED")
        task.status = status
        if old_status != status:
            task.stage_entered_at = _utc_now()
        task.updated_by_admin_id = actor_admin_id
        if completed_at is not None:
            task.completed_at = completed_at
        saved = await self._repo.save_task(task)
        if old_status != status:
            await self._repo.add_status_transition(
                TaskStatusTransition(
                    clinic_id=saved.clinic_id,
                    task_id=saved.id,
                    from_status=old_status,
                    to_status=status,
                    reason=reason,
                    actor_admin_id=actor_admin_id,
                    metadata_json=dict(metadata or {}),
                )
            )
            # Keep task-room timeline in sync with workflow changes.
            if actor_admin_id is not None:
                recent_system_comments = await self._repo.count_comments_for_author_since(
                    task_id=saved.id,
                    author_id=actor_admin_id,
                    since=_utc_now() - timedelta(seconds=COMMENT_RATE_LIMIT_WINDOW_SECONDS),
                    system_only=True,
                )
                if recent_system_comments >= SYSTEM_COMMENT_RATE_LIMIT_PER_WINDOW:
                    raise ValueError("SYSTEM_COMMENT_RATE_LIMITED")
                await self._repo.add_comment(
                    TaskComment(
                        task_id=saved.id,
                        author_id=actor_admin_id,
                        text=self._status_transition_text(
                            from_status=old_status,
                            to_status=status,
                            reason=reason,
                        ),
                    )
                )
            task_status_transitions_total.labels(
                clinic_bucket=clinic_bucket_label(saved.clinic_id),
                from_status=old_status,
                to_status=status,
            ).inc()
        if saved.status == "done" and saved.completed_at is not None:
            delta = (saved.completed_at - saved.created_at).total_seconds()
            if delta >= 0:
                task_time_to_close_seconds.labels(
                    clinic_bucket=clinic_bucket_label(saved.clinic_id),
                    source=saved.source,
                    attention_kind=saved.attention_kind or "none",
                ).observe(delta)
            if saved.due_at is not None and saved.completed_at > saved.due_at:
                task_sla_overdue_total.labels(
                    clinic_bucket=clinic_bucket_label(saved.clinic_id),
                    source=saved.source,
                ).inc()
        return saved

    async def update_task_fields(
        self,
        *,
        task_id: UUID,
        rank: int | None = None,
        blocked: bool | None = None,
        blocked_reason: str | None = None,
        checklist_done: bool | None = None,
        actor_admin_id: UUID | None = None,
    ) -> Task:
        task = await self._require_task(task_id)
        if rank is not None:
            task.rank = rank
        if blocked is not None:
            prev_blocked = task.blocked
            task.blocked = blocked
            if not blocked:
                task.blocked_reason = None
            if prev_blocked != blocked:
                task_blocked_events_total.labels(
                    clinic_bucket=clinic_bucket_label(task.clinic_id),
                    action="blocked" if blocked else "unblocked",
                ).inc()
                await self._repo.add_status_transition(
                    TaskStatusTransition(
                        clinic_id=task.clinic_id,
                        task_id=task.id,
                        from_status=task.status,
                        to_status=task.status,
                        reason=blocked_reason if blocked else "UNBLOCKED",
                        actor_admin_id=actor_admin_id,
                        metadata_json={
                            "event": "blocked" if blocked else "unblocked",
                            "source": "task_fields",
                        },
                    )
                )
        if blocked_reason is not None:
            task.blocked_reason = blocked_reason
        if checklist_done is not None:
            task.checklist_done = checklist_done
        task.updated_by_admin_id = actor_admin_id
        return await self._repo.save_task(task)

    async def list_status_transitions_for_task(
        self, task_id: UUID, limit: int = 50
    ) -> list[TaskStatusTransition]:
        await self._require_task(task_id)
        return await self._repo.list_status_transitions_for_task(task_id, limit=limit)

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

    async def set_task_stream(self, task_id: UUID, stream_id: UUID) -> Task:
        task = await self._require_task(task_id)
        task.stream_id = stream_id
        return await self._repo.save_task(task)

    async def set_task_tags(self, task_id: UUID, tag_ids: list[UUID]) -> Task:
        await self._require_task(task_id)
        await self._repo.replace_task_tags(task_id, list(dict.fromkeys(tag_ids)))
        return await self._require_task(task_id)

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
        recent_comments = await self._repo.count_comments_for_author_since(
            task_id=task.id,
            author_id=author_id,
            since=_utc_now() - timedelta(seconds=COMMENT_RATE_LIMIT_WINDOW_SECONDS),
            system_only=False,
        )
        if recent_comments >= COMMENT_RATE_LIMIT_PER_WINDOW:
            raise ValueError("COMMENT_RATE_LIMITED")
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

