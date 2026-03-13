"""SMTP email sender — implements NotificationSender for Email."""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailSenderError(Exception):
    """SMTP or configuration error."""

    pass


class EmailSender:
    """Send messages via SMTP (same interface as TelegramSender/SMSSender)."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
    ):
        self._host = (host or "").strip() or (settings.smtp_host or "").strip()
        self._port = port if port is not None else (settings.smtp_port or 587)
        self._user = (user or "").strip() or (settings.smtp_user or "").strip()
        self._password = (password or "").strip() or (settings.smtp_password or "").strip()
        self._from_email = (from_email or "").strip() or (
            (settings.smtp_from_email or "").strip()
        )

    def is_configured(self) -> bool:
        """Return True if host and credentials are set."""
        return bool(self._host and self._user and self._password)

    def _send_sync(
        self,
        *,
        email: str | None,
        message: str,
        template: str,
    ) -> None:
        """Synchronous send (runs in thread)."""
        to_addr = (email or "").strip()
        if not to_addr:
            raise EmailSenderError("No email address provided for Email")

        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = f"Уведомление ({template})"
        msg["From"] = self._from_email or self._user
        msg["To"] = to_addr

        with smtplib.SMTP(self._host, self._port) as server:
            server.starttls()
            server.login(self._user, self._password)
            server.sendmail(msg["From"], to_addr, msg.as_string())

        logger.info(
            "[email] sent",
            extra={"template": template, "to": to_addr.split("@")[0] + "@..."},
        )

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
        """Send message to email. Requires email address."""
        if not self.is_configured():
            raise EmailSenderError("SMTP (smtp_user/smtp_password) is not set")

        await asyncio.to_thread(
            self._send_sync,
            email=email,
            message=message,
            template=template,
        )
