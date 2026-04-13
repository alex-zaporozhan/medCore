"""10-Q8 / 1b-F3: Redis-backed rate limit keys for public platform checkout/catalog (real Redis).

``pytest_runtest_setup`` in ``conftest.py`` skips these if ``RUN_REDIS_INTEGRATION_TESTS=0`` or Redis is not reachable
(``REDIS_URL``, e.g. ``docker compose up -d redis``). Otherwise RateLimiter fails open on Redis errors and assertions break.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter

pytestmark = [pytest.mark.redis_integration]


@pytest.mark.asyncio
async def test_public_platform_checkout_rate_limit_key_enforced_on_redis() -> None:
    """Same key pattern as ``public_platform_signup.checkout`` — INCR + TTL window."""
    from src.infrastructure.database.redis_client import get_redis

    redis = await get_redis()
    rl = RateLimiter(redis)
    suffix = uuid4().hex[:12]
    key = f"rate:public_platform_checkout:ip:10q8-{suffix}"
    window = 120
    try:
        await rl.check_or_raise(key, limit=1, window=window)
        with pytest.raises(RateLimitExceeded):
            await rl.check_or_raise(key, limit=1, window=window)
    finally:
        await redis.delete(key)


@pytest.mark.asyncio
async def test_public_platform_catalog_rate_limit_key_enforced_on_redis() -> None:
    """Same key pattern as ``public_platform_catalog`` list endpoints."""
    from src.infrastructure.database.redis_client import get_redis

    redis = await get_redis()
    rl = RateLimiter(redis)
    suffix = uuid4().hex[:12]
    key = f"rate:public_platform_catalog:ip:10q8-{suffix}"
    window = 120
    try:
        await rl.check_or_raise(key, limit=2, window=window)
        await rl.check_or_raise(key, limit=2, window=window)
        with pytest.raises(RateLimitExceeded):
            await rl.check_or_raise(key, limit=2, window=window)
    finally:
        await redis.delete(key)
