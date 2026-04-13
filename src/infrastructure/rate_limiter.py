"""Application-level rate limiting using Redis."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from src.core.metrics import rate_limiter_redis_fail_open_total
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)


@dataclass
class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""

    key: str
    limit: int
    window: int


class RateLimiter:
    """Simple fixed-window rate limiter backed by Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check_or_raise(self, key: str, limit: int, window: int) -> None:
        """
        Increment counter for key and raise if limit exceeded.

        Uses a fixed window: INCR key and set EXPIRE window seconds when key is first created.
        """
        if limit <= 0 or window <= 0:
            return

        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = await pipe.execute()

            if ttl == -1:
                # Key exists without TTL, set window
                await self._redis.expire(key, window)
            elif ttl == -2:
                # Key was just created without TTL in this race window, set TTL
                await self._redis.expire(key, window)

            if int(count) > limit:
                raise RateLimitExceeded(key=key, limit=limit, window=window)
        except RateLimitExceeded:
            raise
        except Exception as exc:  # noqa: BLE001
            # Fail-open: don't block requests if Redis is unavailable (contract: observe, don't hide).
            logger.warning("RateLimiter error, allowing request", extra={"key": key, "error": str(exc)})
            try:
                rate_limiter_redis_fail_open_total.inc()
            except Exception:  # noqa: BLE001
                pass


async def get_rate_limiter() -> RateLimiter:
    """Dependency helper to obtain a RateLimiter instance."""
    redis = await get_redis()
    return RateLimiter(redis)

