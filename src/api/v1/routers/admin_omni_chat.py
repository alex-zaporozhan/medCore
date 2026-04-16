"""Admin API for omnichannel chats (Phase 3, without AI)."""

import logging
import uuid
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.chat_attachment_disposition import clinic_chat_attachment_content_disposition
from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin, get_current_admin_sse
from src.core.config import settings
from src.core.security import create_access_token
from src.core.context import RequestContext
from src.application.dto.omnichannel_chat_dto import (
    CloseOmniChatRequest,
    HideOmniMessageRequest,
    OmniChatClaimResponse,
    OmniChatCloseResponse,
    OmniChatDetailDto,
    OmniChatListItemDto,
    OmniChatsResponse,
    OmniChatAnalyticsResponse,
    OmniChatAdminStatDto,
    OmniChatOutcomeStatDto,
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
from src.application.services.rbac_service import RbacServiceImpl
from src.infrastructure.database import base as db_base
from src.infrastructure.database.rbac_repo_impl import RbacRepositoryImpl
from src.domain.entities.omnichannel_chat_closure import (
    OmniChatClosure,
    OmniChatClosureTag,
    OmniChatClosureTagLink,
)
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omni_lead_log import OmniLeadLog
from src.domain.entities.omni_chat_lease import OmniChatLease
from src.domain.entities.omni_chat_presence_event import OmniChatPresenceEvent
from src.domain.entities.omni_quick_reply import OmniQuickReply
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.domain.entities.task_stream import TaskStream
from src.domain.entities.task import Task
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_log_routing_rule import LeadLogRoutingRule
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.infrastructure.realtime.omni_pubsub import OMNI_EVENTS_CHANNEL_PREFIX, publish_omni_chat_updated
from src.application.dto.omni_resolve_dto import OmniChatResolveResponseDto
from src.application.dto.omni_presence_dto import (
    OmniChatLeaseDto,
    OmniChatPresenceRequest,
    OmniChatPresenceResponse,
)
from src.core.metrics import (
    omni_auto_claim_conflicts_total,
    omni_auto_claim_total,
    omni_auto_resolve_attempts_total,
    omni_active_leases,
    omni_lead_logs_resolved_total,
    omni_lead_logs_resolve_errors_total,
    omni_lead_logs_transcript_bytes,
    omni_lease_duration_seconds,
    omni_presence_events_total,
    omni_presence_idempotent_replays_total,
    omni_time_to_first_outbound_seconds,
    lead_log_routing_fallback_total,
    lead_log_routing_matches_total,
)
from src.core.prometheus_labels import clinic_bucket_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/omni-chats", tags=["admin-omni-chat"])

_OMNI_AUTO_RESOLVE_IDLE_SECONDS = 60 * 10  # 10 minutes: pragmatic, safe default for MVP

def _err(code: str, message: str, *, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def _require_owner_reports(admin_ctx: AdminContext) -> None:
    if "erp.owner_reports.read" not in set(admin_ctx.permissions or set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


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


class OmniChatSseTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int


@router.get("/sse-token", response_model=OmniChatSseTokenResponse)
async def issue_omni_chat_sse_token(
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatSseTokenResponse:
    """Issue short-lived JWT for EventSource query param (reduces leakage risk of long-lived admin JWT)."""
    admin_id = admin_ctx.user_id
    if admin_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    ttl = 300
    token = create_access_token({"type": "admin", "sub": str(admin_id)}, expires_delta=timedelta(seconds=ttl))
    return OmniChatSseTokenResponse(token=token, expires_in_seconds=ttl)


@router.get("/events")
async def omni_chat_event_stream(
    current_admin: AdminUser = Depends(get_current_admin_sse),
) -> StreamingResponse:
    """SSE: `message.created` for current clinic (no message body). ARCH §6."""
    clinic_id = current_admin.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    # RBAC for SSE: EventSource может передавать токен в query и не попадает в require_permissions().
    # Поэтому проверяем права вручную через RBAC сервис.
    # Short-lived session only — do not use Depends(get_session): it stays open for the whole stream.
    async with db_base.AsyncSessionLocal() as session:
        rbac = RbacServiceImpl(RbacRepositoryImpl(session))
        perms = await rbac.get_permissions_for_user(current_admin.id, clinic_id)
    if "omni.inbox.manage" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    channel = f"{OMNI_EVENTS_CHANNEL_PREFIX}:{clinic_id}"

    async def event_generator():
        # Yield immediately so clients see bytes before Redis subscribe (same event loop as ASGI tests).
        yield ": connected\n\n"
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
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
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniQuickRepliesResponse:
    """Quick reply templates for composer (read: any admin with inbox access)."""
    clinic_id = admin_ctx.clinic_id
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
    channel_type: str | None = Query(None, description="Filter chats by channel type (legacy single; e.g. TELEGRAM_BOT)"),
    channel_types: list[str] | None = Query(None, description="Filter chats by channel types (repeatable)."),
    assignee: str | None = Query(None, description='Use "me" for chats assigned to current admin; "unassigned" for inbox'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatsResponse:
    """List omnichannel chats for admin UI."""
    business_account_id: UUID | None = admin_ctx.clinic_id
    admin_id: UUID | None = admin_ctx.user_id
    if business_account_id is None or admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    skip = (page - 1) * page_size

    assignee_admin_id: UUID | None = None
    assignee_unassigned_only = False
    if assignee is not None:
        normalized_assignee = assignee.strip().lower()
        if normalized_assignee not in {"me", "unassigned"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "omni_assignee_invalid", "message": "assignee must be exactly 'me' when provided"},
            )
        if normalized_assignee == "me":
            assignee_admin_id = admin_id
        else:
            assignee_unassigned_only = True

    # List chats via repository
    service = OmnichannelChatService(session)

    normalized_channel_types: list[str] | None = None
    raw_types: list[str] = []
    if channel_types:
        raw_types.extend(channel_types)
    elif channel_type:
        raw_types.append(channel_type)
    if raw_types:
        cleaned: list[str] = []
        for t in raw_types:
            tt = (t or "").strip().upper()
            if not tt:
                continue
            if len(tt) > 32:
                raise _err(
                    "omni_channel_type_invalid",
                    "channel_type слишком длинный",
                    http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            cleaned.append(tt)
        normalized_channel_types = sorted(set(cleaned)) if cleaned else None

    items: list[OmniChat] = await service.chats.list_chats(
        business_account_id=business_account_id,
        status=status_filter,
        search=search,
        channel_types=normalized_channel_types,
        skip=skip,
        limit=page_size,
        assignee_admin_id=assignee_admin_id,
        unassigned_only=assignee_unassigned_only,
    )

    # Total count for pagination
    total_stmt = select(func.count()).select_from(OmniChat).where(OmniChat.business_account_id == business_account_id)
    if normalized_channel_types:
        msg_has_any_type = (
            select(1)
            .select_from(OmniMessage)
            .join(OmniChannel, OmniMessage.channel_id == OmniChannel.id)
            .where(
                OmniMessage.chat_id == OmniChat.id,
                OmniChannel.type.in_(normalized_channel_types),
                OmniChannel.business_account_id == business_account_id,
            )
            .limit(1)
        )
        total_stmt = total_stmt.where(exists(msg_has_any_type))
    if assignee_admin_id is not None:
        total_stmt = total_stmt.where(OmniChat.assignee_admin_id == assignee_admin_id)
    if assignee_unassigned_only:
        total_stmt = total_stmt.where(OmniChat.assignee_admin_id.is_(None))
    if status_filter:
        total_stmt = total_stmt.where(OmniChat.status == status_filter)
    if search:
        ilike_pattern = f"%{search}%"
        total_stmt = total_stmt.join(OmniContact, OmniChat.contact_id == OmniContact.id)
        total_stmt = total_stmt.where(
            or_(
                OmniChat.title.ilike(ilike_pattern),
                OmniContact.full_name.ilike(ilike_pattern),
                OmniContact.primary_phone.ilike(ilike_pattern),
            )
        )
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

    # Fetch channels to expose channel_type in chat list (for enterprise filters)
    primary_channel_ids = {getattr(c, "channel_id", None) for c in items if getattr(c, "channel_id", None)}
    primary_channels_map: dict[UUID, OmniChannel] = {}
    if primary_channel_ids:
        channel_rows = await session.execute(select(OmniChannel).where(OmniChannel.id.in_(primary_channel_ids)))
        for ch in channel_rows.scalars().all():
            primary_channels_map[ch.id] = ch

    chat_ids = [c.id for c in items]
    chat_channel_types_map: dict[UUID, set[str]] = {}
    if chat_ids:
        rows = await session.execute(
            select(OmniMessage.chat_id, OmniChannel.type)
            .select_from(OmniMessage)
            .join(OmniChannel, OmniMessage.channel_id == OmniChannel.id)
            .where(
                OmniMessage.chat_id.in_(chat_ids),
                OmniChannel.business_account_id == business_account_id,
            )
        )
        for chat_id, t in rows.all():
            if chat_id not in chat_channel_types_map:
                chat_channel_types_map[chat_id] = set()
            if t:
                chat_channel_types_map[chat_id].add(str(t))

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
        ch = primary_channels_map.get(getattr(chat, "channel_id", None))
        channel_types_list = sorted(chat_channel_types_map.get(chat.id, set()))
        status_upper = str(getattr(chat, "status", "") or "").upper()
        last_actor_upper = str(getattr(chat, "last_actor_type", "") or "").upper()
        needs_attention = False
        if status_upper != "CLOSED":
            if aid is None and status_upper == "WAITING_FOR_OPERATOR":
                needs_attention = True
            elif aid == admin_id and last_actor_upper in {"CONTACT", "CLIENT", "PATIENT"}:
                needs_attention = True
        dto_items.append(
            OmniChatListItemDto(
                chat_id=chat.id,
                contact_id=chat.contact_id,
                contact_name=getattr(contact, "full_name", None),
                contact_primary_phone=getattr(contact, "primary_phone", None),
                channel_id=getattr(chat, "channel_id", None),
                channel_type=ch.type if ch else None,
                channel_types=channel_types_list,
                status=chat.status,
                last_message_at=chat.last_message_at,
                last_actor_type=chat.last_actor_type,
                ai_mode=chat.ai_mode,
                assignee_admin_id=aid,
                assignee_name=assignee_names.get(aid) if aid else None,
                needs_attention=needs_attention,
            )
        )

    return OmniChatsResponse(items=dto_items, total=total)


@router.post("/{chat_id}/claim", response_model=OmniChatClaimResponse)
async def claim_omni_chat(
    chat_id: UUID,
    force: bool = Query(False, description="Owner-only: reassign chat currently owned by another operator"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatClaimResponse:
    """Assign chat to current admin (idempotent)."""
    clinic_id = admin_ctx.clinic_id
    admin_id = admin_ctx.user_id
    if clinic_id is None or admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(clinic_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    assignee_conflict = bool(chat.assignee_admin_id and chat.assignee_admin_id != admin_id)
    if assignee_conflict and not (force and "owner" in (admin_ctx.roles or set())):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "omni_chat_already_claimed", "message": "Chat already claimed by another admin"},
        )

    now = datetime.utcnow()
    if chat.assignee_admin_id is None:
        chat.assignee_admin_id = admin_id
        if getattr(chat, "claimed_at", None) is None:
            chat.claimed_at = now
    elif assignee_conflict and force:
        chat.assignee_admin_id = admin_id
        chat.claimed_at = now

    if chat.status in {"OPEN", "WAITING_FOR_OPERATOR"}:
        chat.status = "IN_PROGRESS"
    await session.flush()
    await publish_omni_chat_updated(clinic_id=clinic_id, chat_id=chat.id, reason="claim")

    detail = await _build_omni_chat_detail_dto(session, admin_ctx, chat_id)
    return OmniChatClaimResponse(chat=detail)


@router.post("/{chat_id}/presence", response_model=OmniChatPresenceResponse)
async def omni_chat_presence(
    chat_id: UUID,
    body: OmniChatPresenceRequest,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatPresenceResponse:
    """Presence/lease events for no-buttons automation (idempotent per client_event_id)."""
    clinic_id = admin_ctx.clinic_id
    admin_id = admin_ctx.user_id
    if clinic_id is None or admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    # Validate chat belongs to clinic (strict tenant isolation).
    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(clinic_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    # Idempotency: once per (clinic_id, client_event_id).
    existing_evt = await session.execute(
        select(OmniChatPresenceEvent).where(
            OmniChatPresenceEvent.clinic_id == clinic_id,
            OmniChatPresenceEvent.client_event_id == body.client_event_id,
        )
    )
    if existing_evt.scalar_one_or_none() is not None:
        omni_presence_idempotent_replays_total.labels(clinic_bucket=clinic_bucket_label(clinic_id)).inc()
        lease_row = None
        # Best-effort: return current active lease for this tab if exists and not expired.
        now = datetime.utcnow()
        lease_res = await session.execute(
            select(OmniChatLease)
            .where(
                OmniChatLease.clinic_id == clinic_id,
                OmniChatLease.chat_id == chat.id,
                OmniChatLease.admin_id == admin_id,
                OmniChatLease.tab_id == body.tab_id,
                OmniChatLease.expires_at > now,
            )
            .order_by(OmniChatLease.expires_at.desc())
            .limit(1)
        )
        lease_row = lease_res.scalar_one_or_none()
        lease_dto = (
            OmniChatLeaseDto(
                chat_id=lease_row.chat_id,
                admin_id=lease_row.admin_id,
                tab_id=lease_row.tab_id,
                expires_at=lease_row.expires_at,
                last_heartbeat_at=lease_row.last_heartbeat_at,
            )
            if lease_row
            else None
        )
        return OmniChatPresenceResponse(
            lease=lease_dto,
            claimed=bool(chat.assignee_admin_id == admin_id),
            assignee_admin_id=chat.assignee_admin_id,
        )

    now = datetime.utcnow()
    omni_presence_events_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id), event=str(body.event or "UNKNOWN")
    ).inc()
    session.add(
        OmniChatPresenceEvent(
            clinic_id=clinic_id,
            chat_id=chat.id,
            admin_id=admin_id,
            tab_id=body.tab_id,
            client_event_id=body.client_event_id,
            event=body.event,
        )
    )

    ttl_seconds = 90
    expires_at = now + timedelta(seconds=ttl_seconds)

    if body.event == "CLOSE":
        # Observe lease duration before deletion (best-effort).
        lease_row_res = await session.execute(
            select(OmniChatLease).where(
                OmniChatLease.clinic_id == clinic_id,
                OmniChatLease.chat_id == chat.id,
                OmniChatLease.admin_id == admin_id,
                OmniChatLease.tab_id == body.tab_id,
            )
        )
        lease_row = lease_row_res.scalar_one_or_none()
        if lease_row is not None and getattr(lease_row, "created_at", None) is not None:
            try:
                dur = max(0.0, float((now - lease_row.created_at).total_seconds()))
                omni_lease_duration_seconds.labels(clinic_bucket=clinic_bucket_label(clinic_id)).observe(dur)
            except Exception:
                pass

        await session.execute(
            sa.delete(OmniChatLease).where(
                OmniChatLease.clinic_id == clinic_id,
                OmniChatLease.chat_id == chat.id,
                OmniChatLease.admin_id == admin_id,
                OmniChatLease.tab_id == body.tab_id,
            )
        )
        await session.flush()

        # Update active leases gauge (clinic-scoped).
        try:
            cnt_res = await session.execute(
                select(func.count())
                .select_from(OmniChatLease)
                .where(OmniChatLease.clinic_id == clinic_id, OmniChatLease.expires_at > now)
            )
            omni_active_leases.labels(clinic_bucket=clinic_bucket_label(clinic_id)).set(int(cnt_res.scalar_one() or 0))
        except Exception:
            pass

        # Server-side auto-resolve policy (explicit behavior):
        # After removing this tab lease, auto-resolve only when:
        # - current admin is the assignee (we never auto-resolve someone else's chat)
        # - chat is not closed yet
        # - there are NO other active leases for this chat
        # - chat is idle long enough since last_message_at (pragmatic definition)
        result = await _maybe_auto_resolve_on_close(
            session=session,
            admin_ctx=admin_ctx,
            chat=chat,
            now=now,
        )
        if result is not None:
            return OmniChatPresenceResponse(
                lease=None,
                claimed=bool(chat.assignee_admin_id == admin_id),
                assignee_admin_id=chat.assignee_admin_id,
            )

        return OmniChatPresenceResponse(
            lease=None,
            claimed=bool(chat.assignee_admin_id == admin_id),
            assignee_admin_id=chat.assignee_admin_id,
        )

    # OPEN / HEARTBEAT: upsert lease by (clinic_id, chat_id, admin_id, tab_id)
    lease_res = await session.execute(
        select(OmniChatLease).where(
            OmniChatLease.clinic_id == clinic_id,
            OmniChatLease.chat_id == chat.id,
            OmniChatLease.admin_id == admin_id,
            OmniChatLease.tab_id == body.tab_id,
        )
    )
    lease = lease_res.scalar_one_or_none()
    if lease is None:
        lease = OmniChatLease(
            clinic_id=clinic_id,
            chat_id=chat.id,
            admin_id=admin_id,
            tab_id=body.tab_id,
            expires_at=expires_at,
            last_heartbeat_at=now,
        )
        session.add(lease)
    else:
        lease.expires_at = expires_at
        lease.last_heartbeat_at = now

    await session.flush()
    # Update active leases gauge (clinic-scoped).
    try:
        cnt_res = await session.execute(
            select(func.count())
            .select_from(OmniChatLease)
            .where(OmniChatLease.clinic_id == clinic_id, OmniChatLease.expires_at > now)
        )
        omni_active_leases.labels(clinic_bucket=clinic_bucket_label(clinic_id)).set(int(cnt_res.scalar_one() or 0))
    except Exception:
        pass
    return OmniChatPresenceResponse(
        lease=OmniChatLeaseDto(
            chat_id=lease.chat_id,
            admin_id=lease.admin_id,
            tab_id=lease.tab_id,
            expires_at=lease.expires_at,
            last_heartbeat_at=lease.last_heartbeat_at,
        ),
        claimed=bool(chat.assignee_admin_id == admin_id),
        assignee_admin_id=chat.assignee_admin_id,
    )


async def _count_active_leases(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    chat_id: UUID,
    now: datetime,
) -> int:
    res = await session.execute(
        select(func.count())
        .select_from(OmniChatLease)
        .where(
            OmniChatLease.clinic_id == clinic_id,
            OmniChatLease.chat_id == chat_id,
            OmniChatLease.expires_at > now,
        )
    )
    return int(res.scalar_one() or 0)


async def _maybe_auto_resolve_on_close(
    *,
    session: AsyncSession,
    admin_ctx: AdminContext,
    chat: OmniChat,
    now: datetime,
) -> OmniChatResolveResponseDto | None:
    clinic_id = admin_ctx.clinic_id
    admin_id = admin_ctx.user_id
    if clinic_id is None or admin_id is None:
        return None

    if str(getattr(chat, "status", "") or "").upper() == "CLOSED":
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="skipped_already_closed"
        ).inc()
        return None

    if chat.assignee_admin_id != admin_id:
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="skipped_not_assignee"
        ).inc()
        return None

    active = await _count_active_leases(session, clinic_id=clinic_id, chat_id=chat.id, now=now)
    if active > 0:
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="skipped_active_lease"
        ).inc()
        return None

    last_dt = getattr(chat, "last_message_at", None) or getattr(chat, "created_at", None) or now
    try:
        idle_seconds = max(0.0, float((now - last_dt).total_seconds()))
    except Exception:
        idle_seconds = 0.0
    if idle_seconds < _OMNI_AUTO_RESOLVE_IDLE_SECONDS:
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="skipped_not_idle"
        ).inc()
        return None

    omni_auto_resolve_attempts_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id), result="attempted"
    ).inc()
    try:
        dto = await _resolve_chat_to_lead_log_task(chat_id=chat.id, session=session, admin_ctx=admin_ctx)
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="resolved"
        ).inc()
        return dto
    except Exception as e:
        logger.warning("auto_resolve_failed", extra={"chat_id": str(chat.id), "error": str(e)})
        omni_auto_resolve_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), result="error"
        ).inc()
        return None


