"""Admin Tasks API: list, details, create/update tasks and comments."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.task_dto import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    task_comment_entity_to_response,
    task_entity_to_response,
)
from src.application.services.staff_collaboration_service import StaffCollaborationService
from src.application.services.task_service import TaskService
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_comment import TaskComment
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl


router = APIRouter(
    prefix="/admin/tasks",
    tags=["admin-tasks"],
)


def _get_task_service(session: AsyncSession) -> TaskService:
    repo: TaskRepository = TaskRepositoryImpl(session)
    return TaskService(repo)


def _is_doctor_only(context: AdminContext) -> bool:
    """True if user has only doctor role (no owner/manager/admin). Doctors see only their tasks."""
    full_scope = {"owner", "manager", "admin"}
    return bool(context.roles and not full_scope.intersection(context.roles))


async def _task_visible_to_context(
    task: Task, context: AdminContext, session: AsyncSession
) -> bool:
    """True if task is visible to current user (clinic + doctor scope)."""
    if context.clinic_id is None or task.clinic_id != context.clinic_id:
        return False
    if not _is_doctor_only(context):
        return True
    if context.user_id is None:
        return False
    if task.assignee_id == context.user_id or task.role_assignee == "doctor":
        return True
    res = await session.execute(
        select(TaskAssignee.admin_id).where(
            TaskAssignee.task_id == task.id,
            TaskAssignee.admin_id == context.user_id,
        ).limit(1)
    )
    return res.scalar_one_or_none() is not None


async def _task_response(session: AsyncSession, task: Task) -> TaskResponse:
    repo: TaskRepository = TaskRepositoryImpl(session)
    m = await repo.list_assignee_ids_for_task_ids([task.id])
    return task_entity_to_response(task, assignee_ids=m.get(task.id, []))


@router.get(
    "",
    response_model=list[TaskResponse],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    assignee_id: UUID | None = Query(None),
    role_assignee: str | None = Query(None),
    due_from: datetime | None = Query(None),
    due_to: datetime | None = Query(None),
    source: str | None = Query(None, description="Filter by source; use 'ai' for AI-suggested/auto tasks"),
    attention_kind: str | None = Query(
        None,
        description="Filter by linked attention item kind (follow_up|retention_gap|conflict)",
    ),
    attention_ref_id: UUID | None = Query(
        None,
        description="Filter by linked attention item id (underlying entity id from attention feed)",
    ),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskResponse]:
    """List tasks for current clinic with filters. Doctors see only tasks assigned to them or to role 'doctor'."""
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    stmt = select(Task).where(Task.clinic_id == clinic_id)
    if _is_doctor_only(context) and context.user_id:
        in_assignees = exists(
            select(TaskAssignee.task_id).where(
                TaskAssignee.task_id == Task.id,
                TaskAssignee.admin_id == context.user_id,
            )
        )
        stmt = stmt.where(
            or_(
                Task.assignee_id == context.user_id,
                Task.role_assignee == "doctor",
                in_assignees,
            )
        )
    if status_filter and status_filter in TASK_STATUSES:
        stmt = stmt.where(Task.status == status_filter)
    if assignee_id:
        in_assignee_table = Task.id.in_(
            select(TaskAssignee.task_id).where(TaskAssignee.admin_id == assignee_id)
        )
        stmt = stmt.where(or_(Task.assignee_id == assignee_id, in_assignee_table))
    if role_assignee:
        stmt = stmt.where(Task.role_assignee == role_assignee)
    if due_from:
        stmt = stmt.where(Task.due_at >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_at <= due_to)
    if source == "ai":
        stmt = stmt.where(Task.source.in_(["ai_suggested", "ai_auto"]))
    elif source:
        stmt = stmt.where(Task.source == source)
    if attention_kind:
        stmt = stmt.where(Task.attention_kind == attention_kind)
    if attention_ref_id:
        stmt = stmt.where(Task.attention_ref_id == attention_ref_id)
    stmt = stmt.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())

    result = await session.execute(stmt)
    tasks = result.scalars().unique().all()
    if not tasks:
        return []
    repo = TaskRepositoryImpl(session)
    amap = await repo.list_assignee_ids_for_task_ids([t.id for t in tasks])
    return [task_entity_to_response(t, assignee_ids=amap.get(t.id, [])) for t in tasks]


@router.post(
    "/{task_id}/claim",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("manage_tasks", "assign_tasks"))],
)
async def claim_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskResponse:
    """Assign task to current user (claim). Returns updated task or 404."""
    if context.clinic_id is None or context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic and user context required")
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task = await service.reassign_task(
        task_id=task_id,
        assignee_id=context.user_id,
        role_assignee=None,
    )
    await StaffCollaborationService(session).sync_task_room_members_for_task(
        context.clinic_id, task_id
    )
    return await _task_response(session, task)


@router.get(
    "/{task_id}/comments",
    response_model=list[TaskCommentResponse],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def list_task_comments(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskCommentResponse]:
    """Чат задачи: список комментариев (хронологический порядок)."""
    service = _get_task_service(session)
    try:
        task = await service.get_task_details(task_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        comments = await service.list_comments_for_task(task_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not comments:
        return []
    author_ids = {c.author_id for c in comments}
    res = await session.execute(select(AdminUser).where(AdminUser.id.in_(author_ids)))
    name_by_id = {a.id: a.full_name for a in res.scalars().all()}
    return [
        task_comment_entity_to_response(c, author_full_name=name_by_id.get(c.author_id))
        for c in comments
    ]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def get_task_details(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskResponse:
    """Return single task details. Doctors get 404 for tasks not assigned to them or role 'doctor'."""
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return await _task_response(session, task)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks", "assign_tasks"))],
)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskResponse:
    """Create a new task manually."""
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    priority = data.priority if data.priority in TASK_PRIORITIES else "medium"
    assignee_ids: list[UUID] | None = None
    if data.assignee_ids is not None:
        assignee_ids = list(data.assignee_ids)
    elif data.assignee_id is not None:
        assignee_ids = [data.assignee_id]
    service = _get_task_service(session)
    task = await service.create_task(
        clinic_id=clinic_id,
        title=data.title.strip(),
        description=data.description,
        priority=priority,
        creator_id=context.user_id,
        assignee_id=data.assignee_id,
        assignee_ids=assignee_ids,
        role_assignee=data.role_assignee,
        due_at=data.due_at,
        booking_id=data.booking_id,
        patient_id=data.patient_id,
        lead_id=data.lead_id,
        inventory_product_id=data.inventory_product_id,
        source="manual",
    )
    await StaffCollaborationService(session).sync_task_room_members_for_task(clinic_id, task.id)
    return await _task_response(session, task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("manage_tasks", "assign_tasks"))],
)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskResponse:
    """Update task status, assignee or due date. Doctors get 404 for tasks not assigned to them."""
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    reassigned = False
    if data.status is not None:
        task = await service.update_task_status(
            task_id=task_id,
            status=data.status,
            completed_at=datetime.utcnow() if data.status == "done" else None,
        )
    if data.assignee_ids is not None:
        task = await service.set_task_assignees(task_id, list(data.assignee_ids))
        reassigned = True
    elif data.assignee_id is not None or data.role_assignee is not None:
        task = await service.reassign_task(
            task_id=task_id,
            assignee_id=data.assignee_id,
            role_assignee=data.role_assignee,
        )
        reassigned = True
    if data.due_at is not None:
        task = await service.get_task_details(task_id)
        task.due_at = data.due_at
        await session.flush()
        await session.refresh(task)

    task = await service.get_task_details(task_id)
    if context.clinic_id is not None and reassigned:
        await StaffCollaborationService(session).sync_task_room_members_for_task(
            context.clinic_id, task_id
        )
    return await _task_response(session, task)


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def create_task_comment(
    task_id: UUID,
    data: TaskCommentCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskCommentResponse:
    """Add a comment to a task. Doctors get 404 for tasks not assigned to them."""
    service = _get_task_service(session)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User context required")
    try:
        task = await service.get_task_details(task_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comment: TaskComment = await service.add_comment(
        task_id=task_id,
        author_id=context.user_id,
        text=data.text.strip(),
    )
    res = await session.execute(select(AdminUser).where(AdminUser.id == context.user_id))
    author = res.scalar_one_or_none()
    return task_comment_entity_to_response(
        comment,
        author_full_name=author.full_name if author else None,
    )

