"""Task repository implementation using SQLAlchemy AsyncSession."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_comment import TaskComment
from src.domain.interfaces.repositories.task_repository import TaskRepository


class TaskRepositoryImpl(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(self, task: Task) -> Task:
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        return await self._session.get(Task, task_id)

    async def save_task(self, task: Task) -> Task:
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def add_comment(self, comment: TaskComment) -> TaskComment:
        self._session.add(comment)
        await self._session.flush()
        await self._session.refresh(comment)
        return comment

    async def list_comments_for_task(self, task_id: UUID) -> list[TaskComment]:
        res = await self._session.execute(
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at.asc())
        )
        return list(res.scalars().all())

    async def replace_task_assignees(self, task_id: UUID, admin_ids: list[UUID]) -> None:
        await self._session.execute(delete(TaskAssignee).where(TaskAssignee.task_id == task_id))
        for aid in admin_ids:
            self._session.add(TaskAssignee(task_id=task_id, admin_id=aid))
        await self._session.flush()

    async def list_assignee_ids_for_task_ids(self, task_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        if not task_ids:
            return {}
        res = await self._session.execute(
            select(TaskAssignee.task_id, TaskAssignee.admin_id).where(
                TaskAssignee.task_id.in_(task_ids)
            )
        )
        out: dict[UUID, list[UUID]] = {tid: [] for tid in task_ids}
        for task_id, admin_id in res.all():
            out.setdefault(task_id, []).append(admin_id)
        return out

