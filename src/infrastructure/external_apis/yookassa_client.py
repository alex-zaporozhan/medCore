"""YooKassa (ЮKassa) API client for creating and checking payments."""

import base64
import logging
from decimal import Decimal
from uuid import UUID

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"


class YooKassaClientError(Exception):
    """YooKassa API or validation error."""

    pass


class YooKassaClient:
    """Sync client for YooKassa API v3 (used from async code via run_in_executor or from Celery)."""

    def __init__(
        self,
        shop_id: str | None = None,
        secret_key: str | None = None,
    ):
        self.shop_id = shop_id or settings.yookassa_shop_id
        self.secret_key = secret_key or settings.yookassa_secret_key
        self._auth = base64.b64encode(
            f"{self.shop_id}:{self.secret_key}".encode()
        ).decode()

    def is_configured(self) -> bool:
        """Return True if shop_id and secret_key are set."""
        return bool(self.shop_id and self.secret_key)

    def create_payment(
        self,
        amount: Decimal,
        return_url: str,
        description: str,
        booking_id: UUID,
        currency: str = "RUB",
    ) -> tuple[str, str]:
        """
        Create payment in YooKassa. Returns (provider_payment_id, confirmation_url).
        Raises YooKassaClientError on API error or if not configured.
        """
        if not self.is_configured():
            logger.warning("YooKassa not configured (missing shop_id or secret_key)")
            raise YooKassaClientError("YooKassa is not configured")

        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency,
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "description": description[:255],
            "metadata": {"booking_id": str(booking_id)},
            "capture": True,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{YOOKASSA_API_BASE}/payments",
                json=payload,
                headers={
                    "Idempotence-Key": f"{booking_id}",
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._auth}",
                },
            )

        if response.status_code != 200:
            logger.error(
                "YooKassa create payment failed",
                extra={
                    "status_code": response.status_code,
                    "body": response.text[:500],
                    "booking_id": str(booking_id),
                },
            )
            raise YooKassaClientError(
                f"YooKassa API error: {response.status_code} {response.text[:200]}"
            )

        data = response.json()
        pid = data.get("id")
        confirmation = data.get("confirmation") or {}
        url = confirmation.get("confirmation_url") or ""

        if not pid or not url:
            raise YooKassaClientError("YooKassa response missing id or confirmation_url")

        logger.info(
            "YooKassa payment created",
            extra={"provider_payment_id": pid, "booking_id": str(booking_id)},
        )
        return pid, url

    def create_platform_subscription_payment(
        self,
        amount: Decimal,
        return_url: str,
        description: str,
        signup_intent_id: UUID,
        idempotence_key: str,
    ) -> tuple[str, str]:
        """
        Create payment for SaaS platform signup (contour B). Metadata carries signup_intent_id for webhooks.
        """
        if not self.is_configured():
            logger.warning("YooKassa not configured (missing shop_id or secret_key)")
            raise YooKassaClientError("YooKassa is not configured")

        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "description": description[:255],
            "metadata": {
                "signup_intent_id": str(signup_intent_id),
                "kind": "platform_saas_subscription",
            },
            "capture": True,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{YOOKASSA_API_BASE}/payments",
                json=payload,
                headers={
                    "Idempotence-Key": idempotence_key[:200],
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._auth}",
                },
            )

        if response.status_code != 200:
            logger.error(
                "YooKassa platform subscription payment create failed",
                extra={
                    "status_code": response.status_code,
                    "body": response.text[:500],
                    "signup_intent_id": str(signup_intent_id),
                },
            )
            raise YooKassaClientError(
                f"YooKassa API error: {response.status_code} {response.text[:200]}"
            )

        data = response.json()
        pid = data.get("id")
        confirmation = data.get("confirmation") or {}
        url = confirmation.get("confirmation_url") or ""

        if not pid or not url:
            raise YooKassaClientError("YooKassa response missing id or confirmation_url")

        logger.info(
            "YooKassa platform subscription payment created",
            extra={"provider_payment_id": pid, "signup_intent_id": str(signup_intent_id)},
        )
        return str(pid), url

    def get_payment(self, provider_payment_id: str) -> dict:
        """
        Fetch payment by ID from YooKassa. Returns raw payment object.
        Raises YooKassaClientError on API error or if not configured.
        """
        if not self.is_configured():
            raise YooKassaClientError("YooKassa is not configured")

        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{YOOKASSA_API_BASE}/payments/{provider_payment_id}",
                headers={
                    "Authorization": f"Basic {self._auth}",
                },
            )

        if response.status_code != 200:
            logger.warning(
                "YooKassa get payment failed",
                extra={"status_code": response.status_code, "payment_id": provider_payment_id},
            )
            raise YooKassaClientError(
                f"YooKassa API error: {response.status_code}"
            )

        return response.json()
