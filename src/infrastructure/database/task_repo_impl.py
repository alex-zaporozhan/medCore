"""Task repository implementation using SQLAlchemy AsyncSession."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_status_transition import TaskStatusTransition
from src.domain.entities.task_stream import TaskStream
from src.domain.entities.task_task_tag import TaskTaskTag
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

    async def get_default_task_stream_id(self, clinic_id: UUID) -> UUID | None:
        res = await self._session.execute(
            select(TaskStream.id).where(
                TaskStream.clinic_id == clinic_id,
                TaskStream.slug == "general",
                TaskStream.is_archived.is_(False),
            )
        )
        sid = res.scalar_one_or_none()
        if sid is not None:
            return sid
        res2 = await self._session.execute(
            select(TaskStream.id)
            .where(
                TaskStream.clinic_id == clinic_id,
                TaskStream.is_archived.is_(False),
            )
            .order_by(TaskStream.sort_order.asc(), TaskStream.name.asc())
            .limit(1)
        )
        return res2.scalar_one_or_none()

    async def list_tag_ids_for_task_ids(self, task_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        if not task_ids:
            return {}
        res = await self._session.execute(
            select(TaskTaskTag.task_id, TaskTaskTag.tag_id).where(
                TaskTaskTag.task_id.in_(task_ids)
            )
        )
        out: dict[UUID, list[UUID]] = {tid: [] for tid in task_ids}
        for task_id, tag_id in res.all():
            out.setdefault(task_id, []).append(tag_id)
        return out

    async def replace_task_tags(self, task_id: UUID, tag_ids: list[UUID]) -> None:
        await self._session.execute(delete(TaskTaskTag).where(TaskTaskTag.task_id == task_id))
        for tid in tag_ids:
            self._session.add(TaskTaskTag(task_id=task_id, tag_id=tid))
        await self._session.flush()

    async def add_status_transition(self, transition: TaskStatusTransition) -> TaskStatusTransition:
        self._session.add(transition)
        await self._session.flush()
        await self._session.refresh(transition)
        return transition

    async def list_status_transitions_for_task(
        self, task_id: UUID, limit: int = 50
    ) -> list[TaskStatusTransition]:
        res = await self._session.execute(
            select(TaskStatusTransition)
            .where(TaskStatusTransition.task_id == task_id)
            .order_by(TaskStatusTransition.created_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def count_comments_for_author_since(
        self,
        *,
        task_id: UUID,
        author_id: UUID,
        since: datetime,
        system_only: bool = False,
    ) -> int:
        stmt = select(func.count(TaskComment.id)).where(
            TaskComment.task_id == task_id,
            TaskComment.author_id == author_id,
            TaskComment.created_at >= since,
        )
        if system_only:
            stmt = stmt.where(TaskComment.text.like("Системное событие:%"))
        res = await self._session.execute(stmt)
        return int(res.scalar_one() or 0)
