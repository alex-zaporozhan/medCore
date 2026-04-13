"""P1-5: rate limiter fail-open increments observability counter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_fail_open_on_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core import metrics as metrics_mod

    called = {"n": 0}

    def _inc() -> None:
        called["n"] += 1

    monkeypatch.setattr(metrics_mod.rate_limiter_redis_fail_open_total, "inc", _inc)

    bad_redis = MagicMock()

    async def _pipe_raises():
        raise OSError("redis down")

    bad_redis.pipeline = MagicMock(return_value=MagicMock(execute=AsyncMock(side_effect=_pipe_raises)))

    limiter = RateLimiter(bad_redis)
    await limiter.check_or_raise("rate:test:key", limit=10, window=60)
    assert called["n"] == 1
