"""Admin Tasks API: list, details, create/update tasks and comments."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.entitlement_dependencies import require_entitlement
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

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
from src.core.metrics import task_bulk_status_total, task_context_admin_events_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.admin_user import EMPLOYMENT_ACTIVE, AdminUser
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_event_invitation import StaffCalendarEventInvitation
from src.domain.entities.staff_calendar_event_participant import StaffCalendarEventParticipant
from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_stream import TaskStream
from src.domain.entities.task_tag_definition import TaskTagDefinition
from src.domain.entities.task_task_tag import TaskTaskTag
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_status_transition import TaskStatusTransition
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl


router = APIRouter(
    prefix="/admin/tasks",
    tags=["admin-tasks"],
    dependencies=[Depends(require_entitlement("tasks.kanban"))],
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _due_at_calendar_not_in_past(due_at: datetime | None) -> None:
    """Reject due dates before today (UTC calendar day)."""
    if due_at is None:
        return
    dt = due_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    if dt.date() < _utc_now().date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload(
                "Срок не может быть в прошлом (по календарному дню UTC)",
                "DUE_AT_IN_PAST",
                field="due_at",
            ),
        )


async def _ensure_assignee_admins_in_clinic(
    session: AsyncSession,
    clinic_id: UUID,
    admin_ids: list[UUID],
) -> None:
    if not admin_ids:
        return
    unique = list(dict.fromkeys(admin_ids))
    res = await session.execute(
        select(AdminUser.id).where(
            AdminUser.id.in_(unique),
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        )
    )
    found = set(res.scalars().all())
    if found != set(unique):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload(
                "Исполнители должны быть активными сотрудниками этой клиники",
                "ASSIGNEE_INVALID",
                field="assignee_ids",
            ),
        )


async def _ensure_task_stream_belongs_to_clinic(
    session: AsyncSession, clinic_id: UUID, stream_id: UUID
) -> None:
    """List filter: stream must exist for this clinic (archived allowed)."""
    res = await session.execute(
        select(TaskStream.id).where(
            TaskStream.id == stream_id,
            TaskStream.clinic_id == clinic_id,
        )
    )
    if res.scalar_one_or_none() is None:
        task_context_admin_events_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            event="list_reject_bad_stream",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload(
                "Поток не найден в этой клинике",
                "STREAM_NOT_IN_CLINIC",
                field="stream_id",
            ),
        )


async def _ensure_task_stream_active(
    session: AsyncSession, clinic_id: UUID, stream_id: UUID
) -> None:
    res = await session.execute(
        select(TaskStream).where(
            TaskStream.id == stream_id,
            TaskStream.clinic_id == clinic_id,
            TaskStream.is_archived.is_(False),
        )
    )
    if res.scalar_one_or_none() is None:
        task_context_admin_events_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            event="reject_inactive_stream",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload(
                "Поток не найден или архивирован",
                "STREAM_INVALID",
                field="stream_id",
            ),
        )


async def _ensure_task_tags_in_clinic(
    session: AsyncSession, clinic_id: UUID, tag_ids: list[UUID]
) -> None:
    if not tag_ids:
        return
    uniq = list(dict.fromkeys(tag_ids))
    res = await session.execute(
        select(func.count())
        .select_from(TaskTagDefinition)
        .where(
            TaskTagDefinition.id.in_(uniq),
            TaskTagDefinition.clinic_id == clinic_id,
        )
    )
    cnt = int(res.scalar_one() or 0)
    if cnt != len(uniq):
        task_context_admin_events_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            event="reject_bad_tags",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload(
                "Один или несколько тегов не принадлежат клинике",
                "TAG_INVALID",
                field="tag_ids",
            ),
        )


WIP_LIMITS: dict[str, int] = {
    "open": 8,
    "in_progress": 6,
    "on_hold": 6,
    "review": 6,
}


def err_payload(detail: str, code: str, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


def _ensure_operation_permission(
    context: AdminContext,
    *,
    specific: str,
) -> None:
    if specific in context.permissions:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=err_payload("Недостаточно прав", "FORBIDDEN"),
    )


def _ensure_all_permissions(context: AdminContext, *codes: str) -> None:
    missing = [code for code in codes if code not in context.permissions]
    if not missing:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=err_payload("Недостаточно прав", "FORBIDDEN"),
    )


class TaskTransitionResponse(BaseModel):
    id: UUID
    task_id: UUID
    from_status: str
    to_status: str
    reason: str | None = None
    actor_admin_id: UUID | None = None
    created_at: datetime
    metadata: dict = Field(default_factory=dict)


class TaskCalendarParticipantAckResponse(BaseModel):
    admin_id: UUID
    full_name: str | None = None
    acknowledged_at: datetime | None = None


class TaskCalendarEventContextResponse(BaseModel):
    event_id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime
    participants: list[TaskCalendarParticipantAckResponse] = Field(default_factory=list)
    acknowledged_count: int = 0
    participants_count: int = 0


class TaskCalendarInvitePayload(BaseModel):
    admin_ids: list[UUID] = Field(default_factory=list)


class TaskBulkStatusUpdate(BaseModel):
    task_ids: list[UUID] = Field(default_factory=list)
    to_status: str = Field(..., pattern="^(open|in_progress|on_hold|review|done|cancelled)$")
    reason: str | None = None


class TaskBulkStatusUpdateResult(BaseModel):
    applied: list[UUID] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)


class TaskReorderPayload(BaseModel):
    status: str
    ordered_task_ids: list[UUID] = Field(default_factory=list)


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
    tm = await repo.list_tag_ids_for_task_ids([task.id])
    return task_entity_to_response(
        task, assignee_ids=m.get(task.id, []), tag_ids=tm.get(task.id, [])
    )


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
    completed_from: datetime | None = Query(None, description="Filter by completed_at >= (UTC)"),
    completed_to: datetime | None = Query(None, description="Filter by completed_at <= (UTC)"),
    source: str | None = Query(None, description="Filter by source; use 'ai' for AI-suggested/auto tasks"),
    attention_kind: str | None = Query(
        None,
        description="Filter by linked attention item kind (follow_up|retention_gap|conflict)",
    ),
    attention_ref_id: UUID | None = Query(
        None,
        description="Filter by linked attention item id (underlying entity id from attention feed)",
    ),
    stream_id: UUID | None = Query(None, description="Filter by task stream (semantic context)"),
    tag_ids: list[UUID] = Query(
        default_factory=list,
        description="Repeat param; task must have all listed tags (AND)",
    ),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskResponse]:
    """List tasks for current clinic with filters. Doctors see only tasks assigned to them or to role 'doctor'."""
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")

    if stream_id is not None:
        await _ensure_task_stream_belongs_to_clinic(session, clinic_id, stream_id)
    if tag_ids:
        await _ensure_task_tags_in_clinic(session, clinic_id, list(dict.fromkeys(tag_ids)))

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
    if completed_from:
        stmt = stmt.where(Task.completed_at >= completed_from)
    if completed_to:
        stmt = stmt.where(Task.completed_at <= completed_to)
    if source == "ai":
        stmt = stmt.where(Task.source.in_(["ai_suggested", "ai_auto"]))
    elif source:
        stmt = stmt.where(Task.source == source)
    if attention_kind:
        stmt = stmt.where(Task.attention_kind == attention_kind)
    if attention_ref_id:
        stmt = stmt.where(Task.attention_ref_id == attention_ref_id)
    if stream_id:
        stmt = stmt.where(Task.stream_id == stream_id)
    if tag_ids:
        uniq_tags = list(dict.fromkeys(tag_ids))
        stmt = stmt.where(
            Task.id.in_(
                select(TaskTaskTag.task_id)
                .where(TaskTaskTag.tag_id.in_(uniq_tags))
                .group_by(TaskTaskTag.task_id)
                .having(func.count(func.distinct(TaskTaskTag.tag_id)) == len(uniq_tags))
            )
        )
    stmt = stmt.order_by(Task.status.asc(), Task.rank.asc(), Task.due_at.asc().nullslast(), Task.created_at.desc())

    result = await session.execute(stmt)
    tasks = result.scalars().unique().all()
    if not tasks:
        return []
    repo = TaskRepositoryImpl(session)
    amap = await repo.list_assignee_ids_for_task_ids([t.id for t in tasks])
    tmap = await repo.list_tag_ids_for_task_ids([t.id for t in tasks])
    return [
        task_entity_to_response(
            t, assignee_ids=amap.get(t.id, []), tag_ids=tmap.get(t.id, [])
        )
        for t in tasks
    ]


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
    if assignee_ids:
        await _ensure_assignee_admins_in_clinic(session, clinic_id, assignee_ids)
    if data.stream_id is not None:
        await _ensure_task_stream_active(session, clinic_id, data.stream_id)
    if data.tag_ids:
        await _ensure_task_tags_in_clinic(session, clinic_id, list(data.tag_ids))
    _due_at_calendar_not_in_past(data.due_at)
    service = _get_task_service(session)
    try:
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
            stream_id=data.stream_id,
            tag_ids=list(data.tag_ids) if data.tag_ids else None,
        )
    except ValueError as e:
        if str(e) == "NO_TASK_STREAM_FOR_CLINIC":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_payload(
                    "Для клиники не настроен поток задач; обратитесь к администратору",
                    "NO_TASK_STREAM",
                ),
            ) from e
        raise
    await StaffCollaborationService(session).sync_task_room_members_for_task(clinic_id, task.id)
    return await _task_response(session, task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_permissions("manage_tasks", "assign_tasks", "tasks.change_status"))],
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

    if data.due_at is not None:
        _due_at_calendar_not_in_past(data.due_at)

    reassigned = False
    if data.status is not None:
        _ensure_operation_permission(context, specific="tasks.change_status")
        # Soft WIP guardrails on backend side.
        limit = WIP_LIMITS.get(data.status)
        if limit is not None and data.status != task.status:
            cstmt = select(Task).where(
                Task.clinic_id == task.clinic_id,
                Task.status == data.status,
            )
            cres = await session.execute(cstmt)
            current_in_column = len(cres.scalars().all())
            if current_in_column >= limit:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=err_payload(
                        "Превышен лимит задач в целевой колонке (WIP)",
                        "WIP_LIMIT_EXCEEDED",
                        field="status",
                    ),
                )
        try:
            task = await service.update_task_status(
                task_id=task_id,
                status=data.status,
                completed_at=_utc_now() if data.status == "done" else None,
                actor_admin_id=context.user_id,
                reason=data.transition_reason,
            )
        except ValueError as e:
            code = str(e)
            detail = "Нарушение правил перехода статуса"
            if code == "TASK_BLOCKED":
                detail = "Задача заблокирована; нельзя перевести в «Выполнено»"
            if code == "CHECKLIST_REQUIRED":
                detail = "Сначала отметьте чеклист завершения"
            if code == "SYSTEM_COMMENT_RATE_LIMITED":
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=err_payload(
                        "Слишком много служебных сообщений о переходах за короткое время",
                        "RATE_LIMIT_EXCEEDED",
                    ),
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=err_payload(detail, code, field="status"),
            )
    if data.stream_id is not None:
        _ensure_operation_permission(context, specific="manage_tasks")
        await _ensure_task_stream_active(session, task.clinic_id, data.stream_id)
        task = await service.set_task_stream(task_id, data.stream_id)
        if context.clinic_id is not None:
            task_context_admin_events_total.labels(
                clinic_bucket=clinic_bucket_label(context.clinic_id),
                event="task_stream_updated",
            ).inc()
    if data.tag_ids is not None:
        _ensure_operation_permission(context, specific="manage_tasks")
        await _ensure_task_tags_in_clinic(session, task.clinic_id, list(data.tag_ids))
        task = await service.set_task_tags(task_id, list(data.tag_ids))
        if context.clinic_id is not None:
            task_context_admin_events_total.labels(
                clinic_bucket=clinic_bucket_label(context.clinic_id),
                event="task_tags_updated",
            ).inc()
    if data.assignee_ids is not None:
        await _ensure_assignee_admins_in_clinic(session, task.clinic_id, list(data.assignee_ids))
        task = await service.set_task_assignees(task_id, list(data.assignee_ids))
        reassigned = True
    elif data.assignee_id is not None or data.role_assignee is not None:
        if data.assignee_id is not None:
            await _ensure_assignee_admins_in_clinic(session, task.clinic_id, [data.assignee_id])
        task = await service.reassign_task(
            task_id=task_id,
            assignee_id=data.assignee_id,
            role_assignee=data.role_assignee,
        )
        reassigned = True
    if data.due_at is not None:
        # Due date policy: only task creator or management can change.
        if context.user_id != task.creator_id:
            _ensure_operation_permission(context, specific="manage_tasks")
        task = await service.get_task_details(task_id)
        task.due_at = data.due_at
        await session.flush()
        await session.refresh(task)
    if (
        data.rank is not None
        or data.blocked is not None
        or data.blocked_reason is not None
        or data.checklist_done is not None
    ):
        if data.rank is not None:
            _ensure_operation_permission(context, specific="tasks.reprioritize")
        if task.blocked and data.blocked is False:
            _ensure_operation_permission(context, specific="tasks.unblock")
        task = await service.update_task_fields(
            task_id=task_id,
            rank=data.rank,
            blocked=data.blocked,
            blocked_reason=data.blocked_reason,
            checklist_done=data.checklist_done,
            actor_admin_id=context.user_id,
        )

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
    dependencies=[Depends(require_permissions("manage_tasks", "tasks.change_status"))],
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

    try:
        comment: TaskComment = await service.add_comment(
            task_id=task_id,
            author_id=context.user_id,
            text=data.text.strip(),
        )
    except ValueError as e:
        if str(e) == "COMMENT_RATE_LIMITED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_payload(
                    "Превышен лимит комментариев к этой задаче",
                    "RATE_LIMIT_EXCEEDED",
                ),
            )
        raise
    res = await session.execute(select(AdminUser).where(AdminUser.id == context.user_id))
    author = res.scalar_one_or_none()
    return task_comment_entity_to_response(
        comment,
        author_full_name=author.full_name if author else None,
    )


@router.get(
    "/wip-policies",
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def get_wip_policies(
    _context: AdminContext = Depends(get_request_context),
) -> dict[str, int]:
    return WIP_LIMITS


@router.get(
    "/{task_id}/transitions",
    response_model=list[TaskTransitionResponse],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def get_task_transitions(
    task_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskTransitionResponse]:
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    rows = await service.list_status_transitions_for_task(task_id, limit=limit)
    return [
        TaskTransitionResponse(
            id=r.id,
            task_id=r.task_id,
            from_status=r.from_status,
            to_status=r.to_status,
            reason=r.reason,
            actor_admin_id=r.actor_admin_id,
            created_at=r.created_at,
            metadata=dict(r.metadata_json or {}),
        )
        for r in rows
    ]


@router.get(
    "/{task_id}/calendar-context",
    response_model=list[TaskCalendarEventContextResponse],
    dependencies=[Depends(require_permissions("view_tasks", "view_staff_collab"))],
)
async def get_task_calendar_context(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskCalendarEventContextResponse]:
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    ev_res = await session.execute(
        select(StaffCalendarEvent).where(
            StaffCalendarEvent.clinic_id == task.clinic_id,
            StaffCalendarEvent.task_id == task.id,
        ).order_by(StaffCalendarEvent.starts_at.asc())
    )
    events = ev_res.scalars().all()
    if not events:
        return []
    event_ids = [e.id for e in events]
    p_res = await session.execute(
        select(StaffCalendarEventParticipant.event_id, StaffCalendarEventParticipant.admin_id).where(
            StaffCalendarEventParticipant.event_id.in_(event_ids)
        )
    )
    participants_by_event: dict[UUID, list[UUID]] = {}
    for event_id, admin_id in p_res.all():
        participants_by_event.setdefault(event_id, []).append(admin_id)
    inv_res = await session.execute(
        select(
            StaffCalendarEventInvitation.event_id,
            StaffCalendarEventInvitation.invitee_admin_id,
            StaffCalendarEventInvitation.acknowledged_at,
        ).where(
            StaffCalendarEventInvitation.event_id.in_(event_ids),
        )
    )
    ack_by_event_admin: dict[tuple[UUID, UUID], datetime | None] = {}
    for event_id, invitee_admin_id, acknowledged_at in inv_res.all():
        ack_by_event_admin[(event_id, invitee_admin_id)] = acknowledged_at
    all_admin_ids = {aid for a in participants_by_event.values() for aid in a}
    admin_name: dict[UUID, str | None] = {}
    if all_admin_ids:
        names_res = await session.execute(
            select(AdminUser.id, AdminUser.full_name).where(AdminUser.id.in_(list(all_admin_ids)))
        )
        for admin_id, full_name in names_res.all():
            admin_name[admin_id] = full_name
    out: list[TaskCalendarEventContextResponse] = []
    for ev in events:
        ids = participants_by_event.get(ev.id, [])
        participants = [
            TaskCalendarParticipantAckResponse(
                admin_id=aid,
                full_name=admin_name.get(aid),
                acknowledged_at=ack_by_event_admin.get((ev.id, aid)),
            )
            for aid in ids
        ]
        acknowledged_count = sum(1 for p in participants if p.acknowledged_at is not None)
        out.append(
            TaskCalendarEventContextResponse(
                event_id=ev.id,
                title=ev.title,
                starts_at=ev.starts_at,
                ends_at=ev.ends_at,
                participants=participants,
                acknowledged_count=acknowledged_count,
                participants_count=len(participants),
            )
        )
    return out


@router.post(
    "/reorder",
    dependencies=[Depends(require_permissions("manage_tasks", "tasks.reprioritize"))],
)
async def reorder_tasks(
    payload: TaskReorderPayload,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> dict:
    _ensure_operation_permission(context, specific="tasks.reprioritize")
    if context.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload("Clinic context is required", "VALIDATION_ERROR"),
        )
    if payload.status not in TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload("Invalid status", "VALIDATION_ERROR", field="status"),
        )
    ids = payload.ordered_task_ids
    # Lock the whole status column inside clinic to avoid rank races on concurrent reorders.
    column_stmt = (
        select(Task)
        .where(
            Task.clinic_id == context.clinic_id,
            Task.status == payload.status,
        )
        .order_by(Task.rank.asc(), Task.created_at.asc())
        .with_for_update()
    )
    column_rows = (await session.execute(column_stmt)).scalars().all()
    if not column_rows:
        return {"status": payload.status, "updated_ranks": []}

    column_by_id = {r.id: r for r in column_rows}
    payload_seen: set[UUID] = set()
    normalized_ids: list[UUID] = []

    for task_id in ids:
        if task_id in payload_seen:
            continue
        payload_seen.add(task_id)
        if task_id in column_by_id:
            normalized_ids.append(task_id)

    # Append all tasks that were not included in client payload,
    # preserving current server order as fallback normalization rule.
    normalized_ids.extend([t.id for t in column_rows if t.id not in payload_seen])

    current_order = [t.id for t in column_rows]
    if normalized_ids == current_order:
        return {"status": payload.status, "updated_ranks": []}

    # Update only changed ranks to reduce write pressure and avoid noisy updates.
    rank_by_id = {task.id: task.rank for task in column_rows}
    updated = []
    service = _get_task_service(session)
    for index, task_id in enumerate(normalized_ids, start=1):
        current_rank = rank_by_id.get(task_id)
        if current_rank == index:
            continue
        await service.update_task_fields(
            task_id=task_id,
            rank=index,
            actor_admin_id=context.user_id,
        )
        session.add(
            TaskStatusTransition(
                clinic_id=context.clinic_id,
                task_id=task_id,
                from_status=payload.status,
                to_status=payload.status,
                reason=f"rank:{current_rank}->{index}",
                actor_admin_id=context.user_id,
                metadata_json={
                    "event": "reorder",
                    "status": payload.status,
                    "rank_from": current_rank,
                    "rank_to": index,
                },
            )
        )
        updated.append({"task_id": str(task_id), "rank": index})
    await session.flush()
    return {"status": payload.status, "updated_ranks": updated}


@router.post(
    "/bulk/status",
    response_model=TaskBulkStatusUpdateResult,
    dependencies=[Depends(require_permissions("manage_tasks", "tasks.bulk_status"))],
)
async def bulk_update_status(
    payload: TaskBulkStatusUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskBulkStatusUpdateResult:
    _ensure_operation_permission(context, specific="tasks.bulk_status")
    if context.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload("Clinic context is required", "VALIDATION_ERROR"),
        )
    service = _get_task_service(session)
    result = TaskBulkStatusUpdateResult(applied=[], rejected=[])
    for task_id in payload.task_ids:
        try:
            task = await service.get_task_details(task_id)
        except LookupError:
            result.rejected.append(
                {"task_id": str(task_id), "code": "NOT_FOUND", "detail": "Task not found"}
            )
            continue
        if task.clinic_id != context.clinic_id:
            result.rejected.append({"task_id": str(task_id), "code": "TENANT_FORBIDDEN", "detail": "Task not found"})
            continue
        limit = WIP_LIMITS.get(payload.to_status)
        if limit is not None and task.status != payload.to_status:
            current_count = len(
                (
                    await session.execute(
                        select(Task).where(
                            Task.clinic_id == context.clinic_id,
                            Task.status == payload.to_status,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if current_count >= limit:
                result.rejected.append(
                    {"task_id": str(task_id), "code": "WIP_LIMIT_EXCEEDED", "detail": "WIP limit exceeded"}
                )
                continue
        try:
            await service.update_task_status(
                task_id=task_id,
                status=payload.to_status,
                completed_at=_utc_now() if payload.to_status == "done" else None,
                actor_admin_id=context.user_id,
                reason=payload.reason,
                metadata={
                    "event": "bulk_status",
                    "to_status": payload.to_status,
                },
            )
            result.applied.append(task_id)
        except ValueError as e:
            result.rejected.append(
                {"task_id": str(task_id), "code": str(e), "detail": "Workflow rule violation"}
            )
    if context.clinic_id is not None:
        c_bucket = clinic_bucket_label(context.clinic_id)
        task_bulk_status_total.labels(
            clinic_bucket=c_bucket, to_status=payload.to_status, outcome="applied"
        ).inc(len(result.applied))
        task_bulk_status_total.labels(
            clinic_bucket=c_bucket, to_status=payload.to_status, outcome="rejected"
        ).inc(len(result.rejected))
    await session.flush()
    return result


@router.post(
    "/{task_id}/calendar-events/{event_id}/invite",
    response_model=TaskCalendarEventContextResponse,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def invite_task_calendar_participants(
    task_id: UUID,
    event_id: UUID,
    payload: TaskCalendarInvitePayload,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskCalendarEventContextResponse:
    _ensure_all_permissions(context, "manage_tasks", "invite_staff_calendar_participants")
    if context.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_payload("Clinic context is required", "VALIDATION_ERROR"),
        )
    service = _get_task_service(session)
    task = await service.get_task_details(task_id)
    if not await _task_visible_to_context(task, context, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    ev_res = await session.execute(
        select(StaffCalendarEvent).where(
            StaffCalendarEvent.id == event_id,
            StaffCalendarEvent.clinic_id == context.clinic_id,
            StaffCalendarEvent.task_id == task_id,
        )
    )
    ev = ev_res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")
    requested_ids = list(dict.fromkeys(payload.admin_ids))
    if requested_ids:
        valid_res = await session.execute(
            select(AdminUser.id).where(
                AdminUser.clinic_id == context.clinic_id,
                AdminUser.deleted_at.is_(None),
                AdminUser.id.in_(requested_ids),
            )
        )
        valid_ids = set(valid_res.scalars().all())
        if valid_ids != set(requested_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_payload("Invalid participants", "VALIDATION_ERROR", field="admin_ids"),
            )
    cur_p_res = await session.execute(
        select(StaffCalendarEventParticipant.admin_id).where(
            StaffCalendarEventParticipant.event_id == event_id
        )
    )
    current_participants = set(cur_p_res.scalars().all())
    cur_inv_res = await session.execute(
        select(StaffCalendarEventInvitation.invitee_admin_id).where(
            StaffCalendarEventInvitation.event_id == event_id
        )
    )
    current_invitees = set(cur_inv_res.scalars().all())
    merged_participants = list(dict.fromkeys([*current_participants, *requested_ids]))
    for aid in merged_participants:
        if aid in current_participants:
            if aid not in current_invitees:
                session.add(
                    StaffCalendarEventInvitation(
                        clinic_id=context.clinic_id,
                        event_id=event_id,
                        invitee_admin_id=aid,
                        acknowledged_at=None,
                    )
                )
            continue
        session.add(StaffCalendarEventParticipant(event_id=event_id, admin_id=aid))
        if aid not in current_invitees:
            session.add(
                StaffCalendarEventInvitation(
                    clinic_id=context.clinic_id,
                    event_id=event_id,
                    invitee_admin_id=aid,
                    acknowledged_at=None,
                )
            )
    if context.user_id is not None and requested_ids:
        await service.add_comment(
            task_id=task_id,
            author_id=context.user_id,
            text=f"Системное событие: приглашены участники в календарный слот ({len(requested_ids)}).",
        )
    await session.flush()
    rows = await get_task_calendar_context(task_id=task_id, session=session, context=context)
    for row in rows:
        if row.event_id == event_id:
            return row
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")

