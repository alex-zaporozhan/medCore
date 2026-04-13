"""Опциональный webhook при новой публичной заявке (CRM / мессенджеры операторов)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.core.config import settings
from src.core.metrics import enterprise_lead_notify_webhook_total

logger = logging.getLogger(__name__)


async def send_enterprise_lead_created_webhook(*, payload: dict[str, Any]) -> None:
    """POST JSON на ENTERPRISE_LEAD_NOTIFY_WEBHOOK_URL; не бросает наружу (best-effort)."""
    url = (settings.enterprise_lead_notify_webhook_url or "").strip()
    if not url:
        return
    headers: dict[str, str] = {"Content-Type": "application/json"}
    secret = (settings.enterprise_lead_notify_webhook_secret or "").strip()
    if secret:
        headers["X-Enterprise-Lead-Notify-Secret"] = secret
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if 200 <= resp.status_code < 300:
            enterprise_lead_notify_webhook_total.labels(result="ok").inc()
        else:
            enterprise_lead_notify_webhook_total.labels(result="failed").inc()
            logger.warning(
                "enterprise_lead_notify_webhook_http_error",
                extra={"status_code": resp.status_code},
            )
    except Exception as exc:  # noqa: BLE001
        enterprise_lead_notify_webhook_total.labels(result="failed").inc()
        logger.warning("enterprise_lead_notify_webhook_error", extra={"error": str(exc)})
