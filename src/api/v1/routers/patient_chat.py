"""Patient chat API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.core.patient_messages import CHAT_EMPTY_MESSAGE
from src.application.dto.chat_dto import (
    ConversationResponse,
    MarkReadRequest,
    MessageDto,
    MessagesResponse,
    SendMessageRequest,
)
from src.application.services.chat_service import ChatService

logger = logging.getLogger(__name__)


def _handle_chat_error(exc: Exception, context: str) -> str:
    """Build safe user-facing message and log full traceback."""
    msg = str(exc).strip().lower()
    logger.exception("Patient chat %s failed: %s", context, exc)
    if "relation" in msg and ("does not exist" in msg or "not exist" in msg):
        return "Таблицы чата не найдены. Выполните миграции: alembic upgrade head"
    if "no such table" in msg or "undefined_table" in msg:
        return "Таблицы чата не найдены. Выполните миграции: alembic upgrade head"
    return "Внутренняя ошибка при обработке чата. Проверьте логи бэкенда."


router = APIRouter(prefix="/patient/chat", tags=["patient-chat"])


@router.get("/conversation", response_model=ConversationResponse)
async def get_or_create_conversation(
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    service = ChatService(session)
    try:
        clinic_id = current_patient.clinic_id
        return await service.get_or_create_conversation_for_patient(clinic_id, current_patient.id)
    except IntegrityError as e:
        logger.warning("Patient chat conversation create failed (patient/clinic)", extra={"patient_id": str(patient_id), "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient or clinic not found",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_handle_chat_error(e, "get_or_create_conversation"),
        ) from e


@router.get("/conversation/messages", response_model=MessagesResponse)
async def get_conversation_messages(
    cursor: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    service = ChatService(session)
    try:
        clinic_id = current_patient.clinic_id
        return await service.list_messages_for_patient(clinic_id, current_patient.id, cursor=cursor, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_handle_chat_error(e, "get_conversation_messages"),
        ) from e


@router.post("/conversation/messages", response_model=MessageDto, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    service = ChatService(session)
    try:
        clinic_id = current_patient.clinic_id
        msg = await service.send_message_from_patient(
            clinic_id,
            current_patient.id,
            body=data.body,
            message_type=data.message_type,
            sticker_key=data.sticker_key,
        )
    except IntegrityError as e:
        logger.warning("Patient chat send message failed", extra={"patient_id": str(patient_id), "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation or patient not found",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_handle_chat_error(e, "send_message"),
        ) from e
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHAT_EMPTY_MESSAGE,
        )
    return msg


@router.delete("/conversation/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_message(
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    service = ChatService(session)
    try:
        clinic_id = current_patient.clinic_id
        ok = await service.delete_message_for_patient(clinic_id, current_patient.id, message_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_handle_chat_error(e, "delete_message"),
        ) from e
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found or cannot delete")

@router.post("/conversation/mark-read", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_read(
    body: MarkReadRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    up_to = body.up_to_message_id if body else None
    service = ChatService(session)
    try:
        clinic_id = current_patient.clinic_id
        ok = await service.mark_read_by_patient(clinic_id, current_patient.id, up_to)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_handle_chat_error(e, "mark_read"),
        ) from e
    if not ok:
        # Conversation may not exist yet; idempotent no-op
        return