@router.post("/{chat_id}/close", response_model=OmniChatCloseResponse)
async def close_omni_chat(
    chat_id: UUID,
    body: CloseOmniChatRequest,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatCloseResponse:
    """Close chat with required outcome/tags/comment."""
    clinic_id = admin_ctx.clinic_id
    admin_id = admin_ctx.user_id
    if clinic_id is None or admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(clinic_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    if chat.assignee_admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "omni_chat_not_claimed", "message": "Chat must be claimed before closing"},
        )
    if chat.assignee_admin_id != admin_id and "owner" not in (admin_ctx.roles or set()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    tag_ids = list(dict.fromkeys(body.tag_ids or []))
    if tag_ids:
        tags_res = await session.execute(
            select(OmniChatClosureTag.id).where(
                OmniChatClosureTag.clinic_id == clinic_id,
                OmniChatClosureTag.id.in_(tag_ids),
                OmniChatClosureTag.is_active.is_(True),
            )
        )
        found = {row[0] for row in tags_res.all()}
        if len(found) != len(tag_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "omni_closure_tag_invalid", "message": "Some tag_ids are invalid for this clinic"},
            )

    now = datetime.utcnow()
    closure_res = await session.execute(select(OmniChatClosure).where(OmniChatClosure.chat_id == chat.id))
    closure = closure_res.scalar_one_or_none()
    if closure is None:
        closure = OmniChatClosure(
            chat_id=chat.id,
            clinic_id=clinic_id,
            closed_by_admin_id=admin_id,
            closed_at=now,
            outcome=body.outcome,
            comment=body.comment,
        )
        session.add(closure)
        await session.flush()
    else:
        closure.closed_by_admin_id = admin_id
        closure.closed_at = now
        closure.outcome = body.outcome
        closure.comment = body.comment
        await session.flush()

    await session.execute(
        sa.delete(OmniChatClosureTagLink).where(OmniChatClosureTagLink.closure_id == closure.id)
    )
    if tag_ids:
        session.add_all([OmniChatClosureTagLink(closure_id=closure.id, tag_id=tid) for tid in tag_ids])

    chat.status = "CLOSED"
    chat.closed_at = now
    await session.flush()
    await publish_omni_chat_updated(clinic_id=clinic_id, chat_id=chat.id, reason="close")

    detail = await _build_omni_chat_detail_dto(session, admin_ctx, chat_id)
    return OmniChatCloseResponse(chat=detail)


