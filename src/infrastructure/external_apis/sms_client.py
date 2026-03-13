"""SMS client for sending auth codes via external provider (SMSC.ru-compatible API).

This client is intentionally minimal and focused on:
- avoiding leakage of full phone numbers and message texts in logs;
- being easy to disable in non-production environments;
- failing with a generic error message without exposing provider internals.
"""

from __future__ import annotations

import logging
from typing import Final

import httpx

from src.core.config import settings


logger = logging.getLogger(__name__)


class SmsClientError(Exception):
    """Errors when calling external SMS provider."""

    pass


class SmsClient:
    """Simple async SMS client for a single provider (SMSC.ru-style HTTP API)."""

    _BASE_URL: Final[str] = "https://smsc.ru/sys/send.php"

    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        timeout_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._login = (login or settings.smsc_login or "").strip()
        self._password = (password or settings.smsc_password or "").strip()
        self._sender = (sender or settings.smsc_sender or "").strip()
        self._timeout = timeout_seconds or 10
        # Explicit feature flag so that in dev/test we do not accidentally send real SMS.
        self._enabled = enabled if enabled is not None else bool(settings.smsc_login and settings.smsc_password)

    def is_configured(self) -> bool:
        """Return True if credentials are present and sending is enabled."""
        return self._enabled and bool(self._login and self._password)

    async def send_sms(self, phone: str, text: str) -> None:
        """Send SMS with the given text to a single phone number.

        Raises SmsClientError on any failure.
        """
        if not self.is_configured():
            raise SmsClientError("SMS provider is not configured or disabled")

        masked_phone = f"...{phone[-4:]}" if phone and len(phone) >= 4 else None

        params: dict[str, str] = {
            "login": self._login,
            "psw": self._password,
            "phones": phone,
            "mes": text,
            "fmt": "3",  # JSON
        }
        if self._sender:
            params["sender"] = self._sender

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self._BASE_URL, data=params)
        except Exception as exc:  # pragma: no cover - network-related
            logger.exception(
                "SMS send failed (network)",
                extra={
                    "phone_last4": masked_phone,
                },
            )
            raise SmsClientError("Network error when sending SMS") from exc

        # Basic provider-level error check without logging sensitive payloads.
        if resp.status_code != 200:
            logger.error(
                "SMS send failed (HTTP status)",
                extra={
                    "status_code": resp.status_code,
                    "phone_last4": masked_phone,
                },
            )
            raise SmsClientError("SMS provider returned non-200 status")

        try:
            data = resp.json()
        except Exception:  # pragma: no cover - defensive
            # If provider changed the format, treat as failure.
            logger.error(
                "SMS send failed: unexpected response format",
                extra={
                    "phone_last4": masked_phone,
                },
            )
            raise SmsClientError("SMS provider returned invalid response")

        # SMSC.ru JSON success response normally has 'id' and 'cnt'; errors have 'error'.
        if isinstance(data, dict) and data.get("error"):
            logger.error(
                "SMS send failed (provider error)",
                extra={
                    "phone_last4": masked_phone,
                    "error_code": data.get("error_code"),
                },
            )
            raise SmsClientError("SMS provider reported an error")

        logger.info(
            "SMS sent successfully",
            extra={
                "phone_last4": masked_phone,
            },
        )

