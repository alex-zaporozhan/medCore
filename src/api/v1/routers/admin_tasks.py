"""Admin Tasks API: list, details, create/update tasks and comments."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
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
from src.application.services.task_service import TaskService
from src.domain.entities.task import Task
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


def _task_visible_to_context(task: Task, context: AdminContext) -> bool:
    """True if task is visible to current user (clinic + doctor scope)."""
    if context.clinic_id is None or task.clinic_id != context.clinic_id:
        return False
    if not _is_doctor_only(context):
        return True
    if context.user_id is None:
        return False
    return task.assignee_id == context.user_id or task.role_assignee == "doctor"


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
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskResponse]:
    """List tasks for current clinic with filters. Doctors see only tasks assigned to them or to role 'doctor'."""
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    stmt = select(Task).where(Task.clinic_id == clinic_id)
    if _is_doctor_only(context) and context.user_id:
        stmt = stmt.where(
            or_(
                Task.assignee_id == context.user_id,
                Task.role_assignee == "doctor",
            )
        )
    if status_filter and status_filter in TASK_STATUSES:
        stmt = stmt.where(Task.status == status_filter)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
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
    stmt = stmt.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())

    result = await session.execute(stmt)
    tasks = result.scalars().unique().all()
    return [task_entity_to_response(t) for t in tasks]


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
    if not _task_visible_to_context(task, context):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task = await service.reassign_task(
        task_id=task_id,
        assignee_id=context.user_id,
        role_assignee=None,
    )
    return task_entity_to_response(task)


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
    if not _task_visible_to_context(task, context):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_entity_to_response(task)


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
    service = _get_task_service(session)
    task = await service.create_task(
        clinic_id=clinic_id,
        title=data.title.strip(),
        description=data.description,
        priority=priority,
        creator_id=context.user_id,
        assignee_id=data.assignee_id,
        role_assignee=data.role_assignee,
        due_at=data.due_at,
        booking_id=data.booking_id,
        patient_id=data.patient_id,
        lead_id=data.lead_id,
        inventory_product_id=data.inventory_product_id,
        source="manual",
    )
    return task_entity_to_response(task)


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
    if not _task_visible_to_context(task, context):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if data.status is not None:
        task = await service.update_task_status(
            task_id=task_id,
            status=data.status,
            completed_at=datetime.utcnow() if data.status == "done" else None,
        )
    if data.assignee_id is not None or data.role_assignee is not None:
        task = await service.reassign_task(
            task_id=task_id,
            assignee_id=data.assignee_id,
            role_assignee=data.role_assignee,
        )
    if data.due_at is not None:
        task.due_at = data.due_at
        await session.flush()
        await session.refresh(task)

    task = await service.get_task_details(task_id)
    return task_entity_to_response(task)


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
    task = await service.get_task_details(task_id)
    if not _task_visible_to_context(task, context):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comment: TaskComment = await service.add_comment(
        task_id=task_id,
        author_id=context.user_id,
        text=data.text.strip(),
    )
    return task_comment_entity_to_response(comment)

