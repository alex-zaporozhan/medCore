"""Public SaaS catalog endpoints (Phase 1b)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_public_catalog_plans_includes_start_growth_business_os(client: AsyncClient):
    r = await client.get("/api/v1/public/platform/catalog/plans")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    slugs = {row.get("slug") for row in data}
    assert "start" in slugs
    assert "growth" in slugs
    assert "business_os" in slugs
    start = next(x for x in data if x.get("slug") == "start")
    keys = start.get("option_keys") or []
    assert "core.base" in keys
    assert "crm.pipeline" in keys
    assert "tasks.kanban" in keys
    assert start.get("price_monthly_rub") == "2900.00"
    assert start.get("price_annual_rub") == "29000.00"


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
