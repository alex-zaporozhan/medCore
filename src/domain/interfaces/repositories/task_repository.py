"""Task repository interface."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_status_transition import TaskStatusTransition


class TaskRepository(Protocol):
    async def create_task(self, task: Task) -> Task:
        ...

    async def get_task(self, task_id: UUID) -> Task | None:
        ...

    async def save_task(self, task: Task) -> Task:
        ...

    async def add_comment(self, comment: TaskComment) -> TaskComment:
        ...

    async def list_comments_for_task(self, task_id: UUID) -> list[TaskComment]:
        ...

    async def replace_task_assignees(self, task_id: UUID, admin_ids: list[UUID]) -> None:
        ...

    async def list_assignee_ids_for_task_ids(self, task_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        ...

    async def add_status_transition(self, transition: TaskStatusTransition) -> TaskStatusTransition:
        ...

    async def list_status_transitions_for_task(
        self, task_id: UUID, limit: int = 50
    ) -> list[TaskStatusTransition]:
        ...

    async def count_comments_for_author_since(
        self,
        *,
        task_id: UUID,
        author_id: UUID,
        since: datetime,
        system_only: bool = False,
    ) -> int:
        ...
