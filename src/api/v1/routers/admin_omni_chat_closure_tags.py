"""Admin API for omni chat closure tags (pragmatic analytics taxonomy)."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.dto.omnichannel_chat_dto import (
    OmniChatClosureTagCreateRequest,
    OmniChatClosureTagDto,
    OmniChatClosureTagsResponse,
    OmniChatClosureTagUpdateRequest,
)
from src.domain.entities.omnichannel_chat_closure import OmniChatClosureTag

router = APIRouter(prefix="/admin/omni-chat-closure-tags", tags=["admin-omni-chat"])


def _require_owner(admin_ctx: AdminContext) -> None:
    # Pragmatic gate: only owners manage taxonomy.
    if "owner" not in set(admin_ctx.roles or set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("", response_model=OmniChatClosureTagsResponse)
async def list_omni_chat_closure_tags(
    include_inactive: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatClosureTagsResponse:
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    stmt = select(OmniChatClosureTag).where(OmniChatClosureTag.clinic_id == clinic_id)
    if not include_inactive:
        stmt = stmt.where(OmniChatClosureTag.is_active.is_(True))
    stmt = stmt.order_by(OmniChatClosureTag.sort_order.asc(), OmniChatClosureTag.title.asc())
    res = await session.execute(stmt)
    items = res.scalars().all()
    return OmniChatClosureTagsResponse(items=[OmniChatClosureTagDto.model_validate(x) for x in items])


@router.post("", response_model=OmniChatClosureTagDto)
async def create_omni_chat_closure_tag(
    body: OmniChatClosureTagCreateRequest,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatClosureTagDto:
    _require_owner(admin_ctx)
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    row = OmniChatClosureTag(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        title=body.title,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    session.add(row)
    await session.flush()
    return OmniChatClosureTagDto.model_validate(row)


@router.patch("/{tag_id}", response_model=OmniChatClosureTagDto)
async def patch_omni_chat_closure_tag(
    tag_id: UUID,
    body: OmniChatClosureTagUpdateRequest,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatClosureTagDto:
    _require_owner(admin_ctx)
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    res = await session.execute(
        select(OmniChatClosureTag).where(OmniChatClosureTag.id == tag_id, OmniChatClosureTag.clinic_id == clinic_id)
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if body.title is not None:
        row.title = body.title
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        row.is_active = body.is_active
    await session.flush()
    return OmniChatClosureTagDto.model_validate(row)

