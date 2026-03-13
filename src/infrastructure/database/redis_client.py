"""Redis client configuration with connection pooling."""

import logging
import os
from typing import Optional

from redis.asyncio import Redis

from src.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance (not used when TESTING=1 to avoid "attached to a different loop")
_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client instance with connection pooling."""
    global _redis_client

    if os.environ.get("TESTING", "").lower() in ("1", "true", "yes"):
        return Redis.from_url(
            settings.redis_url,
            max_connections=2,
            decode_responses=True,
        )

    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True,
        )

        logger.info(
            "[dental-booking] Redis client initialized",
            extra={"component": "redis", "pool_size": settings.redis_pool_size},
        )

    return _redis_client


async def close_redis() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("[dental-booking] Redis client closed", extra={"component": "redis"})
