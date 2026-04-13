"""Redis client configuration with connection pooling."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Dict

from redis.asyncio import Redis

from src.core.config import settings

logger = logging.getLogger(__name__)

# One pooled client per running asyncio loop (P1-5 / QA_ARCH: avoids attaching one global
# client to a different loop in tests and matches uvicorn's single-loop workers).
_redis_clients: Dict[int, Redis] = {}
_redis_init_lock = threading.Lock()


def _testing() -> bool:
    return os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


async def get_redis() -> Redis:
    """Return a shared Redis client for the current asyncio event loop."""
    loop = asyncio.get_running_loop()
    loop_id = id(loop)

    if loop_id in _redis_clients:
        return _redis_clients[loop_id]

    with _redis_init_lock:
        if loop_id in _redis_clients:
            return _redis_clients[loop_id]

        max_connections = 2 if _testing() else settings.redis_pool_size
        client = Redis.from_url(
            settings.redis_url,
            max_connections=max_connections,
            decode_responses=True,
        )
        _redis_clients[loop_id] = client
        logger.info(
            "[dental-booking] Redis client initialized",
            extra={
                "component": "redis",
                "pool_size": max_connections,
                "event_loop_id": loop_id,
            },
        )
        return client


async def close_redis() -> None:
    """Close all pooled Redis clients (app shutdown)."""
    global _redis_clients

    for loop_id, client in list(_redis_clients.items()):
        try:
            aclose = getattr(client, "aclose", None)
            if aclose is not None:
                await aclose()
            else:
                await client.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[dental-booking] Redis client close error",
                extra={"component": "redis", "event_loop_id": loop_id, "error": str(exc)},
            )
    _redis_clients.clear()
    logger.info("[dental-booking] Redis clients closed", extra={"component": "redis"})
