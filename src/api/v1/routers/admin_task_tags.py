"""Admin API: task tag definitions (clinic-scoped labels)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.task_stream_dto import TaskTagCreate, TaskTagPatch, TaskTagResponse
from src.core.metrics import task_context_admin_events_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.task_tag_definition import TaskTagDefinition

router = APIRouter(prefix="/admin/task-tags", tags=["admin-task-tags"])


def err_payload(detail: str, code: str, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


@router.get(
    "",
    response_model=list[TaskTagResponse],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def list_task_tags(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskTagDefinition]:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    res = await session.execute(
        select(TaskTagDefinition)
        .where(TaskTagDefinition.clinic_id == clinic_id)
        .order_by(TaskTagDefinition.name.asc())
    )
    return list(res.scalars().all())


@router.post(
    "",
    response_model=TaskTagResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def create_task_tag(
    body: TaskTagCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskTagDefinition:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    name = body.name.strip()
    row = TaskTagDefinition(
        id=uuid4(),
        clinic_id=clinic_id,
        name=name,
        color=body.color.strip() if body.color else None,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=err_payload("Тег с таким именем уже есть", "TAG_NAME_CONFLICT", field="name"),
        ) from None
    await session.refresh(row)
    task_context_admin_events_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        event="tag_created",
    ).inc()
    return row


@router.patch(
    "/{tag_id}",
    response_model=TaskTagResponse,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def patch_task_tag(
    tag_id: UUID,
    body: TaskTagPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskTagDefinition:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    res = await session.execute(
        select(TaskTagDefinition).where(
            TaskTagDefinition.id == tag_id,
            TaskTagDefinition.clinic_id == clinic_id,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.color is not None:
        row.color = body.color.strip() if body.color.strip() else None
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=err_payload("Тег с таким именем уже есть", "TAG_NAME_CONFLICT", field="name"),
        ) from None
    await session.refresh(row)
    return row
