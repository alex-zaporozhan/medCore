"""In-memory push manager for webchat long-poll: notifies waiting clients when new outbound messages arrive.

Warning: With multiple application instances, long-poll on one instance will not receive
events from the dispatcher on another instance. For horizontal scaling, replace this
in-memory store with Redis Pub/Sub (e.g. a channel per chat_id or a global channel with
payload containing chat_id).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class WebchatPushItem:
    message_id: UUID
    content: str
    created_at: datetime
    actor_type: str


class WebchatPushManager:
    """Singleton: pending messages per chat_id and asyncio.Event for long-poll wake-up.

    Limitation: in-memory only. With several app instances, long-poll on one instance
    does not receive events from the dispatcher on another. For horizontal scaling,
    use Redis Pub/Sub (channel by chat_id or global with payload chat_id).
    """

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


# Module-level singleton for use from dispatcher and webchat poll endpoint
_webchat_push_manager: WebchatPushManager | None = None


def get_webchat_push_manager() -> WebchatPushManager:
    global _webchat_push_manager
    if _webchat_push_manager is None:
        _webchat_push_manager = WebchatPushManager()
    return _webchat_push_manager
