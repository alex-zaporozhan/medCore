"""Telegram Bot API sender — implements NotificationSender for Telegram."""

import logging
from typing import Any

import httpx

from src.core.config import settings
from src.domain.interfaces.notification_sender import NotificationSender

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramSenderError(Exception):
    """Telegram API or configuration error."""

    pass


class TelegramSender:
    """Send messages via Telegram Bot API (sendMessage)."""

    def __init__(
        self,
        token: str | None = None,
        admin_chat_id: str | None = None,
    ):
        self._token = (token or "").strip() or (settings.telegram_bot_token or "").strip()
        self._admin_chat_id = (admin_chat_id or "").strip() or (
            (settings.telegram_admin_chat_id or "").strip()
        )

    def is_configured(self) -> bool:
        """Return True if bot token is set."""
        return bool(self._token)

    async def send(
        self,
        *,
        chat_id: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        message: str,
        template: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Send message to Telegram chat. Uses chat_id or fallback to admin_chat_id."""
        if not self.is_configured():
            raise TelegramSenderError("TELEGRAM_BOT_TOKEN is not set")

        target_chat = (chat_id or "").strip() or self._admin_chat_id
        if not target_chat:
            raise TelegramSenderError("No chat_id and TELEGRAM_ADMIN_CHAT_ID is not set")

        url = f"{TELEGRAM_API_BASE}/bot{self._token}/sendMessage"
        payload = {"chat_id": target_chat, "text": message}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise TelegramSenderError(
                    data.get("description", "Telegram API returned not ok")
                )
        logger.info(
            "[telegram] sent",
            extra={"template": template, "chat_id": target_chat},
        )
