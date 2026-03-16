"""Chat service."""

import logging
from uuid import UUID

from src.core.datetime_utils import utc_now_naive

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.chat_dto import (
    AdminConversationListItemDto,
    AssignResponse,
    ConversationResponse,
    MessageDto,
    MessagesResponse,
)
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.conversation import Conversation
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.chat_message_repository import ChatMessageRepository
from src.domain.interfaces.repositories.conversation_repository import ConversationRepository
from src.infrastructure.database.chat_message_repo_impl import ChatMessageRepositoryImpl
from src.infrastructure.database.conversation_repo_impl import ConversationRepositoryImpl

logger = logging.getLogger(__name__)

BODY_MAX_LENGTH = 2000
MESSAGES_DEFAULT_LIMIT = 50
MESSAGES_MAX_LIMIT = 200


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conv_repo: ConversationRepository = ConversationRepositoryImpl(session)
        self.msg_repo: ChatMessageRepository = ChatMessageRepositoryImpl(session)

    async def get_or_create_conversation_for_patient(
        self, clinic_id: UUID, patient_id: UUID
    ) -> ConversationResponse:
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient_id,
                assigned_admin_id=None,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            conv = await self.conv_repo.create(conv)
        return ConversationResponse(
            conversation_id=conv.id,
            unread_by_patient_count=conv.unread_by_patient_count,
            unread_by_admin_count=conv.unread_by_admin_count,
            last_message_at=conv.last_message_at,
        )

    async def list_messages_for_patient(
        self, clinic_id: UUID, patient_id: UUID, cursor: UUID | None, limit: int
    ) -> MessagesResponse:
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            return MessagesResponse(items=[], next_cursor=None)
        if conv.clinic_id != clinic_id:
            return MessagesResponse(items=[], next_cursor=None)
        limit = min(max(limit, 1), MESSAGES_MAX_LIMIT) if limit else MESSAGES_DEFAULT_LIMIT
        if cursor is None:
            rows = await self.msg_repo.list_by_conversation(conv.id, cursor=None, limit=limit, ascending=False)
            items = list(reversed(rows[:limit]))
            next_cursor = items[0].id if items and len(rows) > limit else None
        else:
            rows = await self.msg_repo.list_by_conversation(conv.id, cursor=cursor, limit=limit + 1, ascending=True)
            items = rows[:limit]
            next_cursor = rows[limit].id if len(rows) > limit else None
        dtos = [
            MessageDto(
                id=m.id,
                sender_type=m.sender_type,
                message_type=getattr(m, "message_type", "text"),
                body=m.body,
                sticker_key=getattr(m, "sticker_key", None),
                created_at=m.created_at,
                is_mine=(m.sender_type == "patient"),
            )
            for m in items
        ]
        return MessagesResponse(items=dtos, next_cursor=next_cursor)

    async def send_message_from_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        body: str,
        message_type: str = "text",
        sticker_key: str | None = None,
    ) -> MessageDto | None:
        if message_type == "sticker":
            if not sticker_key or not sticker_key.strip() or len(sticker_key.strip()) > 255:
                return None
            body_val = ""
        else:
            body = (body or "").strip()
            if not body or len(body) > BODY_MAX_LENGTH:
                return None
            body_val = body
            sticker_key = None
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient_id,
                assigned_admin_id=None,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            conv = await self.conv_repo.create(conv)
        now = utc_now_naive()
        msg = ChatMessage(
            clinic_id=clinic_id,
            conversation_id=conv.id,
            patient_id=patient_id,
            admin_id=None,
            sender_type="patient",
            message_type=message_type,
            body=body_val,
            sticker_key=sticker_key.strip() if sticker_key else None,
            read_by_admin_at=None,
            read_by_patient_at=None,
        )
        msg = await self.msg_repo.create(msg)
        conv.last_message_at = now
        conv.last_message_sender_type = "patient"
        conv.unread_by_admin_count = (conv.unread_by_admin_count or 0) + 1
        await self.conv_repo.update(conv)
        await self._bridge_patient_message_to_omni(clinic_id, patient_id, conv.id, msg)
        logger.info("Chat message from patient", extra={"conversation_id": str(conv.id), "message_id": str(msg.id)})
        return MessageDto(
            id=msg.id,
            sender_type=msg.sender_type,
            message_type=msg.message_type,
            body=msg.body,
            sticker_key=msg.sticker_key,
            created_at=msg.created_at if msg.created_at is not None else now,
            is_mine=True,
        )

    async def _bridge_patient_message_to_omni(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        conversation_id: UUID,
        msg: ChatMessage,
    ) -> None:
        """Bridge patient PWA message to omnichannel (WEB_APP) so it appears in Unified Chat."""
        from src.application.services.omnichannel_chat_service import OmnichannelChatService

        result = await self.session.execute(select(Patient).where(Patient.id == patient_id).limit(1))
        patient: Patient | None = result.scalar_one_or_none()
        full_name = patient.full_name if patient else None
        primary_phone = patient.phone if patient else None

        omni_svc = OmnichannelChatService(self.session)
        contact = await omni_svc.get_or_create_contact_for_patient(
            business_account_id=clinic_id,
            patient_id=patient_id,
            full_name=full_name,
            primary_phone=primary_phone,
        )
        channel_id = await omni_svc.get_or_create_channel_for_provider(clinic_id, "WEB_APP")
        if not channel_id:
            logger.warning(
                "Unified chat bridge: WEB_APP channel not created",
                extra={"clinic_id": str(clinic_id), "message_id": str(msg.id)},
            )
            return
        chat = await omni_svc.get_or_create_chat(clinic_id, contact, channel_id=channel_id)
        external_message_id = f"patient_msg_{conversation_id}_{msg.id}"
        if await omni_svc.exists_inbound_by_external_id(chat.id, "WEB_APP", external_message_id):
            return
        content = (msg.body or "").strip() or (f"[{msg.message_type}]" if msg.message_type != "text" else "")
        await omni_svc.create_inbound_message(
            chat=chat,
            contact=contact,
            content=content,
            channel_id=channel_id,
            source_metadata={"provider": "WEB_APP", "external_message_id": external_message_id},
        )

    async def mark_read_by_patient(
        self, clinic_id: UUID, patient_id: UUID, up_to_message_id: UUID | None
    ) -> bool:
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None or conv.clinic_id != clinic_id:
            return False
        n = await self.msg_repo.mark_read_by_patient_up_to(conv.id, up_to_message_id)
        if n > 0:
            conv.unread_by_patient_count = max(0, (conv.unread_by_patient_count or 0) - n)
            await self.conv_repo.update(conv)
        return True

    async def list_conversations_for_admin(
        self,
        clinic_id: UUID,
        filter_kind: str,
        assigned_admin_id: UUID | None,
        search: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[AdminConversationListItemDto], int]:
        convs, total = await self.conv_repo.list_for_clinic(
            clinic_id=clinic_id,
            filter_kind=filter_kind or "all",
            assigned_admin_id=assigned_admin_id,
            search=search,
            skip=skip,
            limit=limit,
        )
        from src.domain.entities.patient import Patient

        patient_ids = [c.patient_id for c in convs]
        patients_map: dict[UUID, Patient] = {}
        if patient_ids:
            result = await self.session.execute(select(Patient).where(Patient.id.in_(patient_ids)))
            for p in result.scalars().all():
                patients_map[p.id] = p
        items = []
        for c in convs:
            p = patients_map.get(c.patient_id)
            items.append(
                AdminConversationListItemDto(
                    conversation_id=c.id,
                    patient_id=c.patient_id,
                    patient_name=p.full_name if p else None,
                    patient_phone=p.phone if p else "",
                    assigned_admin_id=c.assigned_admin_id,
                    assigned_admin_name=None,
                    last_message_at=c.last_message_at,
                    last_message_sender_type=c.last_message_sender_type,
                    unread_by_admin_count=c.unread_by_admin_count or 0,
                )
            )
        return items, total

    async def list_messages_for_admin(
        self, clinic_id: UUID, conversation_id: UUID, cursor: UUID | None, limit: int
    ) -> MessagesResponse | None:
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv is None or conv.clinic_id != clinic_id:
            return None
        limit = min(max(limit, 1), MESSAGES_MAX_LIMIT) if limit else MESSAGES_DEFAULT_LIMIT
        if cursor is None:
            rows = await self.msg_repo.list_by_conversation(conv.id, cursor=None, limit=limit + 1, ascending=False)
            items = list(reversed(rows[:limit]))
            next_cursor = items[0].id if items and len(rows) > limit else None
        else:
            rows = await self.msg_repo.list_by_conversation(conv.id, cursor=cursor, limit=limit + 1, ascending=True)
            items = rows[:limit]
            next_cursor = rows[limit].id if len(rows) > limit else None
        dtos = [
            MessageDto(
                id=m.id,
                sender_type=m.sender_type,
                message_type=getattr(m, "message_type", "text"),
                body=m.body,
                sticker_key=getattr(m, "sticker_key", None),
                created_at=m.created_at,
                is_mine=(m.sender_type == "admin"),
            )
            for m in items
        ]
        return MessagesResponse(items=dtos, next_cursor=next_cursor)

    async def list_messages_for_admin_by_patient(
        self, clinic_id: UUID, patient_id: UUID, cursor: UUID | None, limit: int
    ) -> MessagesResponse:
        """Return messages for the patient's conversation; empty list if no conversation."""
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None:
            return MessagesResponse(items=[], next_cursor=None)
        result = await self.list_messages_for_admin(clinic_id, conv.id, cursor=cursor, limit=limit)
        return result if result is not None else MessagesResponse(items=[], next_cursor=None)

    async def send_message_from_admin(
        self,
        clinic_id: UUID,
        conversation_id: UUID,
        admin_id: UUID | None,
        body: str,
        message_type: str = "text",
        sticker_key: str | None = None,
    ) -> MessageDto | None:
        if message_type == "sticker":
            if not sticker_key or not sticker_key.strip() or len(sticker_key.strip()) > 255:
                return None
            body_val = ""
        else:
            body = (body or "").strip()
            if not body or len(body) > BODY_MAX_LENGTH:
                return None
            body_val = body
            sticker_key = None
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv is None or conv.clinic_id != clinic_id:
            return None
        now = utc_now_naive()
        msg = ChatMessage(
            clinic_id=clinic_id,
            conversation_id=conv.id,
            patient_id=conv.patient_id,
            admin_id=admin_id,
            sender_type="admin",
            message_type=message_type,
            body=body_val,
            sticker_key=sticker_key.strip() if sticker_key else None,
            read_by_admin_at=None,
            read_by_patient_at=None,
        )
        msg = await self.msg_repo.create(msg)
        conv.last_message_at = now
        conv.last_message_sender_type = "admin"
        conv.unread_by_patient_count = (conv.unread_by_patient_count or 0) + 1
        await self.conv_repo.update(conv)
        logger.info("Chat message from admin", extra={"conversation_id": str(conv.id), "message_id": str(msg.id)})
        return MessageDto(
            id=msg.id,
            sender_type=msg.sender_type,
            message_type=msg.message_type,
            body=msg.body,
            sticker_key=msg.sticker_key,
            created_at=msg.created_at if msg.created_at is not None else now,
            is_mine=True,
        )

    async def assign_conversation(
        self, clinic_id: UUID, conversation_id: UUID, admin_id: UUID | None
    ) -> AssignResponse | None:
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv is None or conv.clinic_id != clinic_id:
            return None
        conv.assigned_admin_id = admin_id
        await self.conv_repo.update(conv)
        return AssignResponse(conversation_id=conv.id, assigned_admin_id=conv.assigned_admin_id)

    async def mark_read_by_admin(
        self, clinic_id: UUID, conversation_id: UUID, up_to_message_id: UUID | None
    ) -> bool:
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv is None or conv.clinic_id != clinic_id:
            return False
        n = await self.msg_repo.mark_read_by_admin_up_to(conv.id, up_to_message_id)
        if n > 0:
            conv.unread_by_admin_count = max(0, (conv.unread_by_admin_count or 0) - n)
            await self.conv_repo.update(conv)
        return True

    async def delete_message_for_patient(
        self, clinic_id: UUID, patient_id: UUID, message_id: UUID
    ) -> bool:
        """Soft-delete a message. Patient can delete only their own messages."""
        conv = await self.conv_repo.get_by_clinic_patient(clinic_id, patient_id)
        if conv is None or conv.clinic_id != clinic_id:
            return False
        msg = await self.msg_repo.get_by_id_include_deleted(message_id)
        if msg is None or msg.conversation_id != conv.id or msg.sender_type != "patient" or msg.patient_id != patient_id:
            return False
        if msg.deleted_at is not None:
            return True
        msg.deleted_at = utc_now_naive()
        await self.msg_repo.update(msg)
        return True

    async def delete_message_for_admin(
        self, clinic_id: UUID, conversation_id: UUID, message_id: UUID
    ) -> bool:
        """Soft-delete a message. Admin can delete any message in the conversation."""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv is None or conv.clinic_id != clinic_id:
            return False
        msg = await self.msg_repo.get_by_id_include_deleted(message_id)
        if msg is None or msg.conversation_id != conv.id:
            return False
        if msg.deleted_at is not None:
            return True
        msg.deleted_at = utc_now_naive()
        await self.msg_repo.update(msg)
        return True