def _title_from_first_client_message(messages: list[OmniMessage]) -> str:
    for m in messages:
        if str(getattr(m, "actor_type", "") or "").upper() in {"CLIENT", "CONTACT", "PATIENT"}:
            raw = str(getattr(m, "content", "") or "").strip()
            if raw.lower().startswith("reply_to:"):
                raw = "\n".join(raw.splitlines()[1:]).strip()
            s = " ".join(raw.split())
            if s:
                return (s[:120] + "…") if len(s) > 120 else s
    return "Обращение"


async def _ensure_leads_log_stream(session: AsyncSession, clinic_id: UUID) -> TaskStream:
    res = await session.execute(
        select(TaskStream).where(TaskStream.clinic_id == clinic_id, TaskStream.slug == "leads-log")
    )
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing
    max_res = await session.execute(
        select(func.coalesce(func.max(TaskStream.sort_order), -1)).where(TaskStream.clinic_id == clinic_id)
    )
    next_order = int(max_res.scalar_one() or -1) + 1
    row = TaskStream(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Лиды (лог)",
        slug="leads-log",
        sort_order=next_order,
        is_archived=False,
        theme={"mantine_color": "blue", "page_tint": "none"},
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def _pick_lead_log_target_stream_id(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    channel_type: str | None,
    source_key: str | None,
) -> LeadLogRoutingRule | None:
    ch = channel_type.strip().upper() if channel_type and channel_type.strip() else None
    sk = source_key.strip() if source_key and source_key.strip() else None
    res = await session.execute(
        select(LeadLogRoutingRule)
        .where(LeadLogRoutingRule.clinic_id == clinic_id, LeadLogRoutingRule.is_active.is_(True))
        .order_by(LeadLogRoutingRule.sort_order.asc(), LeadLogRoutingRule.id.asc())
    )
    rules = list(res.scalars().all())
    for r in rules:
        if r.channel_type and ch and r.channel_type != ch:
            continue
        if r.channel_type and ch is None:
            continue
        if r.source_key and sk and r.source_key != sk:
            continue
        if r.source_key and sk is None:
            continue
        stream_res = await session.execute(
            select(TaskStream.id).where(
                TaskStream.id == r.target_stream_id,
                TaskStream.clinic_id == clinic_id,
                TaskStream.is_archived.is_(False),
            )
        )
        sid = stream_res.scalar_one_or_none()
        if sid is not None:
            return r
    return None


@router.post("/{chat_id}/resolve", response_model=OmniChatResolveResponseDto)
async def resolve_omni_chat(
    chat_id: UUID,
    force: bool = Query(False, description="Force resolve even if there is an active lease (requires override permission)"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatResolveResponseDto:
    """Resolve chat: close + snapshot transcript into OmniLeadLog + create done Task artifact."""
    return await _resolve_chat_to_lead_log_task(chat_id=chat_id, session=session, admin_ctx=admin_ctx, force=force)


async def _resolve_chat_to_lead_log_task(
    *,
    chat_id: UUID,
    session: AsyncSession,
    admin_ctx: AdminContext,
    force: bool = False,
) -> OmniChatResolveResponseDto:
    """Shared resolve implementation: used by explicit endpoint and auto-resolve policy."""
    clinic_id = admin_ctx.clinic_id
    admin_id = admin_ctx.user_id
    if clinic_id is None or admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    service = OmnichannelChatService(session)
    chat = await service.get_chat_for_business(clinic_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    if chat.assignee_admin_id is None:
        omni_lead_logs_resolve_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), reason="NOT_CLAIMED"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "omni_chat_not_claimed", "message": "Chat must be claimed before resolving"},
        )
    if chat.assignee_admin_id != admin_id and "owner" not in (admin_ctx.roles or set()):
        omni_lead_logs_resolve_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), reason="FORBIDDEN"
        ).inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if force:
        perms = set(admin_ctx.permissions or set())
        roles = set(admin_ctx.roles or set())
        if "owner" not in roles and "omni.chat.resolve.override" not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    now_guard = datetime.utcnow()
    active_leases = await _count_active_leases(session, clinic_id=clinic_id, chat_id=chat.id, now=now_guard)
    if active_leases > 0 and not force:
        omni_lead_logs_resolve_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), reason="ACTIVE_LEASE"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "omni_chat_active_lease",
                "message": "Chat has an active lease; wait until operator leaves or use force resolve",
            },
        )

    log_res = await session.execute(select(OmniLeadLog).where(OmniLeadLog.omni_chat_id == chat.id))
    existing_log = log_res.scalar_one_or_none()
    if existing_log is not None:
        return OmniChatResolveResponseDto(
            lead_log_id=existing_log.id,
            task_id=None,
            outcome=getattr(existing_log, "outcome", None),
        )

    msgs_res = await session.execute(
        select(OmniMessage)
        .where(OmniMessage.chat_id == chat.id)
        .order_by(OmniMessage.created_at.asc(), OmniMessage.id.asc())
    )
    messages: list[OmniMessage] = list(msgs_res.scalars().all())

    def clean_body(s: str) -> str:
        raw = (s or "").strip()
        if raw.lower().startswith("reply_to:"):
            raw = "\n".join(raw.splitlines()[1:]).strip()
        return raw

    parts: list[str] = []
    for m in messages:
        ts = getattr(m, "created_at", None)
        ts_s = ts.isoformat() if ts else ""
        who = str(getattr(m, "actor_type", "") or "").upper() or "UNKNOWN"
        body = clean_body(str(getattr(m, "content", "") or ""))
        parts.append(f"[{ts_s}] {who}: {body}")
    transcript_text = "\n".join(parts).strip()
    try:
        omni_lead_logs_transcript_bytes.labels(clinic_bucket=clinic_bucket_label(clinic_id)).observe(
            len(transcript_text.encode("utf-8"))
        )
    except Exception:
        pass

    title = _title_from_first_client_message(messages)

    # Routing inputs (MVP): channel_type from chat.channel_id; source_key not available yet.
    channel_type: str | None = None
    if getattr(chat, "channel_id", None):
        ch_res = await session.execute(
            select(OmniChannel.type).where(OmniChannel.id == chat.channel_id).limit(1)
        )
        channel_type = ch_res.scalar_one_or_none()

    lead_id = None
    booking_id = None
    patient_id = None
    outcome = "UNKNOWN"
    try:
        lead = await session.execute(
            select(LeadCard)
            .where(
                LeadCard.clinic_id == clinic_id,
                LeadCard.omnichannel_contact_id == chat.contact_id,
            )
            .order_by(LeadCard.created_at.desc())
            .limit(1)
        )
        lead_row = lead.scalar_one_or_none()
        if lead_row:
            lead_id = lead_row.id
            booking_id = lead_row.primary_booking_id
            patient_id = lead_row.patient_id
            outcome = "BOOKED" if booking_id else "NOT_BOOKED"
        else:
            outcome = "UNKNOWN"
    except Exception:
        outcome = "UNKNOWN"

    now = datetime.utcnow()
    chat.status = "CLOSED"
    chat.closed_at = now
    await session.flush()
    await publish_omni_chat_updated(clinic_id=clinic_id, chat_id=chat.id, reason="resolve")

    try:
        lead_log = OmniLeadLog(
            clinic_id=clinic_id,
            omni_chat_id=chat.id,
            contact_id=chat.contact_id,
            opened_by_admin_id=chat.assignee_admin_id,
            opened_at=getattr(chat, "created_at", None),
            closed_at=now,
            title=title,
            outcome=outcome,
            transcript_text=transcript_text,
            transcript_json={
                "chat_id": str(chat.id),
                "messages": [
                    {
                        "id": str(getattr(m, "id")),
                        "created_at": getattr(m, "created_at").isoformat() if getattr(m, "created_at", None) else None,
                        "actor_type": getattr(m, "actor_type", None),
                        "direction": getattr(m, "direction", None),
                        "content": clean_body(str(getattr(m, "content", "") or "")),
                    }
                    for m in messages
                ],
            },
            lead_id=lead_id,
            booking_id=booking_id,
            patient_id=patient_id,
        )
        session.add(lead_log)
        await session.flush()
        await session.refresh(lead_log)
    except IntegrityError:
        res2 = await session.execute(select(OmniLeadLog).where(OmniLeadLog.omni_chat_id == chat.id))
        lead_log = res2.scalar_one()

    # Pick target stream via routing rules; fallback to default leads-log stream.
    matched_rule = await _pick_lead_log_target_stream_id(
        session,
        clinic_id=clinic_id,
        channel_type=channel_type,
        source_key=None,
    )
    if matched_rule is None:
        lead_log_routing_fallback_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), channel_type=str(channel_type or "UNKNOWN")
        ).inc()
        stream = await _ensure_leads_log_stream(session, clinic_id)
    else:
        stream = await session.get(TaskStream, matched_rule.target_stream_id)
        if stream is None or stream.clinic_id != clinic_id or stream.is_archived:
            lead_log_routing_fallback_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), channel_type=str(channel_type or "UNKNOWN")
            ).inc()
            stream = await _ensure_leads_log_stream(session, clinic_id)
        else:
            lead_log_routing_matches_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                channel_type=str(channel_type or "UNKNOWN"),
                stream_slug=str(getattr(stream, "slug", "") or "unknown"),
            ).inc()
    task = Task(
        clinic_id=clinic_id,
        stream_id=stream.id,
        title=title,
        description=(transcript_text[:1800] + ("\n…\n" if len(transcript_text) > 1800 else "")) + f"\n\nLeadLog: {lead_log.id}",
        status="done",
        priority="medium",
        creator_id=admin_id,
        assignee_id=None,
        role_assignee=None,
        due_at=None,
        completed_at=now,
        booking_id=booking_id,
        patient_id=patient_id,
        lead_id=lead_id,
        source="system",
        trace_id=f"omni_lead_log:{lead_log.id}",
    )
    session.add(task)
    await session.flush()

    omni_lead_logs_resolved_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        outcome=str(outcome or "UNKNOWN"),
    ).inc()
    return OmniChatResolveResponseDto(lead_log_id=lead_log.id, task_id=task.id, outcome=outcome)


