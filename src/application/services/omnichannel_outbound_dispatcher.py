"""Outbound Dispatcher for omnichannel messages (Phase 3).

Dispatches outbound messages to real providers: Telegram (sendMessage), Web-chat (push for long-poll).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.webchat_push_manager import get_webchat_push_manager
from src.core.config import settings
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class OmnichannelOutboundDispatcher:
    """Dispatcher for outbound omnichannel messages. Requires session to load chat/contact/channel."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dispatch_to_channel(self, message: Message) -> None:
        """Dispatch outbound message to underlying channel (Telegram, Web-chat, etc.)."""
        if not message.channel_id:
            logger.info(
                "OmnichannelOutboundDispatcher: no channel_id, skip delivery",
                extra={
                    "component": "omni_outbound_dispatcher",
                    "message_id": str(message.id),
                    "chat_id": str(message.chat_id),
                },
            )
            return

        result = await self.session.execute(
            select(OmniChat).where(OmniChat.id == message.chat_id).limit(1)
        )
        chat: OmniChat | None = result.scalar_one_or_none()
        if not chat:
            logger.warning(
                "OmnichannelOutboundDispatcher: chat not found",
                extra={"message_id": str(message.id), "chat_id": str(message.chat_id)},
            )
            return

        result = await self.session.execute(
            select(OmniChannel).where(OmniChannel.id == message.channel_id).limit(1)
        )
        channel: OmniChannel | None = result.scalar_one_or_none()
        if not channel:
            logger.warning(
                "OmnichannelOutboundDispatcher: channel not found",
                extra={"message_id": str(message.id), "channel_id": str(message.channel_id)},
            )
            return

        contact: OmniContact | None = None
        if chat.contact_id:
            result = await self.session.execute(
                select(OmniContact).where(OmniContact.id == chat.contact_id).limit(1)
            )
            contact = result.scalar_one_or_none()

        channel_type = (channel.type or "").upper()

        if channel_type == "TELEGRAM_BOT":
            await self._dispatch_telegram(message, chat, contact, channel)
        elif channel_type == "WEB_WIDGET":
            await self._dispatch_webchat(message)
        elif channel_type == "WEB_APP":
            await self._dispatch_web_app(message, chat, contact)
        else:
            logger.info(
                "OmnichannelOutboundDispatcher.dispatch_to_channel (no adapter)",
                extra={
                    "component": "omni_outbound_dispatcher",
                    "event": "dispatch_attempt",
                    "message_id": str(message.id),
                    "chat_id": str(message.chat_id),
                    "channel_type": channel_type,
                    "correlation_chat_id": str(message.chat_id),
                    "correlation_message_id": str(message.id),
                },
            )

    async def _dispatch_telegram(
        self,
        message: Message,
        chat: OmniChat,
        contact: OmniContact | None,
        channel: OmniChannel,
    ) -> None:
        """Send message via Telegram Bot API."""
        telegram_chat_id: str | None = None
        if contact and contact.external_ids and isinstance(contact.external_ids, dict):
            telegram_chat_id = (contact.external_ids.get("telegram_user_id") or "").strip() or None
        if not telegram_chat_id:
            logger.warning(
                "OmnichannelOutboundDispatcher: Telegram contact has no telegram_user_id",
                extra={"contact_id": str(contact.id) if contact else None, "message_id": str(message.id)},
            )
            return

        token: str | None = None
        from src.application.services.omnichannel_integrations_config_service import (
            OmnichannelIntegrationsConfigService,
        )
        config_svc = OmnichannelIntegrationsConfigService(self.session)
        raw = await config_svc.get_integration_secret(channel_id=channel.id)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and parsed.get("bot_token"):
                    token = (parsed["bot_token"] or "").strip() or None
            except (TypeError, ValueError):
                pass
            if not token and isinstance(raw, str) and raw.strip():
                token = raw.strip()
        if not token:
            token = (settings.telegram_bot_token or "").strip() or None
        if not token:
            logger.warning(
                "OmnichannelOutboundDispatcher: no Telegram token for channel",
                extra={"channel_id": str(channel.id), "message_id": str(message.id)},
            )
            return

        from src.application.services.omni_media_storage import OMNI_FILES_META_KEY, read_omni_file_bytes

        omni_files: list = []
        if isinstance(message.source_metadata, dict):
            lst = message.source_metadata.get(OMNI_FILES_META_KEY)
            if isinstance(lst, list):
                omni_files = lst

        async def _telegram_post_with_retries(
            build_request,
        ) -> bool:
            last_err: Exception | None = None
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        resp = await build_request(client)
                        resp.raise_for_status()
                    data = resp.json()
                    if not data.get("ok"):
                        logger.warning(
                            "OmnichannelOutboundDispatcher: Telegram API not ok",
                            extra={"message_id": str(message.id), "description": data.get("description")},
                        )
                        return False
                    meta = dict(message.source_metadata or {})
                    meta["delivery_status"] = "DELIVERED"
                    meta["delivery_channel"] = "TELEGRAM_BOT"
                    provider_payload = data.get("result") if isinstance(data.get("result"), dict) else None
                    if provider_payload and provider_payload.get("message_id") is not None:
                        meta["provider_message_id"] = str(provider_payload.get("message_id"))
                    message.source_metadata = meta
                    await self.session.flush()
                    return True
                except (httpx.HTTPStatusError, httpx.RequestError, OSError) as e:
                    last_err = e
                    if attempt < 2:
                        delay = 1 * (2**attempt)
                        logger.warning(
                            "OmnichannelOutboundDispatcher: Telegram send attempt failed, retrying",
                            extra={
                                "message_id": str(message.id),
                                "attempt": attempt + 1,
                                "error": str(e),
                                "delay_seconds": delay,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.exception(
                            "OmnichannelOutboundDispatcher: Telegram send failed after retries",
                            extra={"message_id": str(message.id), "error": str(last_err)},
                        )
                        return False
            return False

        if omni_files:
            cap_left = (message.content or "").strip()[:1024]
            first = True
            for f in omni_files:
                if not isinstance(f, dict):
                    continue
                raw_b = read_omni_file_bytes(str(f.get("storage_rel") or ""))
                if not raw_b:
                    continue
                fn = str(f.get("file_name") or "file")
                ct = (str(f.get("content_type") or "application/octet-stream")).lower()
                cap = cap_left if first else ""
                first = False

                def _build(client: httpx.AsyncClient, c=cap, r=raw_b, n=fn, t=ct):
                    tg = f"{TELEGRAM_API_BASE}/bot{token}"
                    if t.startswith("image/"):
                        return client.post(
                            f"{tg}/sendPhoto",
                            data={"chat_id": telegram_chat_id, "caption": c},
                            files={"photo": (n, r, t)},
                        )
                    if t.startswith("audio/") and ("ogg" in t or n.lower().endswith(".ogg")):
                        return client.post(
                            f"{tg}/sendVoice",
                            data={"chat_id": telegram_chat_id, "caption": c},
                            files={"voice": (n, r, t or "audio/ogg")},
                        )
                    return client.post(
                        f"{tg}/sendDocument",
                        data={"chat_id": telegram_chat_id, "caption": c},
                        files={"document": (n, r, t)},
                    )

                ok = await _telegram_post_with_retries(lambda cl: _build(cl))
                if not ok:
                    return
            logger.info(
                "OmnichannelOutboundDispatcher: Telegram media sent",
                extra={"message_id": str(message.id), "chat_id": str(message.chat_id)},
            )
            return

        text_body = (message.content or "").strip()
        if not text_body:
            logger.info(
                "OmnichannelOutboundDispatcher: Telegram skip empty text message",
                extra={"message_id": str(message.id)},
            )
            return

        url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": text_body}

        async def _send_text(client: httpx.AsyncClient):
            return await client.post(url, json=payload)

        if not await _telegram_post_with_retries(_send_text):
            return

        logger.info(
            "OmnichannelOutboundDispatcher: Telegram sent",
            extra={
                "component": "omni_outbound_dispatcher",
                "event": "telegram_sent",
                "message_id": str(message.id),
                "chat_id": str(message.chat_id),
                "correlation_chat_id": str(message.chat_id),
                "correlation_message_id": str(message.id),
            },
        )

    async def _dispatch_web_app(
        self,
        message: Message,
        chat: OmniChat,
        contact: OmniContact | None,
    ) -> None:
        """Write admin reply to PWA chat_messages and update Conversation."""
        if not contact or not isinstance(contact.external_ids, dict):
            logger.warning(
                "OmnichannelOutboundDispatcher: WEB_APP contact has no external_ids",
                extra={"message_id": str(message.id), "chat_id": str(chat.id)},
            )
            return
        patient_id_str = (contact.external_ids.get("patient_id") or "").strip()
        if not patient_id_str:
            logger.warning(
                "OmnichannelOutboundDispatcher: WEB_APP contact has no patient_id",
                extra={"message_id": str(message.id), "contact_id": str(contact.id)},
            )
            return
        try:
            patient_id = UUID(patient_id_str)
        except (ValueError, TypeError):
            logger.warning(
                "OmnichannelOutboundDispatcher: invalid patient_id in contact",
                extra={"message_id": str(message.id), "patient_id": patient_id_str},
            )
            return
        business_account_id = chat.business_account_id
        from src.core.datetime_utils import utc_now_naive
        from src.domain.entities.chat_message import ChatMessage
        from src.infrastructure.database.chat_message_repo_impl import ChatMessageRepositoryImpl
        from src.infrastructure.database.conversation_repo_impl import ConversationRepositoryImpl

        conv_repo = ConversationRepositoryImpl(self.session)
        msg_repo = ChatMessageRepositoryImpl(self.session)
        conv = await conv_repo.get_by_clinic_patient(business_account_id, patient_id)
        if conv is None:
            logger.warning(
                "OmnichannelOutboundDispatcher: no Conversation for WEB_APP patient, message not delivered to PWA",
                extra={
                    "message_id": str(message.id),
                    "chat_id": str(chat.id),
                    "patient_id": patient_id_str,
                },
            )
            return
        now = utc_now_naive()
        admin_uid = message.sender_admin_id if message.actor_type == "HUMAN_ADMIN" else None

        from src.application.services.omni_media_storage import (
            OMNI_FILES_META_KEY,
            read_omni_file_bytes,
            sanitize_omni_filename,
        )
        from src.domain.entities.chat_message_attachment import ChatMessageAttachment

        omni_files: list = []
        sm = message.source_metadata
        if isinstance(sm, dict):
            raw_list = sm.get(OMNI_FILES_META_KEY)
            if isinstance(raw_list, list):
                omni_files = raw_list

        # Не дублировать служебные подписи в PWA, если вложения уже копируются в clinic_chat.
        _pwa_placeholder_only = frozenset(
            {"", "[Изображение]", "[Вложение]", "[Голосовое сообщение]"},
        )
        body_val = (message.content or "").strip()
        if omni_files and body_val in _pwa_placeholder_only:
            body_val = ""

        admin_msg = ChatMessage(
            clinic_id=business_account_id,
            conversation_id=conv.id,
            patient_id=patient_id,
            admin_id=admin_uid,
            sender_type="admin",
            message_type="text",
            body=body_val,
            sticker_key=None,
            read_by_admin_at=None,
            read_by_patient_at=None,
        )
        await msg_repo.create(admin_msg)
        for f in omni_files:
            if not isinstance(f, dict):
                continue
            rel = f.get("storage_rel")
            if not rel:
                continue
            raw_bytes = read_omni_file_bytes(str(rel))
            if not raw_bytes:
                continue
            att_id = uuid.uuid4()
            safe = sanitize_omni_filename(str(f.get("file_name") or "file"))
            rel_chat = f"{business_account_id}/clinic_chat/{att_id}_{safe}"
            fs_path = Path(settings.staff_chat_upload_root) / rel_chat.replace("/", os.sep)
            fs_path.parent.mkdir(parents=True, exist_ok=True)
            fs_path.write_bytes(raw_bytes)
            self.session.add(
                ChatMessageAttachment(
                    id=att_id,
                    clinic_id=business_account_id,
                    message_id=admin_msg.id,
                    file_name=str(f.get("file_name") or "file")[:500],
                    content_type=str(f.get("content_type") or "application/octet-stream")[:128],
                    size_bytes=len(raw_bytes),
                    storage_path=rel_chat.replace("\\", "/"),
                )
            )

        conv.last_message_at = now
        conv.last_message_sender_type = "admin"
        conv.unread_by_patient_count = (conv.unread_by_patient_count or 0) + 1
        await conv_repo.update(conv)
        meta = dict(message.source_metadata or {})
        meta["delivery_status"] = "DELIVERED"
        meta["delivery_channel"] = "WEB_APP"
        message.source_metadata = meta
        await self.session.flush()
        logger.info(
            "OmnichannelOutboundDispatcher: WEB_APP reply written to PWA",
            extra={
                "component": "omni_outbound_dispatcher",
                "event": "web_app_delivered",
                "message_id": str(message.id),
                "chat_id": str(message.chat_id),
                "conversation_id": str(conv.id),
                "correlation_chat_id": str(message.chat_id),
                "correlation_message_id": str(message.id),
            },
        )

    async def _dispatch_webchat(self, message: Message) -> None:
        """Notify webchat long-poll waiters so widget can receive the message."""
        manager = get_webchat_push_manager()
        manager.notify(
            chat_id=message.chat_id,
            message_id=message.id,
            content=message.content or "",
            created_at=message.created_at,
            actor_type=message.actor_type or "SYSTEM",
        )
        meta = dict(message.source_metadata or {})
        meta["delivery_status"] = "DELIVERED"
        meta["delivery_channel"] = "WEB_WIDGET"
        message.source_metadata = meta
        await self.session.flush()
        logger.info(
            "OmnichannelOutboundDispatcher: Webchat push notified",
            extra={
                "component": "omni_outbound_dispatcher",
                "event": "webchat_notified",
                "message_id": str(message.id),
                "chat_id": str(message.chat_id),
                "correlation_chat_id": str(message.chat_id),
                "correlation_message_id": str(message.id),
            },
        )

    @staticmethod
    def get_correlation_ids(message: Message) -> dict[str, str]:
        """Return correlation identifiers to be reused in logs/metrics."""
        return {
            "correlation_chat_id": str(message.chat_id),
            "correlation_message_id": str(message.id),
        }
