"""Rate limits on public SaaS catalog (landing §5 / PRC-C1)."""

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.main import app


@pytest.mark.asyncio
async def test_public_catalog_plans_rate_limited_by_ip(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "rate_public_platform_catalog_ip_limit", 2)
    monkeypatch.setattr(settings, "rate_public_platform_catalog_ip_window_seconds", 600)

    class _CountingRl:
        def __init__(self) -> None:
            self.n = 0

        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            self.n += 1
            if self.n > 2:
                raise RateLimitExceeded(key=key, limit=limit, window=window)

    rl = _CountingRl()

    async def _fake_dep():
        return rl

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        path = "/api/v1/public/platform/catalog/plans"
        assert (await client.get(path)).status_code == 200
        assert (await client.get(path)).status_code == 200
        r3 = await client.get(path)
        assert r3.status_code == 429
        assert r3.json().get("code") == "rate_limited"
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)
