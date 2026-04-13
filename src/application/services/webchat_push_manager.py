"""Webchat long-poll wake: in-process events and optional Redis fan-out (multi-replica)."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.metrics import webchat_redis_fanout_total

logger = logging.getLogger(__name__)

REDIS_NOTIFY_PREFIX = "webchat:notify:"


@dataclass
class WebchatPushItem:
    message_id: UUID
    content: str
    created_at: datetime
    actor_type: str


class WebchatPushManager:
    """Singleton: pending messages per chat_id and asyncio.Event for long-poll wake-up."""

    _events: dict[UUID, asyncio.Event]
    _pending: dict[UUID, list[WebchatPushItem]]

    def __init__(self) -> None:
        self._events = {}
        self._pending = defaultdict(list)

    def _get_or_create_event(self, chat_id: UUID) -> asyncio.Event:
        if chat_id not in self._events:
            self._events[chat_id] = asyncio.Event()
        return self._events[chat_id]

    def notify(self, chat_id: UUID, message_id: UUID, content: str, created_at: datetime, actor_type: str) -> None:
        """Called when an outbound message is dispatched to webchat; wakes long-poll waiters."""
        self._pending[chat_id].append(
            WebchatPushItem(
                message_id=message_id,
                content=content,
                created_at=created_at,
                actor_type=actor_type,
            )
        )
        self._get_or_create_event(chat_id).set()
        logger.debug(
            "WebchatPushManager.notify",
            extra={"chat_id": str(chat_id), "message_id": str(message_id)},
        )

    async def wait_for_new(
        self,
        chat_id: UUID,
        timeout_seconds: float,
    ) -> list[WebchatPushItem]:
        """Wait up to timeout_seconds for new messages for chat_id; return and clear them."""
        event = self._get_or_create_event(chat_id)
        event.clear()
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            pass
        items = self._pending.pop(chat_id, [])
        return items


_webchat_push_manager: WebchatPushManager | None = None


def get_webchat_push_manager() -> WebchatPushManager:
    global _webchat_push_manager
    if _webchat_push_manager is None:
        _webchat_push_manager = WebchatPushManager()
    return _webchat_push_manager


async def _publish_webchat_redis_wake(chat_id: UUID) -> None:
    from src.infrastructure.database.redis_client import get_redis

    channel = f"{REDIS_NOTIFY_PREFIX}{chat_id}"
    try:
        r = await get_redis()
        await r.publish(channel, "1")
        webchat_redis_fanout_total.labels(op="publish", result="ok").inc()
    except Exception:
        webchat_redis_fanout_total.labels(op="publish", result="error").inc()
        logger.exception(
            "webchat_redis_publish_failed",
            extra={"chat_id": str(chat_id), "channel": channel},
        )


async def notify_webchat_outbound_wake(
    chat_id: UUID,
    message_id: UUID,
    content: str,
    created_at: datetime,
    actor_type: str,
) -> None:
    """Wake long-poll waiters: Redis fan-out when enabled, else in-process manager only."""
    if settings.webchat_redis_fanout_enabled:
        await _publish_webchat_redis_wake(chat_id)
        return
    mgr = get_webchat_push_manager()
    mgr.notify(chat_id, message_id, content, created_at, actor_type)


async def _load_webchat_items_from_db(
    session: AsyncSession,
    chat_id: UUID,
    since: datetime,
) -> list[WebchatPushItem]:
    from sqlalchemy import select

    from src.domain.entities.omnichannel_message import Message

    dc = Message.source_metadata["delivery_channel"].as_string()
    stmt = (
        select(Message)
        .where(
            Message.chat_id == chat_id,
            Message.direction == "OUTBOUND",
            Message.created_at >= since,
            dc == "WEB_WIDGET",
        )
        .order_by(Message.created_at.asc())
        .limit(80)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    out: list[WebchatPushItem] = []
    for m in rows:
        created = m.created_at if isinstance(m.created_at, datetime) else datetime.now(timezone.utc)
        out.append(
            WebchatPushItem(
                message_id=m.id,
                content=m.content or "",
                created_at=created,
                actor_type=m.actor_type or "SYSTEM",
            )
        )
    return out


async def wait_for_webchat_poll_items(
    session: AsyncSession,
    chat_id: UUID,
    timeout_seconds: float,
) -> list[WebchatPushItem]:
    """Long-poll: Redis + DB when ``webchat_redis_fanout_enabled``, else in-memory manager."""
    if not settings.webchat_redis_fanout_enabled:
        mgr = get_webchat_push_manager()
        return await mgr.wait_for_new(chat_id, timeout_seconds)

    from src.infrastructure.database.redis_client import get_redis

    wait_started = datetime.now(timezone.utc)
    since = wait_started - timedelta(seconds=15)

    r = await get_redis()
    pubsub = r.pubsub()
    channel = f"{REDIS_NOTIFY_PREFIX}{chat_id}"
    await pubsub.subscribe(channel)
    webchat_redis_fanout_total.labels(op="subscribe", result="ok").inc()
    try:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                # Do not load from DB on idle timeout: same window would re-send rows every poll (duplicates).
                return []
            timeout = min(1.0, remaining)
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if msg and msg.get("type") == "message":
                return await _load_webchat_items_from_db(session, chat_id, since)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            logger.debug("webchat pubsub cleanup", exc_info=True)

