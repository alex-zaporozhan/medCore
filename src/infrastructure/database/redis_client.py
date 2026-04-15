"""Redis client configuration with connection pooling."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import weakref

from redis.asyncio import Redis

from src.core.config import settings

logger = logging.getLogger(__name__)

# One pooled client per running asyncio **loop object** (not id(loop): CPython may reuse ids
# after a closed loop is GC'd, which would return a dead Redis pool — Windows pytest saw
# "Event loop is closed" on the next test).
_redis_clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Redis] = (
    weakref.WeakKeyDictionary()
)
_redis_init_lock = threading.Lock()


def _testing() -> bool:
    return os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


async def get_redis() -> Redis:
    """Return a shared Redis client for the current asyncio event loop."""
    loop = asyncio.get_running_loop()

    cached = _redis_clients.get(loop)
    if cached is not None:
        return cached

    with _redis_init_lock:
        cached = _redis_clients.get(loop)
        if cached is not None:
            return cached

        max_connections = 2 if _testing() else settings.redis_pool_size
        client = Redis.from_url(
            settings.redis_url,
            max_connections=max_connections,
            decode_responses=True,
        )
        _redis_clients[loop] = client
        logger.info(
            "[dental-booking] Redis client initialized",
            extra={
                "component": "redis",
                "pool_size": max_connections,
                "event_loop": repr(loop),
            },
        )
        return client


async def close_redis() -> None:
    """Close all pooled Redis clients (app shutdown)."""
    global _redis_clients

    for loop, client in list(_redis_clients.items()):
        try:
            aclose = getattr(client, "aclose", None)
            if aclose is not None:
                await aclose()
            else:
                await client.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[dental-booking] Redis client close error",
                extra={"component": "redis", "event_loop": repr(loop), "error": str(exc)},
            )
    _redis_clients.clear()
    logger.info("[dental-booking] Redis clients closed", extra={"component": "redis"})
