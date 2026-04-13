"""Redis pub/sub for omnichannel inbox realtime (ARCH §6)."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from src.core.metrics import omni_realtime_publish_failed_total
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)

OMNI_EVENTS_CHANNEL_PREFIX = "omni:events"


async def publish_omni_message_created(
    *,
    clinic_id: UUID,
    chat_id: UUID,
    message_id: UUID,
) -> None:
    """Notify SSE subscribers for clinic (no message content)."""
    payload = json.dumps(
        {
            "type": "message.created",
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "clinic_id": str(clinic_id),
        },
        separators=(",", ":"),
    )
    channel = f"{OMNI_EVENTS_CHANNEL_PREFIX}:{clinic_id}"
    try:
        redis = await get_redis()
        await redis.publish(channel, payload)
    except Exception as exc:  # noqa: BLE001
        omni_realtime_publish_failed_total.labels(event="message_created").inc()
        logger.warning(
            "omni realtime publish failed",
            extra={"channel": channel, "error": str(exc)},
        )


async def publish_omni_chat_updated(
    *,
    clinic_id: UUID,
    chat_id: UUID,
    reason: str,
) -> None:
    """Notify SSE subscribers that chat meta/status changed."""
    payload = json.dumps(
        {
            "type": "chat.updated",
            "chat_id": str(chat_id),
            "clinic_id": str(clinic_id),
            "reason": str(reason)[:64],
        },
        separators=(",", ":"),
    )
    channel = f"{OMNI_EVENTS_CHANNEL_PREFIX}:{clinic_id}"
    try:
        redis = await get_redis()
        await redis.publish(channel, payload)
    except Exception as exc:  # noqa: BLE001
        omni_realtime_publish_failed_total.labels(event="chat_updated").inc()
        logger.warning(
            "omni realtime publish failed",
            extra={"channel": channel, "error": str(exc)},
        )
