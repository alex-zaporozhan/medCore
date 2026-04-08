"""Admin API: task streams (semantic context per clinic)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.entitlement_dependencies import require_entitlement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.task_stream_dto import (
    TaskStreamCreate,
    TaskStreamPatch,
    TaskStreamResponse,
    TaskStreamTheme,
    slugify_stream_slug,
)
from src.core.metrics import task_context_admin_events_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.task_stream import TaskStream

router = APIRouter(
    prefix="/admin/task-streams",
    tags=["admin-task-streams"],
    dependencies=[Depends(require_entitlement("tasks.kanban"))],
)


def err_payload(detail: str, code: str, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


@router.get(
    "",
    response_model=list[TaskStreamResponse],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def list_task_streams(
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskStream]:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    stmt = select(TaskStream).where(TaskStream.clinic_id == clinic_id)
    if not include_archived:
        stmt = stmt.where(TaskStream.is_archived.is_(False))
    stmt = stmt.order_by(TaskStream.sort_order.asc(), TaskStream.name.asc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post(
    "",
    response_model=TaskStreamResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def create_task_stream(
    body: TaskStreamCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskStream:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    slug = (body.slug or "").strip().lower() or slugify_stream_slug(body.name)
    if not slug:
        slug = "stream"
    res_max = await session.execute(
        select(func.coalesce(func.max(TaskStream.sort_order), -1)).where(TaskStream.clinic_id == clinic_id)
    )
    next_order = int(res_max.scalar_one() or -1) + 1
    theme_dict = (body.theme or TaskStreamTheme()).to_json_dict()
    row = TaskStream(
        id=uuid4(),
        clinic_id=clinic_id,
        name=body.name.strip(),
        slug=slug[:64],
        sort_order=next_order,
        is_archived=False,
        theme=theme_dict,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=err_payload("Поток с таким slug уже есть", "STREAM_SLUG_CONFLICT", field="slug"),
        ) from None
    await session.refresh(row)
    task_context_admin_events_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        event="stream_created",
    ).inc()
    return row


@router.patch(
    "/{stream_id}",
    response_model=TaskStreamResponse,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def patch_task_stream(
    stream_id: UUID,
    body: TaskStreamPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskStream:
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    res = await session.execute(
        select(TaskStream).where(TaskStream.id == stream_id, TaskStream.clinic_id == clinic_id)
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.theme is not None:
        row.theme = body.theme.to_json_dict()
    if body.is_archived is not None:
        row.is_archived = body.is_archived
    await session.flush()
    await session.refresh(row)
    task_context_admin_events_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        event="stream_patched",
    ).inc()
    return row
