"""Notification delivery orchestrator: fallback chain Telegram → SMS → log."""

import logging
from typing import Any

from src.infrastructure.external_apis.email_sender import EmailSender, EmailSenderError
from src.infrastructure.external_apis.sms_sender import SMSSender, SMSSenderError
from src.infrastructure.external_apis.telegram_sender import TelegramSender, TelegramSenderError

logger = logging.getLogger(__name__)


def _get_delivery_service():
    """Return shared sender instances (stateless, read from settings)."""
    return TelegramSender(), SMSSender(), EmailSender()


async def send_with_fallback(
    *,
    chat_id: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    message: str,
    template: str,
    meta: dict[str, Any] | None = None,
    preferred_channel: str = "sms",
) -> tuple[bool, str | None]:
    """
    Try to deliver via preferred_channel, then fallback (telegram → sms → log).
    Returns (success, error_message). On success error_message is None.
    If no sender is configured or all fail, logs and returns (True, None) so we do not crash.
    """
    meta = meta or {}
    telegram_sender, sms_sender, email_sender = _get_delivery_service()

    order: list[str]
    if preferred_channel == "telegram":
        order = ["telegram", "sms"]
    elif preferred_channel == "email":
        order = ["email", "telegram", "sms"]
    else:
        order = ["sms", "telegram"]

    last_error: str | None = None
    attempted_any = False

    for channel in order:
        if channel == "telegram":
            if not telegram_sender.is_configured():
                last_error = "Telegram not configured"
                continue
            attempted_any = True
            try:
                await telegram_sender.send(
                    chat_id=chat_id,
                    phone=phone,
                    email=email,
                    message=message,
                    template=template,
                    meta=meta,
                )
                return True, None
            except TelegramSenderError as e:
                last_error = str(e)
                logger.warning(
                    "[notification] telegram failed, fallback",
                    extra={"template": template, "error": last_error},
                )
                continue
        if channel == "sms":
            if not sms_sender.is_configured():
                last_error = "SMS not configured"
                continue
            if not (phone or "").strip():
                last_error = "No phone for SMS"
                continue
            attempted_any = True
            try:
                await sms_sender.send(
                    chat_id=chat_id,
                    phone=phone,
                    email=email,
                    message=message,
                    template=template,
                    meta=meta,
                )
                return True, None
            except SMSSenderError as e:
                last_error = str(e)
                logger.warning(
                    "[notification] sms failed, fallback",
                    extra={"template": template, "error": last_error},
                )
                continue
        if channel == "email":
            if not email_sender.is_configured():
                last_error = "Email not configured"
                continue
            if not (email or "").strip():
                last_error = "No email for Email channel"
                continue
            attempted_any = True
            try:
                await email_sender.send(
                    chat_id=chat_id,
                    phone=phone,
                    email=email,
                    message=message,
                    template=template,
                    meta=meta,
                )
                return True, None
            except EmailSenderError as e:
                last_error = str(e)
                logger.warning(
                    "[notification] email failed, fallback",
                    extra={"template": template, "error": last_error},
                )
                continue

    if attempted_any:
        logger.error(
            "[notification] all channels failed",
            extra={"template": template, "error": last_error},
        )
        return False, last_error or "All channels failed"

    logger.info(
        "[notification] delivered via log only (no sender configured)",
        extra={
            "template": template,
            "channel": preferred_channel,
            "message_preview": message[:80],
        },
    )
    return True, None
