"""P1 Staff Core: internal feed, staff chat, calendar, knowledge base."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.chat_attachment_disposition import clinic_chat_attachment_content_disposition
from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.staff_collab_dto import (
    StaffCalendarEventDetailsResponse,
    StaffCalendarInvitationAckResponse,
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    StaffAttachmentBrief,
    StaffCalendarEventCreate,
    StaffCalendarEventResponse,
    StaffCalendarEventUpdate,
    StaffCalendarMonthGridResponse,
    StaffChatMessageCreate,
    StaffChatMessageResponse,
    StaffChatRoomResponse,
    StaffFeedCommentCreate,
    StaffFeedCommentResponse,
    StaffFeedCommentUpdate,
    StaffFeedPostCreate,
    StaffFeedPostResponse,
    StaffFeedPostLikeResponse,
    StaffFeedPostAckResponse,
    StaffFeedPostAckStatusResponse,
    StaffFeedAckStatusRow,
    StaffAnnouncementPublishPolicyRow,
    StaffAnnouncementPublishPolicyResponse,
    StaffAnnouncementPublishPolicyAuditListResponse,
    StaffRoomCreateDm,
    StaffRoomCreateGroup,
    StaffRoomInviteCreate,
)
from src.application.services.staff_collaboration_service import StaffCollaborationService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_event_participant import StaffCalendarEventParticipant
from src.domain.entities.task import Task
from src.core.config import settings
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.core.metrics import chat_rate_limited_total
from src.core.metrics import chat_upload_rejected_total

router = APIRouter(prefix="/admin/staff", tags=["admin-staff-collab"])


def _naive_utc(dt: datetime) -> datetime:
    """DB stores naive timestamps; normalize query params from ISO with offset."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _svc(session: AsyncSession) -> StaffCollaborationService:
    return StaffCollaborationService(session)


def _clinic_id(ctx: AdminContext) -> UUID:
    if ctx.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    return ctx.clinic_id


async def _admin_in_clinic(session: AsyncSession, clinic_id: UUID, admin_id: UUID) -> bool:
    res = await session.execute(
        select(AdminUser.id).where(
            AdminUser.id == admin_id,
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        )
    )
    return res.scalar_one_or_none() is not None


async def require_active_clinic_admin(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions()),
) -> AdminContext:
    """Любой активный администратор в контексте своей клиники.

    Для **внутренней стены** (лента персонала): чтение, лайки и комментарии доступны всем
    сотрудникам с учётной записью админки этой клиники, без отдельного ``view_staff_collab``.
    Чат, календарь и база знаний по-прежнему требуют ``view_staff_collab``.
    """
    if context.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется пользователь",
        )
    cid = _clinic_id(context)
    if not await _admin_in_clinic(session, cid, context.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к клинике",
        )
    return context