@router.get("/analytics", response_model=OmniChatAnalyticsResponse)
async def omni_chat_analytics(
    date_from: str = Query(..., description="YYYY-MM-DD (inclusive)"),
    date_to: str = Query(..., description="YYYY-MM-DD (exclusive)"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("erp.owner_reports.read")),
) -> OmniChatAnalyticsResponse:
    """Pragmatic analytics for omni-chat (owner/chief admin)."""
    _require_owner_reports(admin_ctx)
    clinic_id = admin_ctx.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")

    try:
        from datetime import date

        df = date.fromisoformat(date_from)
        dt = date.fromisoformat(date_to)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "omni_analytics_date_invalid", "message": "date_from/date_to must be YYYY-MM-DD"},
        )
    if not (df < dt):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "omni_analytics_date_range_invalid", "message": "date_from must be < date_to"},
        )

    start_dt = datetime(df.year, df.month, df.day)
    end_dt = datetime(dt.year, dt.month, dt.day)

    created_stmt = (
        select(func.count())
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
    )
    claimed_stmt = (
        select(func.count())
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.claimed_at.is_not(None),
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
    )
    closed_stmt = (
        select(func.count())
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.closed_at.is_not(None),
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
    )

    created = int((await session.execute(created_stmt)).scalar_one() or 0)
    claimed = int((await session.execute(claimed_stmt)).scalar_one() or 0)
    closed = int((await session.execute(closed_stmt)).scalar_one() or 0)

    # Average times (seconds) on chats created in range.
    avg_claim_stmt = (
        select(func.avg(func.extract("epoch", OmniChat.claimed_at - OmniChat.created_at)))
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.claimed_at.is_not(None),
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
    )
    avg_close_stmt = (
        select(func.avg(func.extract("epoch", OmniChat.closed_at - OmniChat.created_at)))
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.closed_at.is_not(None),
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
    )
    avg_claim = (await session.execute(avg_claim_stmt)).scalar_one_or_none()
    avg_close = (await session.execute(avg_close_stmt)).scalar_one_or_none()

    # Outcomes breakdown by closures closed in range (by closed_at).
    outcomes_rows = await session.execute(
        select(OmniChatClosure.outcome, func.count())
        .select_from(OmniChatClosure)
        .where(
            OmniChatClosure.clinic_id == clinic_id,
            OmniChatClosure.closed_at >= start_dt,
            OmniChatClosure.closed_at < end_dt,
        )
        .group_by(OmniChatClosure.outcome)
        .order_by(func.count().desc())
    )
    outcomes = [OmniChatOutcomeStatDto(outcome=str(o), count=int(c)) for o, c in outcomes_rows.all()]

    # By admin (claimed/closed counts).
    claimed_by_admin_rows = await session.execute(
        select(OmniChat.assignee_admin_id, func.count())
        .select_from(OmniChat)
        .where(
            OmniChat.business_account_id == clinic_id,
            OmniChat.assignee_admin_id.is_not(None),
            OmniChat.claimed_at.is_not(None),
            OmniChat.created_at >= start_dt,
            OmniChat.created_at < end_dt,
        )
        .group_by(OmniChat.assignee_admin_id)
    )
    claimed_by_admin = {aid: int(cnt) for aid, cnt in claimed_by_admin_rows.all() if aid}

    closed_by_admin_rows = await session.execute(
        select(OmniChatClosure.closed_by_admin_id, func.count())
        .select_from(OmniChatClosure)
        .where(
            OmniChatClosure.clinic_id == clinic_id,
            OmniChatClosure.closed_at >= start_dt,
            OmniChatClosure.closed_at < end_dt,
        )
        .group_by(OmniChatClosure.closed_by_admin_id)
    )
    closed_by_admin = {aid: int(cnt) for aid, cnt in closed_by_admin_rows.all() if aid}

    admin_ids = set(claimed_by_admin.keys()) | set(closed_by_admin.keys())
    admin_names = await _admin_display_names(session, admin_ids)
    by_admin = [
        OmniChatAdminStatDto(
            admin_id=aid,
            admin_name=admin_names.get(aid),
            claimed_count=claimed_by_admin.get(aid, 0),
            closed_count=closed_by_admin.get(aid, 0),
        )
        for aid in sorted(admin_ids, key=lambda x: admin_names.get(x) or str(x))
    ]

    return OmniChatAnalyticsResponse(
        date_from=date_from,
        date_to=date_to,
        total_chats_created=created,
        total_claimed=claimed,
        total_closed=closed,
        avg_time_to_claim_seconds=float(avg_claim) if avg_claim is not None else None,
        avg_time_to_close_seconds=float(avg_close) if avg_close is not None else None,
        outcomes=outcomes,
        by_admin=by_admin,
    )


