"""Admin chat API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.api.v1.chat_attachment_disposition import clinic_chat_attachment_content_disposition
from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin, get_current_admin_optional
from src.application.dto.chat_ai_dto import ConversationSummaryResponse, SuggestReplyResponse
from src.application.dto.chat_dto import (
    AdminConversationsResponse,
    AssignRequest,
    AssignResponse,
    MarkReadRequest,
    MessageDto,
    MessagesResponse,
    SendMessageRequest,
)
from src.application.services.chat_ai_service import ChatAiService, ChatAiServiceError
from src.application.services.chat_service import ChatService
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/chat", tags=["admin-chat"])


class SuggestReplyRequest(BaseModel):
    intent: str | None = None


@router.get("/conversations", response_model=AdminConversationsResponse)
async def list_conversations(
    filter_kind: str = Query("all", alias="filter"),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    assigned_admin_id: UUID | None = None
    if filter_kind == "mine":
        assigned_admin_id = current_admin.id
    items, total = await service.list_conversations_for_admin(
        clinic_id=clinic_id,
        filter_kind=filter_kind,
        assigned_admin_id=assigned_admin_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    return AdminConversationsResponse(items=items, total=total)


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
async def get_conversation_messages(
    conversation_id: UUID,
    cursor: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    result = await service.list_messages_for_admin(clinic_id, conversation_id, cursor=cursor, limit=limit)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return result


@router.post("/conversations/{conversation_id}/messages", response_model=MessageDto, status_code=status.HTTP_201_CREATED)
async def send_admin_message(
    conversation_id: UUID,
    data: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    msg = await service.send_message_from_admin(
        clinic_id,
        conversation_id,
        admin_id=current_admin.id if current_admin else None,
        body=data.body,
        message_type=data.message_type,
        sticker_key=data.sticker_key,
    )
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message body/sticker or conversation not found",
        )
    return msg


@router.post(
    "/conversations/{conversation_id}/messages/upload",
    response_model=MessageDto,
    status_code=status.HTTP_201_CREATED,
)
async def send_admin_message_with_file(
    conversation_id: UUID,
    body: str = Form(""),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    try:
        raw = await file.read()
        msg = await service.send_message_from_admin_with_file(
            clinic_id,
            conversation_id,
            admin_id=current_admin.id,
            body=body,
            file_name=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            raw=raw,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой",
            ) from exc
        if code == "file_type_not_allowed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимый тип файла",
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from exc
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message or conversation not found",
        )
    return msg


@router.get("/conversations/{conversation_id}/attachments/{attachment_id}/file")
async def download_clinic_chat_attachment(
    conversation_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions()),
) -> Response:
    if admin_ctx.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется контекст клиники",
        )
    clinic_id = admin_ctx.clinic_id
    service = ChatService(session)
    payload = await service.get_clinic_chat_attachment_for_admin(clinic_id, conversation_id, attachment_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
    row, raw = payload
    allow_audio = "owner" in admin_ctx.roles
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


@router.post("/conversations/{conversation_id}/assign", response_model=AssignResponse)
async def assign_conversation(
    conversation_id: UUID,
    data: AssignRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    admin_id = data.admin_id if data else None
    service = ChatService(session)
    result = await service.assign_conversation(clinic_id, conversation_id, admin_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return result


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_admin_message(
    conversation_id: UUID,
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    ok = await service.delete_message_for_admin(clinic_id, conversation_id, message_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message or conversation not found")


@router.post("/conversations/{conversation_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_read_admin(
    conversation_id: UUID,
    body: MarkReadRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    up_to = body.up_to_message_id if body else None
    clinic_id: UUID = current_admin.clinic_id
    service = ChatService(session)
    ok = await service.mark_read_by_admin(clinic_id, conversation_id, up_to)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get(
    "/conversations/{conversation_id}/ai-summary",
    response_model=ConversationSummaryResponse,
)
async def get_ai_summary(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    rate_limiter=Depends(get_rate_limiter),
) -> ConversationSummaryResponse:
    clinic_id: UUID = current_admin.clinic_id
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:ai:summary:clinic:{clinic_id}",
            limit=settings.rate_ai_clinic_limit,
            window=settings.rate_ai_clinic_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов к AI. Попробуйте позже.",
        )
    service = ChatAiService(session)
    try:
        return await service.summarize_conversation(clinic_id, conversation_id)
    except ChatAiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post(
    "/conversations/{conversation_id}/ai-suggest-reply",
    response_model=SuggestReplyResponse,
)
async def get_ai_suggest_reply(
    conversation_id: UUID,
    body: SuggestReplyRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser | None = Depends(get_current_admin_optional),
    rate_limiter=Depends(get_rate_limiter),
) -> SuggestReplyResponse:
    clinic_id: UUID | None = current_admin.clinic_id if current_admin else None
    if clinic_id is not None:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:ai:suggest_reply:clinic:{clinic_id}",
                limit=settings.rate_ai_clinic_limit,
                window=settings.rate_ai_clinic_window_seconds,
            )
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов к AI. Попробуйте позже.",
            )
    service = ChatAiService(session)
    intent = body.intent if body else None
    admin_id = current_admin.id if current_admin else None
    try:
        return await service.suggest_reply(clinic_id, conversation_id, admin_id, intent)
    except ChatAiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
