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

