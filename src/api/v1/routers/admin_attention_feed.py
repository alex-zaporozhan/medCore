"""Admin attention feed API router."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.attention_feed_dto import AttentionFeedRead
from src.application.services.attention_feed_service import AttentionFeedService
from src.application.dto.task_dto import TaskResponse, task_entity_to_response
from src.application.services.task_service import TaskService
from src.domain.entities.task import Task
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.domain.entities.admin_user import AdminUser
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-attention-feed"])


class ClaimItemBody(BaseModel):
    """Body for attention-feed claim. item_id is the entity id (task id, message id, etc.)."""

    item_type: str = Field(..., description="task | follow_up")
    item_id: UUID


def _get_task_service(session: AsyncSession) -> TaskService:
    repo: TaskRepository = TaskRepositoryImpl(session)
    return TaskService(repo)


@router.get(
    "/{clinic_id}/attention-feed",
    response_model=AttentionFeedRead,
)
async def get_attention_feed(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AttentionFeedRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = AttentionFeedService(session)
    return await service.get_feed(clinic_id)


@router.patch(
    "/{clinic_id}/attention-feed/items/claim",
    status_code=status.HTTP_200_OK,
)
async def claim_attention_feed_item(
    clinic_id: UUID,
    body: ClaimItemBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """Assign feed item to current admin (claim). item_type: task | follow_up."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if body.item_type not in ("task", "follow_up"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_type must be task or follow_up",
        )
    service = AttentionFeedService(session)
    ok = await service.claim_item(
        clinic_id=clinic_id,
        item_type=body.item_type,
        item_id=body.item_id,
        admin_id=current_admin.id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await session.commit()
    return {"ok": True}


@router.get(
    "/{clinic_id}/attention-feed/{item_type}/{item_id}/tasks",
    response_model=list[TaskResponse],
)
async def get_tasks_for_attention_item(
    clinic_id: UUID,
    item_type: str,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[TaskResponse]:
    """Return tasks linked to a specific attention item (by kind and underlying id)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if item_type not in ("follow_up", "retention_gap", "conflict"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_type must be follow_up, retention_gap or conflict",
        )
    stmt = (
        select(Task)
        .where(
            Task.clinic_id == clinic_id,
            Task.attention_kind == item_type,
            Task.attention_ref_id == item_id,
        )
        .order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
    )
    result = await session.execute(stmt)
    tasks = result.scalars().unique().all()
    if not tasks:
        return []
    repo = TaskRepositoryImpl(session)
    amap = await repo.list_assignee_ids_for_task_ids([t.id for t in tasks])
    return [task_entity_to_response(t, assignee_ids=amap.get(t.id, [])) for t in tasks]


class CreateTaskFromAttentionBody(BaseModel):
    """Body for creating a task explicitly linked to an attention item from UI."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    assignee_id: UUID | None = None
    role_assignee: str | None = None
    due_at: datetime | None = None


@router.post(
    "/{clinic_id}/attention-feed/{item_type}/{item_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_from_attention_item(
    clinic_id: UUID,
    item_type: str,
    item_id: UUID,
    body: CreateTaskFromAttentionBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TaskResponse:
    """Create a new task linked to a specific attention item."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if item_type not in ("follow_up", "retention_gap", "conflict"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_type must be follow_up, retention_gap or conflict",
        )
    service = _get_task_service(session)
    aids = [body.assignee_id] if body.assignee_id else None
    task = await service.create_task(
        clinic_id=clinic_id,
        title=body.title.strip(),
        description=body.description,
        priority=body.priority,
        creator_id=current_admin.id,
        assignee_id=body.assignee_id,
        assignee_ids=aids,
        role_assignee=body.role_assignee,
        due_at=body.due_at,
        source="from_attention",
        attention_kind=item_type,
        attention_ref_id=item_id,
    )
    repo = TaskRepositoryImpl(session)
    amap = await repo.list_assignee_ids_for_task_ids([task.id])
    return task_entity_to_response(task, assignee_ids=amap.get(task.id, []))


@router.post(
    "/{clinic_id}/attention-feed/follow-up/{message_id}/close",
    status_code=status.HTTP_200_OK,
)
async def close_follow_up_item(
    clinic_id: UUID,
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = AttentionFeedService(session)
    ok = await service.close_follow_up(clinic_id, message_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return {"ok": True}

