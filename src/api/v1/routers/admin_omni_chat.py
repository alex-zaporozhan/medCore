"""Admin API for omnichannel chats (Phase 3, without AI)."""

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.chat_attachment_disposition import clinic_chat_attachment_content_disposition
from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin, get_current_admin_sse
from src.core.config import settings
from src.core.context import RequestContext
from src.application.dto.omnichannel_chat_dto import (
    HideOmniMessageRequest,
    OmniChatDetailDto,
    OmniChatListItemDto,
    OmniChatsResponse,
    OmniMessageAttachmentDto,
    OmniMessageDto,
    OmniMessagesResponse,
    OmniQuickReplyCreateRequest,
    OmniQuickReplyDto,
    OmniQuickRepliesResponse,
    OmniQuickReplyUpdateRequest,
    PatchOmniChatRequest,
    SendOmniMessageRequest,
)
from src.application.services.omni_outbound_policy import resolve_reply_channel_id_for_admin
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.application.services.lead_service import LeadService
from src.application.services.omnichannel_outbound_dispatcher import (
    OmnichannelOutboundDispatcher,
)
from src.application.services.omni_media_storage import (
    CLINIC_CHAT_BRIDGE_META_KEY,
    OMNI_FILES_META_KEY,
    allowed_omni_upload_mime,
    find_omni_file_meta,
    read_omni_file_bytes,
    save_omni_upload,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omni_quick_reply import OmniQuickReply
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.infrastructure.realtime.omni_pubsub import OMNI_EVENTS_CHANNEL_PREFIX

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/omni-chats", tags=["admin-omni-chat"])


def _attachments_from_omni_entity(m: OmniMessage) -> list[OmniMessageAttachmentDto]:
    out: list[OmniMessageAttachmentDto] = []
    raw = getattr(m, "source_metadata", None)
    if not isinstance(raw, dict):
        return out
    files = raw.get(OMNI_FILES_META_KEY)
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            try:
                aid = UUID(str(item["id"]))
            except (KeyError, ValueError, TypeError):
                continue
            out.append(
                OmniMessageAttachmentDto(
                    id=aid,
                    file_name=str(item.get("file_name") or "file")[:500],
                    content_type=str(item.get("content_type") or "application/octet-stream")[:128],
                    size_bytes=int(item.get("size_bytes") or 0),
                    source="omni",
                )
            )
    bridge = raw.get(CLINIC_CHAT_BRIDGE_META_KEY)
    if isinstance(bridge, dict):
        conv_raw = bridge.get("conversation_id")
        conv_id: UUID | None
        try:
            conv_id = UUID(str(conv_raw)) if conv_raw else None
        except (ValueError, TypeError):
            conv_id = None
        for item in bridge.get("attachments") or []:
            if not isinstance(item, dict):
                continue
            try:
                aid = UUID(str(item["id"]))
            except (KeyError, ValueError, TypeError):
                continue
            out.append(
                OmniMessageAttachmentDto(
                    id=aid,
                    file_name=str(item.get("file_name") or "file")[:500],
                    content_type=str(item.get("content_type") or "application/octet-stream")[:128],
                    size_bytes=int(item.get("size_bytes") or 0),
                    source="clinic_chat",
                    conversation_id=conv_id,
                )
            )
    return out


def _omni_message_to_dto(
    m: OmniMessage,
    channels_map: dict[UUID, str],
) -> OmniMessageDto:
    channel_id = getattr(m, "channel_id", None)
    channel_type = channels_map.get(channel_id) if channel_id is not None else None
    raw_meta = getattr(m, "source_metadata", None)
    delivery_status = None
    read_status = None
    if isinstance(raw_meta, dict):
        raw_delivery = raw_meta.get("delivery_status")
        raw_read = raw_meta.get("read_status")
        if raw_delivery is not None:
            delivery_status = str(raw_delivery)
        if raw_read is not None:
            read_status = str(raw_read)
    return OmniMessageDto(
        id=m.id,
        direction=m.direction,
        actor_type=m.actor_type,
        content=m.content,
        message_content_type=(getattr(m, "content_type", None) or "TEXT")[:32],
        attachments=_attachments_from_omni_entity(m),
        created_at=m.created_at,
        ui_hidden=getattr(m, "ui_hidden", False),
        hidden_reason=getattr(m, "hidden_reason", None),
        channel_id=channel_id,
        channel_type=channel_type,
        sender_admin_id=getattr(m, "sender_admin_id", None),
        delivery_status=delivery_status,
        read_status=read_status,
    )


async def _admin_display_names(session: AsyncSession, admin_ids: set[UUID]) -> dict[UUID, str]:
    if not admin_ids:
        return {}
    result = await session.execute(select(AdminUser).where(AdminUser.id.in_(admin_ids)))
    out: dict[UUID, str] = {}
    for u in result.scalars().all():
        label = (u.full_name or u.email or str(u.id))[:120]
        out[u.id] = label
    return out


class UpdateOmniChatAiModeRequest(BaseModel):
    ai_mode: str


@router.get("/events")
async def omni_chat_event_stream(
    current_admin: AdminUser = Depends(get_current_admin_sse),
) -> StreamingResponse:
    """SSE: `message.created` for current clinic (no message body). ARCH §6."""
    clinic_id = current_admin.clinic_id
    channel = f"{OMNI_EVENTS_CHANNEL_PREFIX}:{clinic_id}"

    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield ": connected\n\n"
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=25.0)
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    if isinstance(data, str):
                        yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception as e:
                logger.debug("omni SSE pubsub close", extra={"error": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/quick-replies", response_model=OmniQuickRepliesResponse)
async def list_omni_quick_replies(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniQuickRepliesResponse:
    """Quick reply templates for composer (read: any admin with inbox access)."""
    clinic_id = current_admin.clinic_id
    result = await session.execute(
        select(OmniQuickReply)
        .where(OmniQuickReply.clinic_id == clinic_id)
        .order_by(OmniQuickReply.sort_order.asc(), OmniQuickReply.created_at.asc())
    )
    rows = list(result.scalars().all())
    items = [
        OmniQuickReplyDto(
            id=r.id,
            clinic_id=r.clinic_id,
            title=r.title,
            body=r.body,
            sort_order=r.sort_order,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return OmniQuickRepliesResponse(items=items)


@router.post("/quick-replies", response_model=OmniQuickReplyDto, status_code=status.HTTP_201_CREATED)
async def create_omni_quick_reply(
    body: OmniQuickReplyCreateRequest,
    session: AsyncSession = Depends(get_session),
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniQuickReplyDto:
    clinic_id = _admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    row = OmniQuickReply(
        clinic_id=clinic_id,
        title=body.title.strip(),
        body=body.body.strip(),
        sort_order=body.sort_order,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return OmniQuickReplyDto(
        id=row.id,
        clinic_id=row.clinic_id,
        title=row.title,
        body=row.body,
        sort_order=row.sort_order,
        created_at=row.created_at,
    )


@router.patch("/quick-replies/{reply_id}", response_model=OmniQuickReplyDto)
async def update_omni_quick_reply(
    reply_id: UUID,
    body: OmniQuickReplyUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniQuickReplyDto:
    clinic_id = _admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    result = await session.execute(
        select(OmniQuickReply).where(OmniQuickReply.id == reply_id, OmniQuickReply.clinic_id == clinic_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found")
    if body.title is not None:
        row.title = body.title.strip()
    if body.body is not None:
        row.body = body.body.strip()
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    await session.flush()
    await session.refresh(row)
    return OmniQuickReplyDto(
        id=row.id,
        clinic_id=row.clinic_id,
        title=row.title,
        body=row.body,
        sort_order=row.sort_order,
        created_at=row.created_at,
    )


@router.delete("/quick-replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_omni_quick_reply(
    reply_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> None:
    clinic_id = _admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    result = await session.execute(
        select(OmniQuickReply).where(OmniQuickReply.id == reply_id, OmniQuickReply.clinic_id == clinic_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found")
    await session.delete(row)


@router.get("", response_model=OmniChatsResponse)
async def list_omni_chats(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    assignee: str | None = Query(None, description='Use "me" for chats assigned to current admin'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniChatsResponse:
    """List omnichannel chats for admin UI."""
    business_account_id: UUID = current_admin.clinic_id
    skip = (page - 1) * page_size

    assignee_admin_id: UUID | None = None
    if assignee is not None:
        if assignee.strip().lower() != "me":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="assignee must be exactly 'me' when provided",
            )
        assignee_admin_id = current_admin.id

    # List chats via repository
    service = OmnichannelChatService(session)
    items: list[OmniChat] = await service.chats.list_chats(
        business_account_id=business_account_id,
        status=status_filter,
        search=search,
        skip=skip,
        limit=page_size,
        assignee_admin_id=assignee_admin_id,
    )

    # Total count for pagination
    total_stmt = select(func.count()).select_from(OmniChat).where(OmniChat.business_account_id == business_account_id)
    if assignee_admin_id is not None:
        total_stmt = total_stmt.where(OmniChat.assignee_admin_id == assignee_admin_id)
    if status_filter:
        total_stmt = total_stmt.where(OmniChat.status == status_filter)
    if search:
        ilike_pattern = f"%{search}%"
        total_stmt = total_stmt.where(OmniChat.title.ilike(ilike_pattern))
    total_result = await session.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)

    # Fetch contacts for display
    contact_ids = {c.contact_id for c in items}
    contacts_map: dict[UUID, OmniContact] = {}
    if contact_ids:
        contact_rows = await session.execute(
            select(OmniContact).where(OmniContact.id.in_(contact_ids))
        )
        for c in contact_rows.scalars().all():
            contacts_map[c.id] = c

    assignee_ids: set[UUID] = set()
    for c in items:
        aid = getattr(c, "assignee_admin_id", None)
        if aid:
            assignee_ids.add(aid)
    assignee_names = await _admin_display_names(session, assignee_ids)

    dto_items: list[OmniChatListItemDto] = []
    for chat in items:
        contact = contacts_map.get(chat.contact_id)
        aid = getattr(chat, "assignee_admin_id", None)
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
                assignee_admin_id=aid,
                assignee_name=assignee_names.get(aid) if aid else None,
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

    # Optional CRM lead snapshot for this contact
    lead_id = None
    lead_stage_id = None
    lead_stage_name = None
    lead_estimated_value = None
    lead_actual_value = None
    try:
        lead_service = LeadService(session)
        lead = await lead_service.repository.find_open_lead_for_contact_or_patient(
            clinic_id=business_account_id,
            omnichannel_contact_id=chat.contact_id,
            patient_id=None,
        )
        if lead:
            lead_id = lead.id
            lead_stage_id = lead.stage_id
            # We need stage name; fetch minimal info
            stage = await lead_service.repository.get_stage_by_id(
                clinic_id=business_account_id,
                stage_id=lead.stage_id,
            )
            lead_stage_name = stage.name if stage else None
            lead_estimated_value = str(lead.estimated_value)
            lead_actual_value = str(lead.actual_value)
    except Exception as e:
        logger.warning(
            "[CRM] Failed to enrich OmniChat detail with lead info",
            extra={"error": str(e), "chat_id": str(chat.id)},
        )

    assignee_admin_id = getattr(chat, "assignee_admin_id", None)
    assignee_name_detail = None
    if assignee_admin_id:
        an = await _admin_display_names(session, {assignee_admin_id})
        assignee_name_detail = an.get(assignee_admin_id)

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
        lead_id=lead_id,
        lead_stage_id=lead_stage_id,
        lead_stage_name=lead_stage_name,
        lead_estimated_value=lead_estimated_value,
        lead_actual_value=lead_actual_value,
        assignee_admin_id=assignee_admin_id,
        assignee_name=assignee_name_detail,
    )


@router.patch("/{chat_id}", response_model=OmniChatDetailDto)
async def patch_omni_chat(
    chat_id: UUID,
    body: PatchOmniChatRequest,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatDetailDto:
    """Assign dialog to an admin and/or change status (P1-B)."""
    business_account_id = admin_ctx.clinic_id
    if business_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется контекст клиники",
        )
    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    if body.assignee_admin_id is not None:
        if body.assignee_admin_id:
            res = await session.execute(
                select(AdminUser).where(
                    AdminUser.id == body.assignee_admin_id,
                    AdminUser.clinic_id == business_account_id,
                    AdminUser.deleted_at.is_(None),
                )
            )
            if res.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="assignee_admin_id is not a valid admin for this clinic",
                )
        chat.assignee_admin_id = body.assignee_admin_id
    if body.status is not None:
        chat.status = body.status
    await session.flush()

    admin_result = await session.execute(select(AdminUser).where(AdminUser.id == admin_ctx.user_id))
    admin_user = admin_result.scalar_one_or_none()
    if admin_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return await get_omni_chat(chat_id, session, admin_user)


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

    items = [_omni_message_to_dto(m, channels_map) for m in messages]
    return OmniMessagesResponse(items=items)


@router.post(
    "/{chat_id}/messages",
    response_model=OmniMessageDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid reply_channel_id or channel does not support outbound"},
        404: {"description": "Chat not found"},
        409: {"description": "Reply channel could not be resolved (OMNI_REPLY_CHANNEL_UNRESOLVED)"},
        429: {"description": "Outbound send rate limit (per admin, default 30/min)"},
    },
)
async def send_admin_omni_message(
    chat_id: UUID,
    data: SendOmniMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    rate_limiter=Depends(get_rate_limiter),
) -> OmniMessageDto:
    """Append outbound HUMAN_ADMIN message to an omnichannel chat (OutboundPolicy §3)."""
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:omni:send:admin:{current_admin.id}",
            limit=settings.rate_admin_omni_send_per_admin_limit,
            window=settings.rate_admin_omni_send_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "OMNI_SEND_RATE_LIMITED",
                "message": "Слишком много исходящих сообщений. Подождите и повторите.",
            },
        ) from None

    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)
    dispatcher = OmnichannelOutboundDispatcher(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    resolved_channel_id = await resolve_reply_channel_id_for_admin(
        session,
        clinic_id=business_account_id,
        chat=chat,
        reply_channel_id=data.reply_channel_id,
    )

    msg = await service.append_outbound_message(
        chat=chat,
        actor_type="HUMAN_ADMIN",
        content=data.content,
        channel_id=resolved_channel_id,
        sender_admin_id=current_admin.id,
    )

    await dispatcher.dispatch_to_channel(msg)

    ch_res = await session.execute(
        select(OmniChannel).where(OmniChannel.id == resolved_channel_id).limit(1)
    )
    resolved_row = ch_res.scalar_one_or_none()
    channels_map: dict[UUID, str] = {}
    if resolved_row:
        channels_map[resolved_row.id] = resolved_row.type

    return _omni_message_to_dto(msg, channels_map)


@router.post(
    "/{chat_id}/messages/upload",
    response_model=OmniMessageDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid file type or empty file"},
        404: {"description": "Chat not found"},
        413: {"description": "File too large"},
        429: {"description": "Rate limit"},
    },
)
async def send_admin_omni_message_upload(
    chat_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    rate_limiter=Depends(get_rate_limiter),
    body: str = Form(""),
    file: UploadFile = File(...),
    reply_channel_id: str | None = Form(None),
) -> OmniMessageDto:
    """Исходящее сообщение с файлом (изображение, документ, аудио) в omnichannel."""
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:omni:send:admin:{current_admin.id}",
            limit=settings.rate_admin_omni_send_per_admin_limit,
            window=settings.rate_admin_omni_send_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "OMNI_SEND_RATE_LIMITED",
                "message": "Слишком много исходящих сообщений. Подождите и повторите.",
            },
        ) from None

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")
    if len(raw) > settings.staff_chat_max_attachment_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip()
    if not allowed_omni_upload_mime(ct):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый тип файла для omnichannel",
        )

    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)
    dispatcher = OmnichannelOutboundDispatcher(session)

    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    rid: UUID | None = None
    if reply_channel_id and reply_channel_id.strip():
        try:
            rid = UUID(reply_channel_id.strip())
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid reply_channel_id",
            ) from e

    resolved_channel_id = await resolve_reply_channel_id_for_admin(
        session,
        clinic_id=business_account_id,
        chat=chat,
        reply_channel_id=rid,
    )

    # Подпись опциональна; вложение в meta — без плейсхолдеров в тексте.
    caption = (body or "").strip()[:2000]

    att_id = uuid.uuid4()
    rel = save_omni_upload(
        business_account_id,
        att_id,
        file.filename or "file",
        raw,
    )
    meta = {
        OMNI_FILES_META_KEY: [
            {
                "id": str(att_id),
                "file_name": (file.filename or "file")[:500],
                "content_type": ct[:128],
                "size_bytes": len(raw),
                "storage_rel": rel,
            }
        ]
    }

    msg = await service.append_outbound_message(
        chat=chat,
        actor_type="HUMAN_ADMIN",
        content=caption,
        channel_id=resolved_channel_id,
        sender_admin_id=current_admin.id,
        source_metadata=meta,
        content_type="MEDIA",
    )

    await dispatcher.dispatch_to_channel(msg)

    ch_res = await session.execute(
        select(OmniChannel).where(OmniChannel.id == resolved_channel_id).limit(1)
    )
    resolved_row = ch_res.scalar_one_or_none()
    channels_map: dict[UUID, str] = {}
    if resolved_row:
        channels_map[resolved_row.id] = resolved_row.type

    return _omni_message_to_dto(msg, channels_map)


@router.get("/{chat_id}/messages/{message_id}/attachments/{attachment_id}/file")
async def download_omni_message_attachment(
    chat_id: UUID,
    message_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    request_context: RequestContext = Depends(get_request_context),
) -> Response:
    """Скачать файл, прикреплённый к исходящему/внутреннему omni-сообщению (не для моста PWA)."""
    business_account_id: UUID = current_admin.clinic_id
    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(business_account_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    msg = await session.get(OmniMessage, message_id)
    if msg is None or msg.chat_id != chat.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    meta = find_omni_file_meta(getattr(msg, "source_metadata", None), attachment_id)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    rel = meta.get("storage_rel")
    if not rel or not isinstance(rel, str):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    payload = read_omni_file_bytes(rel)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")

    fname = str(meta.get("file_name") or "file")
    media_type = str(meta.get("content_type") or "application/octet-stream")
    if media_type.lower().startswith("audio/"):
        allow_audio = request_context.user_type == "admin" and "owner" in request_context.roles
        disp = clinic_chat_attachment_content_disposition(
            media_type,
            fname,
            allow_audio_as_attachment=allow_audio,
        )
    else:
        disp = f'inline; filename="{fname.replace(chr(34), chr(39))[:200]}"'
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": disp},
    )


@router.post("/{chat_id}/ai-mode", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
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


@router.post("/{chat_id}/messages/{message_id}/hide", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
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

