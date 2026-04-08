"""10-Q8 / 1b-F3: Redis-backed rate limit keys for public platform checkout/catalog (real Redis).

Run with ``RUN_REDIS_INTEGRATION_TESTS=1`` and reachable ``REDIS_URL`` / ``REDIS_URL_TEST``.
CI: ``build-and-test-entitlements.yml`` and ``full-backend-tests`` set the env when Redis service is up.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter

pytestmark = [
    pytest.mark.redis_integration,
    pytest.mark.skipif(
        os.environ.get("RUN_REDIS_INTEGRATION_TESTS", "").strip().lower() not in ("1", "true", "yes"),
        reason="Set RUN_REDIS_INTEGRATION_TESTS=1 to run Redis integration tests (10-Q8)",
    ),
]


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
