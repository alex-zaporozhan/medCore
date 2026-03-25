"""Task repository interface."""

from typing import Protocol
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment


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