@router.get(
    "/chat/rooms",
    response_model=list[StaffChatRoomResponse],
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def list_staff_chat_rooms(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[StaffChatRoomResponse]:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    return await _svc(session).list_chat_rooms(cid, context.user_id)


@router.post(
    "/chat/rooms/{room_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def mark_staff_chat_room_read(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> None:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    ok = await _svc(session).mark_chat_room_read(cid, room_id, context.user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")


@router.get(
    "/chat/rooms/{room_id}/messages",
    response_model=list[StaffChatMessageResponse],
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def list_staff_chat_messages(
    room_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[StaffChatMessageResponse]:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    rows = await _svc(session).list_chat_messages(cid, room_id, context.user_id, limit=limit)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")
    return rows


@router.post(
    "/chat/rooms/{room_id}/messages",
    response_model=StaffChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def post_staff_chat_message(
    room_id: UUID,
    data: StaffChatMessageCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    rate_limiter=Depends(get_rate_limiter),
) -> StaffChatMessageResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:staff_chat_send:admin:{context.user_id}",
            limit=settings.rate_staff_chat_send_per_admin_limit,
            window=settings.rate_staff_chat_send_window_seconds,
        )
        await rate_limiter.check_or_raise(
            key=f"rate:staff_chat_send:room:{room_id}",
            limit=settings.rate_staff_chat_send_per_room_limit,
            window=settings.rate_staff_chat_send_window_seconds,
        )
    except RateLimitExceeded:
        chat_rate_limited_total.labels(kind="staff_chat").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "CHAT_RATE_LIMITED", "message": "Слишком много сообщений. Подождите и повторите."},
        ) from None
    msg = await _svc(session).post_chat_message(cid, room_id, context.user_id, data)
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")
    return msg


@router.post(
    "/chat/rooms/dm",
    response_model=StaffChatRoomResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def create_staff_dm_room(
    data: StaffRoomCreateDm,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffChatRoomResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    if context.user_id == data.peer_admin_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя открыть DM с самим собой")
    if not await _admin_in_clinic(session, cid, data.peer_admin_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сотрудник не в этой клинике")
    room = await _svc(session).get_or_create_dm_room(cid, context.user_id, data.peer_admin_id)
    return StaffChatRoomResponse(
        id=room.id, kind=room.kind, title=room.title, task_id=room.task_id
    )


@router.post(
    "/chat/rooms/group",
    response_model=StaffChatRoomResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def create_staff_group_room(
    data: StaffRoomCreateGroup,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffChatRoomResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    for aid in data.member_admin_ids:
        if not await _admin_in_clinic(session, cid, aid):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Сотрудник {aid} не в этой клинике",
            )
    room = await _svc(session).create_group_room(cid, context.user_id, data)
    return StaffChatRoomResponse(
        id=room.id, kind=room.kind, title=room.title, task_id=room.task_id
    )


@router.get(
    "/chat/task-rooms/{task_id}",
    response_model=StaffChatRoomResponse,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def get_or_create_task_chat_room(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffChatRoomResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    task = await session.get(Task, task_id)
    if task is None or task.clinic_id != cid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    room = await _svc(session).ensure_task_room(cid, task_id, context.user_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена или нет доступа к комнате задачи",
        )
    return StaffChatRoomResponse(
        id=room.id, kind=room.kind, title=room.title, task_id=room.task_id
    )


@router.post(
    "/chat/rooms/{room_id}/members",
    response_model=StaffChatRoomResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def invite_staff_chat_room_member(
    room_id: UUID,
    data: StaffRoomInviteCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffChatRoomResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    try:
        room = await _svc(session).invite_to_room(cid, room_id, context.user_id, data)
    except ValueError as exc:
        code = str(exc)
        if code == "cannot_invite_self":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя пригласить себя") from exc
        if code == "room_kind_not_invitable":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="В этот тип комнаты приглашения не поддерживаются",
            ) from exc
        if code == "invitee_not_in_clinic":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сотрудник не в этой клинике",
            ) from exc
        raise
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")
    return StaffChatRoomResponse(
        id=room.id, kind=room.kind, title=room.title, task_id=room.task_id
    )


@router.post(
    "/chat/messages/{message_id}/attachments",
    response_model=StaffAttachmentBrief,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def upload_staff_chat_attachment(
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    file: UploadFile = File(...),
) -> StaffAttachmentBrief:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    max_bytes = int(settings.staff_chat_max_attachment_bytes or 0)
    if max_bytes <= 0:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Upload limit not configured")
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = tmp.name
    size = 0
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                chat_upload_rejected_total.labels(kind="staff_chat_upload", reason="file_too_large").inc()
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
            tmp.write(chunk)
        tmp.flush()
    finally:
        try:
            await file.close()
        except Exception:
            pass
        try:
            tmp.close()
        except Exception:
            pass
    try:
        att = await _svc(session).add_message_attachment(
            cid,
            message_id,
            context.user_id,
            file_name=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            raw=None,
            tmp_path=tmp_path,
            size_bytes=size,
        )
    except ValueError as exc:
        if str(exc) == "file_too_large":
            chat_upload_rejected_total.labels(kind="staff_chat_upload", reason="file_too_large").inc()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой",
            ) from exc
        if str(exc) == "file_magic_mismatch":
            chat_upload_rejected_total.labels(kind="staff_chat_upload", reason="file_magic_mismatch").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл не соответствует заявленному типу (content-type).",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    if att is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
    return att


@router.get(
    "/attachments/{attachment_id}/file",
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def download_staff_chat_attachment(
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> Response:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    payload = await _svc(session).get_attachment_payload(cid, attachment_id, context.user_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
    row, raw = payload
    allow_audio = "owner" in context.roles
    disp = clinic_chat_attachment_content_disposition(
        row.content_type,
        row.file_name,
        allow_audio_as_attachment=allow_audio,
    )
    return Response(
        content=raw,
        media_type=row.content_type,
        headers={"Content-Disposition": disp},
    )


@router.get(
    "/feed/posts",
    response_model=list[StaffFeedPostResponse],
)
async def list_staff_feed_posts(
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> list[StaffFeedPostResponse]:
    return await _svc(session).list_feed_posts(
        _clinic_id(context),
        viewer_admin_id=context.user_id,
        viewer_role_codes=set(context.roles),
        limit=limit,
        exclude_announcements=True,
    )


@router.get(
    "/feed/announcements",
    response_model=list[StaffFeedPostResponse],
)
async def list_staff_feed_announcements(
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> list[StaffFeedPostResponse]:
    return await _svc(session).list_feed_posts(
        _clinic_id(context),
        viewer_admin_id=context.user_id,
        viewer_role_codes=set(context.roles),
        limit=limit,
        only_announcements=True,
    )


@router.post(
    "/feed/posts",
    response_model=StaffFeedPostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_staff_feed_post(
    data: StaffFeedPostCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedPostResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    try:
        return await _svc(session).create_feed_post(
            cid,
            context.user_id,
            data,
            actor_role_codes=set(context.roles),
        )
    except ValueError as exc:
        if str(exc) == "announcement_publish_denied":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Публикация объявлений отключена политикой",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/feed/posts/{post_id}",
    response_model=StaffFeedPostResponse,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def update_staff_feed_post(
    post_id: UUID,
    title: str | None = Form(None),
    body: str = Form(...),
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffFeedPostResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")

    raw = None
    file_name = None
    content_type = None
    if file is not None:
        raw = await file.read()
        file_name = file.filename or "file"
        content_type = file.content_type or "application/octet-stream"

    try:
        updated = await _svc(session).update_feed_post(
            cid,
            context.user_id,
            post_id,
            title=title,
            body=body,
            raw=raw,
            file_name=file_name,
            content_type=content_type,
        )
    except ValueError as exc:
        if str(exc) == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    return updated


@router.delete(
    "/feed/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def delete_staff_feed_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> None:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    ok = await _svc(session).delete_feed_post(cid, post_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")


@router.post(
    "/feed/posts/{post_id}/like",
    response_model=StaffFeedPostLikeResponse,
)
async def toggle_staff_feed_post_like(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedPostLikeResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    toggled = await _svc(session).toggle_feed_post_like(cid, post_id, context.user_id)
    if toggled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    liked, likes_count = toggled
    return StaffFeedPostLikeResponse(liked=liked, likes_count=likes_count)


@router.post(
    "/feed/posts/{post_id}/ack",
    response_model=StaffFeedPostAckResponse,
)
async def acknowledge_staff_feed_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedPostAckResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    toggled = await _svc(session).acknowledge_feed_post(
        cid,
        post_id,
        context.user_id,
        viewer_role_codes=set(context.roles),
    )
    if toggled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    acknowledged, acknowledged_count = toggled
    return StaffFeedPostAckResponse(
        acknowledged=acknowledged,
        acknowledged_count=acknowledged_count,
    )


@router.get(
    "/feed/posts/{post_id}/ack-status",
    response_model=StaffFeedPostAckStatusResponse,
)
async def get_staff_feed_post_ack_status(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedPostAckStatusResponse:
    cid = _clinic_id(context)
    rows = await _svc(session).feed_post_ack_status(cid, post_id)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    acknowledged_rows, pending_rows = rows
    return StaffFeedPostAckStatusResponse(
        post_id=post_id,
        acknowledged=[
            StaffFeedAckStatusRow(admin_id=aid, admin_name=name, acknowledged_at=acked_at)
            for aid, name, acked_at in acknowledged_rows
        ],
        pending=[
            StaffFeedAckStatusRow(admin_id=aid, admin_name=name, acknowledged_at=None)
            for aid, name, _ in pending_rows
        ],
    )


@router.post(
    "/feed/posts/{post_id}/attachments",
    response_model=StaffAttachmentBrief,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def upload_staff_feed_post_attachment(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
    file: UploadFile = File(...),
) -> StaffAttachmentBrief:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    raw = await file.read()
    try:
        att = await _svc(session).add_feed_post_attachment(
            cid,
            post_id,
            context.user_id,
            file_name=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            raw=raw,
        )
    except ValueError as exc:
        if str(exc) == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if att is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    return att


@router.get(
    "/feed/attachments/{attachment_id}/file",
)
async def download_staff_feed_post_attachment(
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> Response:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    payload = await _svc(session).get_feed_attachment_payload(cid, attachment_id, context.user_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
    row, raw = payload
    return Response(
        content=raw,
        media_type=row.content_type,
        headers={"Content-Disposition": f'attachment; filename="{row.file_name}"'},
    )


@router.get(
    "/feed/posts/{post_id}/comments",
    response_model=list[StaffFeedCommentResponse],
)
async def list_staff_feed_comments(
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> list[StaffFeedCommentResponse]:
    include_deleted = "owner" in set(context.roles or set())
    rows = await _svc(session).list_feed_comments(
        _clinic_id(context),
        post_id,
        include_deleted=include_deleted,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    return rows


@router.post(
    "/feed/posts/{post_id}/comments",
    response_model=StaffFeedCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_staff_feed_comment(
    post_id: UUID,
    data: StaffFeedCommentCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedCommentResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    try:
        c = await _svc(session).add_feed_comment(cid, post_id, context.user_id, data)
    except ValueError as exc:
        if str(exc) == "invalid_parent_comment":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Комментарий для ответа не найден в этом посте",
            ) from exc
        raise
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пост не найден")
    return c


@router.patch(
    "/feed/comments/{comment_id}",
    response_model=StaffFeedCommentResponse,
)
async def update_staff_feed_comment(
    comment_id: UUID,
    data: StaffFeedCommentUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffFeedCommentResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    try:
        row = await _svc(session).update_feed_comment(
            cid,
            comment_id=comment_id,
            editor_admin_id=context.user_id,
            data=data,
        )
    except ValueError as exc:
        if str(exc) == "comment_deleted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Комментарий удалён") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комментарий не найден или вы не автор")
    return row


@router.delete(
    "/feed/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_staff_feed_comment(
    comment_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> None:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    allow_moderate = (
        ("owner" in set(context.roles or set()))
        or ("staff.feed.comments.moderate" in set(context.permissions or set()))
    )
    ok = await _svc(session).delete_feed_comment(
        cid,
        comment_id=comment_id,
        actor_admin_id=context.user_id,
        allow_moderate=allow_moderate,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комментарий не найден или нет доступа")


@router.get(
    "/feed/announcements/publish-policy",
    response_model=StaffAnnouncementPublishPolicyResponse,
    dependencies=[Depends(require_permissions("rbac.manage"))],
)
async def get_staff_announcement_publish_policy(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffAnnouncementPublishPolicyResponse:
    cid = _clinic_id(context)
    return await _svc(session).list_announcement_publish_policies(cid)


@router.put(
    "/feed/announcements/publish-policy",
    response_model=StaffAnnouncementPublishPolicyResponse,
    dependencies=[Depends(require_permissions("rbac.manage"))],
)
async def put_staff_announcement_publish_policy(
    rows: list[StaffAnnouncementPublishPolicyRow],
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffAnnouncementPublishPolicyResponse:
    cid = _clinic_id(context)
    return await _svc(session).upsert_announcement_publish_policies(
        cid,
        actor_admin_id=context.user_id,
        rows=rows,
    )


@router.get(
    "/feed/announcements/publish-policy/audit",
    response_model=StaffAnnouncementPublishPolicyAuditListResponse,
)
async def list_staff_announcement_publish_policy_audit(
    limit: int = Query(200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
) -> StaffAnnouncementPublishPolicyAuditListResponse:
    # Owner-only by default, with optional individual grant.
    is_owner = "owner" in set(context.roles or set())
    has_perm = "staff.announcements.policy.audit.view" in set(context.permissions or set())
    if not (is_owner or has_perm):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return await _svc(session).list_announcement_publish_policy_audits(_clinic_id(context), limit=limit)


@router.post(
    "/feed/comments/{comment_id}/attachments",
    response_model=StaffAttachmentBrief,
    status_code=status.HTTP_201_CREATED,
)
async def upload_staff_feed_comment_attachment(
    comment_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_active_clinic_admin),
    file: UploadFile = File(...),
) -> StaffAttachmentBrief:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    raw = await file.read()
    try:
        att = await _svc(session).add_feed_comment_attachment(
            cid,
            comment_id,
            context.user_id,
            file_name=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            raw=raw,
        )
    except ValueError as exc:
        if str(exc) == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if att is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комментарий не найден или вы не автор",
        )
    return att


@router.get(
    "/calendar/events",
    response_model=list[StaffCalendarEventResponse],
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def list_staff_calendar_events(
    from_ts: datetime = Query(..., alias="from"),
    to_ts: datetime = Query(..., alias="to"),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[StaffCalendarEventResponse]:
    from_ts = _naive_utc(from_ts)
    to_ts = _naive_utc(to_ts)
    if from_ts >= to_ts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Интервал некорректен")
    full_scope = {"owner", "manager", "admin"}
    doctor_only = bool(context.roles and not full_scope.intersection(context.roles))
    filter_uid = context.user_id if doctor_only else None
    return await _svc(session).list_calendar_events(
        _clinic_id(context),
        from_ts=from_ts,
        to_ts=to_ts,
        filter_doctor_user_id=filter_uid,
    )


@router.get(
    "/calendar/month",
    response_model=StaffCalendarMonthGridResponse,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def get_staff_calendar_month_grid(
    from_ts: datetime = Query(..., alias="from"),
    to_ts: datetime = Query(..., alias="to"),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffCalendarMonthGridResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    from_ts = _naive_utc(from_ts)
    to_ts = _naive_utc(to_ts)
    if from_ts >= to_ts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Интервал некорректен")
    return await _svc(session).list_calendar_month_grid(
        cid,
        from_ts=from_ts,
        to_ts=to_ts,
        current_admin_id=context.user_id,
    )


@router.get(
    "/calendar/events/{event_id}",
    response_model=StaffCalendarEventDetailsResponse,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def get_staff_calendar_event_details(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffCalendarEventDetailsResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")

    ev_res = await session.execute(
        select(StaffCalendarEvent).where(
            StaffCalendarEvent.id == event_id,
            StaffCalendarEvent.clinic_id == cid,
        )
    )
    ev = ev_res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Событие не найдено")

    uid = context.user_id
    is_member = ev.created_by_admin_id == uid
    if not is_member:
        part_res = await session.execute(
            select(StaffCalendarEventParticipant.event_id).where(
                StaffCalendarEventParticipant.event_id == event_id,
                StaffCalendarEventParticipant.admin_id == uid,
            )
        )
        is_member = part_res.scalar_one_or_none() is not None

    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к событию")

    details = await _svc(session).get_calendar_event_details(
        cid,
        event_id=event_id,
        current_admin_id=uid,
    )
    if details is None:
        # Should not happen because we already validated membership + existence.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Событие не найдено")
    return details


@router.post(
    "/calendar/events/{event_id}/invitations/ack",
    response_model=StaffCalendarInvitationAckResponse,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def ack_staff_calendar_invitation(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffCalendarInvitationAckResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")

    ev_res = await session.execute(
        select(StaffCalendarEvent).where(
            StaffCalendarEvent.id == event_id,
            StaffCalendarEvent.clinic_id == cid,
        )
    )
    ev = ev_res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Событие не найдено")

    uid = context.user_id
    is_member = ev.created_by_admin_id == uid
    if not is_member:
        part_res = await session.execute(
            select(StaffCalendarEventParticipant.event_id).where(
                StaffCalendarEventParticipant.event_id == event_id,
                StaffCalendarEventParticipant.admin_id == uid,
            )
        )
        is_member = part_res.scalar_one_or_none() is not None
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к событию")

    ack = await _svc(session).ack_calendar_invitation(
        cid,
        event_id=event_id,
        current_admin_id=uid,
    )
    if ack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")
    return ack


@router.post(
    "/calendar/events",
    response_model=StaffCalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def create_staff_calendar_event(
    data: StaffCalendarEventCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffCalendarEventResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    if data.ends_at <= data.starts_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Время окончания должно быть позже начала")
    if len(data.participant_admin_ids) > 0 and "invite_staff_calendar_participants" not in context.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Приглашение участников требует права invite_staff_calendar_participants",
        )
    try:
        return await _svc(session).create_calendar_event(cid, context.user_id, data)
    except ValueError as exc:
        if str(exc) == "invalid_participants":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректные участники (клиника или статус сотрудника)",
            ) from exc
        if str(exc) == "calendar_event_overlap":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Событие пересекается с другим событием",
            ) from exc
        raise


@router.patch(
    "/calendar/events/{event_id}",
    response_model=StaffCalendarEventResponse,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def patch_staff_calendar_event(
    event_id: UUID,
    data: StaffCalendarEventUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> StaffCalendarEventResponse:
    cid = _clinic_id(context)
    if data.starts_at is not None and data.ends_at is not None and data.ends_at <= data.starts_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Время окончания должно быть позже начала")
    if data.participant_admin_ids is not None and "invite_staff_calendar_participants" not in context.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Изменение участников требует права invite_staff_calendar_participants",
        )
    try:
        ev = await _svc(session).update_calendar_event(cid, event_id, data)
    except ValueError as exc:
        if str(exc) == "invalid_event_range":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Время окончания должно быть позже начала",
            ) from exc
        if str(exc) == "invalid_participants":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректные участники (клиника или статус сотрудника)",
            ) from exc
        if str(exc) == "calendar_event_overlap":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Событие пересекается с другим событием",
            ) from exc
        raise
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Событие не найдено")
    return ev


@router.get(
    "/knowledge/documents",
    response_model=list[KnowledgeDocumentResponse],
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def list_knowledge_documents(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[KnowledgeDocumentResponse]:
    return await _svc(session).list_knowledge(_clinic_id(context), context.roles)


@router.post(
    "/knowledge/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def create_knowledge_document(
    data: KnowledgeDocumentCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> KnowledgeDocumentResponse:
    cid = _clinic_id(context)
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется пользователь")
    return await _svc(session).create_knowledge(cid, context.user_id, data)


@router.patch(
    "/knowledge/documents/{doc_id}",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permissions("manage_staff_collab"))],
)
async def update_knowledge_document(
    doc_id: UUID,
    data: KnowledgeDocumentUpdate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> KnowledgeDocumentResponse:
    doc = await _svc(session).update_knowledge(_clinic_id(context), doc_id, data)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return doc
