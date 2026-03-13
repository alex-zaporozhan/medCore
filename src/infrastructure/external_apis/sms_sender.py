"""SMSC.ru HTTP API sender — implements NotificationSender for SMS."""

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from src.core.config import settings
from src.domain.interfaces.notification_sender import NotificationSender

logger = logging.getLogger(__name__)

SMSC_SEND_URL = "https://smsc.ru/sys/send.php"


class SMSSenderError(Exception):
    """SMSC API or configuration error."""

    pass


class SMSSender:
    """Send SMS via SMSC.ru HTTP API."""

    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
        sender: str | None = None,
    ):
        self._login = (login or "").strip() or (settings.smsc_login or "").strip()
        self._password = (password or "").strip() or (settings.smsc_password or "").strip()
        self._sender = (sender or "").strip() or (settings.smsc_sender or "").strip()

    def is_configured(self) -> bool:
        """Return True if login and password are set."""
        return bool(self._login and self._password)

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
        """Send SMS to phone. Requires phone number."""
        if not self.is_configured():
            raise SMSSenderError("SMSC_LOGIN or SMSC_PASSWORD is not set")

        phone_str = (phone or "").strip()
        if not phone_str:
            raise SMSSenderError("No phone number provided for SMS")

        params = {
            "login": self._login,
            "psw": self._password,
            "phones": phone_str,
            "mes": message,
            "fmt": 3,
        }
        if self._sender:
            params["sender"] = self._sender

        url = f"{SMSC_SEND_URL}?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json() if resp.text else {}
            if isinstance(data, dict) and data.get("error"):
                raise SMSSenderError(
                    str(data.get("error", "Unknown SMSC error"))
                )
        logger.info(
            "[sms] sent",
            extra={"template": template, "phone_last": phone_str[-4:]},
        )
