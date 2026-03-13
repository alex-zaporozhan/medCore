"""Admin API for omnichannel chats (Phase 3, without AI)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.omnichannel_chat_dto import (
    HideOmniMessageRequest,
    OmniChatDetailDto,
    OmniChatListItemDto,
    OmniChatsResponse,
    OmniMessageDto,
    OmniMessagesResponse,
    SendOmniMessageRequest,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.application.services.omnichannel_outbound_dispatcher import (
    OmnichannelOutboundDispatcher,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/omni-chats", tags=["admin-omni-chat"])


class UpdateOmniChatAiModeRequest(BaseModel):
    ai_mode: str


@router.get("", response_model=OmniChatsResponse)
async def list_omni_chats(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniChatsResponse:
    """List omnichannel chats for admin UI."""
    business_account_id: UUID = current_admin.clinic_id
    skip = (page - 1) * page_size

    # List chats via repository
    service = OmnichannelChatService(session)
    items: list[OmniChat] = await service.chats.list_chats(
        business_account_id=business_account_id,
        status=status_filter,
        search=search,
        skip=skip,
        limit=page_size,
    )

    # Total count for pagination
    total_stmt = select(OmniChat).where(OmniChat.business_account_id == business_account_id)
    if status_filter:
        total_stmt = total_stmt.where(OmniChat.status == status_filter)
    if search:
        ilike_pattern = f"%{search}%"
        total_stmt = total_stmt.where(OmniChat.title.ilike(ilike_pattern))
    total_result = await session.execute(total_stmt)
    total = len(list(total_result.scalars().all()))

    # Fetch contacts for display
    contact_ids = {c.contact_id for c in items}
    contacts_map: dict[UUID, OmniContact] = {}
    if contact_ids:
        contact_rows = await session.execute(
            select(OmniContact).where(OmniContact.id.in_(contact_ids))
        )
        for c in contact_rows.scalars().all():
            contacts_map[c.id] = c

    dto_items: list[OmniChatListItemDto] = []
    for chat in items:
        contact = contacts_map.get(chat.contact_id)
        dto_items.append(
            OmniChatListItemDto(
                chat_id=chat.id,
                contact_id=chat.contact_id,
                contact_name=getattr(contact, "full_name", None),
                contact_primary_phone=getattr(contact, "primary_phone", None),
                status=chat.status,
                last_message_at=chat.last_message_at,
                last_actor_type=chat.last_actor_type,
                ai_mode=chat.ai_mode,
            )
        )

    return OmniChatsResponse(items=dto_items, total=total)


@router.get("/{chat_id}", response_model=OmniChatDetailDto)
async def get_omni_chat(
    chat_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniChatDetailDto:
    """Return single omnichannel chat by id for current business."""
    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    contact = await service.contacts.get_by_id(chat.contact_id)
    channel: OmniChannel | None = None
    if chat.channel_id:
        result = await session.execute(
            select(OmniChannel).where(OmniChannel.id == chat.channel_id).limit(1)
        )
        channel = result.scalar_one_or_none()

    return OmniChatDetailDto(
        chat_id=chat.id,
        contact_id=chat.contact_id,
        contact_name=getattr(contact, "full_name", None) if contact else None,
        contact_primary_phone=getattr(contact, "primary_phone", None) if contact else None,
        channel_id=chat.channel_id,
        channel_type=channel.type if channel else None,
        status=chat.status,
        ai_mode=chat.ai_mode or "DISABLED",
        last_message_at=chat.last_message_at,
        last_actor_type=chat.last_actor_type,
        created_at=chat.created_at,
    )


@router.get("/{chat_id}/messages", response_model=OmniMessagesResponse)
async def get_omni_chat_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    after: UUID | None = Query(None, description="Return messages after this message id (cursor)"),
    before: UUID | None = Query(None, description="Return messages before this message id (cursor)"),
    include_hidden: bool = Query(False, description="Include soft-hidden messages"),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniMessagesResponse:
    """Return messages for given chat (chronological order). Use after/before for cursor pagination."""
    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    messages = await service.list_messages(
        chat_id=chat.id,
        limit=limit,
        after_id=after,
        before_id=before,
        include_hidden=include_hidden,
    )

    # Prefetch channel types for messages to show source per-message
    channel_ids = {m.channel_id for m in messages if getattr(m, "channel_id", None)}
    channels_map: dict[UUID, str] = {}
    if channel_ids:
        channel_rows = await session.execute(
            select(OmniChannel).where(OmniChannel.id.in_(channel_ids))
        )
        for ch in channel_rows.scalars().all():
            channels_map[ch.id] = ch.type

    items = []
    for m in messages:
        channel_type = None
        channel_id = getattr(m, "channel_id", None)
        if channel_id is not None:
            channel_type = channels_map.get(channel_id)
        items.append(
            OmniMessageDto(
                id=m.id,
                direction=m.direction,
                actor_type=m.actor_type,
                content=m.content,
                created_at=m.created_at,
                ui_hidden=getattr(m, "ui_hidden", False),
                hidden_reason=getattr(m, "hidden_reason", None),
                channel_type=channel_type,
            )
        )
    return OmniMessagesResponse(items=items)


@router.post("/{chat_id}/messages", response_model=OmniMessageDto, status_code=status.HTTP_201_CREATED)
async def send_admin_omni_message(
    chat_id: UUID,
    data: SendOmniMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniMessageDto:
    """Append outbound HUMAN_ADMIN message to an omnichannel chat.

    Outbound Dispatcher integration (provider delivery) is handled separately.
    """
    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)
    dispatcher = OmnichannelOutboundDispatcher(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    msg = await service.append_outbound_message(
        chat=chat,
        actor_type="HUMAN_ADMIN",
        content=data.content,
        channel_id=chat.channel_id,
    )

    # Outbound Dispatcher integration (Phase 3 stub)
    await dispatcher.dispatch_to_channel(msg)

    return OmniMessageDto(
        id=msg.id,
        direction=msg.direction,
        actor_type=msg.actor_type,
        content=msg.content,
        created_at=msg.created_at,
    )


@router.post("/{chat_id}/ai-mode", status_code=status.HTTP_204_NO_CONTENT)
async def update_omni_chat_ai_mode(
    chat_id: UUID,
    body: UpdateOmniChatAiModeRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    """Update ai_mode for specific omnichannel chat (FAST toggle in admin UI)."""
    from src.application.services.omnichannel_ai_settings_service import (
        OmnichannelAISettingsService,
    )

    allowed_modes = {"AUTO_REPLY", "SUGGEST_ONLY", "DISABLED"}
    mode = body.ai_mode.upper()
    if mode not in allowed_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ai_mode",
        )

    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Persist on chat entity for quick filtering in UI
    chat.ai_mode = mode

    # Also persist in omni_ai_settings as CHAT scope so orchestrator picks it up
    settings_svc = OmnichannelAISettingsService(session)
    await settings_svc.upsert_settings(
        scope="CHAT",
        scope_id=chat.id,
        data={"ai_mode": mode},
    )
    await session.flush()


@router.post("/{chat_id}/messages/{message_id}/hide", status_code=status.HTTP_204_NO_CONTENT)
async def hide_omni_message(
    chat_id: UUID,
    message_id: UUID,
    body: HideOmniMessageRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    """Soft-hide a message in omnichannel chat with AuditLog entry."""
    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    result = await session.execute(
        select(OmniMessage).where(
            OmniMessage.id == message_id,
            OmniMessage.chat_id == chat.id,
        )
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    await service.soft_hide_message(
        business_account_id=business_account_id,
        message=message,
        reason=body.reason,
        actor_id=current_admin.id,
        actor_type="ADMIN",
        ip_address=ip,
        user_agent=ua,
    )