async def _build_omni_chat_detail_dto(
    session: AsyncSession,
    admin_ctx: AdminContext,
    chat_id: UUID,
) -> OmniChatDetailDto:
    """Shared body for GET /{chat_id} and post-mutation responses (claim/close/patch)."""
    business_account_id: UUID | None = admin_ctx.clinic_id
    if business_account_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
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
        claimed_at=getattr(chat, "claimed_at", None),
        closed_at=getattr(chat, "closed_at", None),
    )


@router.get("/{chat_id}", response_model=OmniChatDetailDto)
async def get_omni_chat(
    chat_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniChatDetailDto:
    """Return single omnichannel chat by id for current business."""
    return await _build_omni_chat_detail_dto(session, admin_ctx, chat_id)


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
    if "assignee_admin_id" in body.model_fields_set:
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
    if "status" in body.model_fields_set and body.status is not None:
        chat.status = body.status
    await session.flush()

    return await _build_omni_chat_detail_dto(session, admin_ctx, chat_id)


@router.get("/{chat_id}/messages", response_model=OmniMessagesResponse)
async def get_omni_chat_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    after: UUID | None = Query(None, description="Return messages after this message id (cursor)"),
    before: UUID | None = Query(None, description="Return messages before this message id (cursor)"),
    include_hidden: bool = Query(False, description="Include soft-hidden messages"),
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
) -> OmniMessagesResponse:
    """Return messages for given chat (chronological order). Use after/before for cursor pagination."""
    business_account_id: UUID | None = admin_ctx.clinic_id
    if business_account_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
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
        409: {"description": "Reply channel could not be resolved (code omni_reply_channel_unresolved)"},
        429: {"description": "Outbound send rate limit (per admin, default 30/min)"},
    },
)
async def send_admin_omni_message(
    chat_id: UUID,
    data: SendOmniMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
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
                "code": "omni_send_rate_limited",
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

    # Hard-claim-on-commit (first outbound send): do not auto-steal claimed chats.
    if chat.assignee_admin_id is None:
        omni_auto_claim_total.labels(
            clinic_bucket=clinic_bucket_label(business_account_id), source="message"
        ).inc()
        try:
            if getattr(chat, "created_at", None) is not None:
                dt = max(0.0, float((datetime.utcnow() - chat.created_at).total_seconds()))
                omni_time_to_first_outbound_seconds.labels(
                    clinic_bucket=clinic_bucket_label(business_account_id)
                ).observe(dt)
        except Exception:
            pass
        chat.assignee_admin_id = current_admin.id
        if getattr(chat, "claimed_at", None) is None:
            chat.claimed_at = datetime.utcnow()
        if chat.status in {"OPEN", "WAITING_FOR_OPERATOR"}:
            chat.status = "IN_PROGRESS"
        await session.flush()
        await publish_omni_chat_updated(
            clinic_id=business_account_id, chat_id=chat.id, reason="auto_claim_commit"
        )
    elif chat.assignee_admin_id != current_admin.id:
        omni_auto_claim_conflicts_total.labels(clinic_bucket=clinic_bucket_label(business_account_id)).inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "omni_chat_already_claimed",
                "message": "Chat already claimed by another admin",
            },
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
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
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
                "code": "omni_send_rate_limited",
                "message": "Слишком много исходящих сообщений. Подождите и повторите.",
            },
        ) from None

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")
    if len(raw) > settings.staff_chat_max_attachment_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip()
    fn = (file.filename or "").lower()
    if fn.endswith(".svg") or fn.endswith(".svgz") or ct.lower() in {"image/svg+xml", "image/svg"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SVG запрещён")
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

    # Hard-claim-on-commit (first outbound send): do not auto-steal claimed chats.
    if chat.assignee_admin_id is None:
        omni_auto_claim_total.labels(
            clinic_bucket=clinic_bucket_label(business_account_id), source="upload"
        ).inc()
        try:
            if getattr(chat, "created_at", None) is not None:
                dt = max(0.0, float((datetime.utcnow() - chat.created_at).total_seconds()))
                omni_time_to_first_outbound_seconds.labels(
                    clinic_bucket=clinic_bucket_label(business_account_id)
                ).observe(dt)
        except Exception:
            pass
        chat.assignee_admin_id = current_admin.id
        if getattr(chat, "claimed_at", None) is None:
            chat.claimed_at = datetime.utcnow()
        if chat.status in {"OPEN", "WAITING_FOR_OPERATOR"}:
            chat.status = "IN_PROGRESS"
        await session.flush()
        await publish_omni_chat_updated(
            clinic_id=business_account_id, chat_id=chat.id, reason="auto_claim_commit"
        )
    elif chat.assignee_admin_id != current_admin.id:
        omni_auto_claim_conflicts_total.labels(clinic_bucket=clinic_bucket_label(business_account_id)).inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "omni_chat_already_claimed",
                "message": "Chat already claimed by another admin",
            },
        )

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
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
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
    raw_media_type = str(meta.get("content_type") or "application/octet-stream")
    media_type = raw_media_type.split(";")[0].strip() or "application/octet-stream"
    safe_inline_images = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/avif"}
    if media_type.lower().startswith("audio/"):
        allow_audio = request_context.user_type == "admin" and "owner" in request_context.roles
        disp = clinic_chat_attachment_content_disposition(
            media_type,
            fname,
            allow_audio_as_attachment=allow_audio,
        )
    else:
        # SECURITY: don't trust stored content_type; download as attachment by default.
        if media_type.lower() in safe_inline_images:
            disp = f'inline; filename="{fname.replace(chr(34), chr(39))[:200]}"'
        else:
            disp = f'attachment; filename="{fname.replace(chr(34), chr(39))[:200]}"'
            media_type = "application/octet-stream"
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
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
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
    _admin_ctx: AdminContext = Depends(require_permissions("omni.inbox.manage")),
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

