"""Public SaaS catalog endpoints (Phase 1b)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_public_catalog_plans_includes_starter_rf(client: AsyncClient):
    r = await client.get("/api/v1/public/platform/catalog/plans")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    slugs = {row.get("slug") for row in data}
    assert "starter_rf" in slugs
    starter = next(x for x in data if x.get("slug") == "starter_rf")
    keys = starter.get("option_keys") or []
    assert "core.base" in keys
    assert "tasks.kanban" in keys
    assert starter.get("price_monthly_rub") == "4990.00"
    assert starter.get("price_annual_rub") == "49900.00"


@pytest.mark.asyncio
async def test_public_catalog_options_includes_core_base(client: AsyncClient):
    r = await client.get("/api/v1/public/platform/catalog/options")
    assert r.status_code == 200
    data = r.json()
    keys = {row.get("entitlement_key") for row in data}
    assert "core.base" in keys
    assert "crm.pipeline" in keys
    assert "omni.embed.bundle" in keys
    assert "ai.assistant.chat" in keys
