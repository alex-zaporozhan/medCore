"""Platform founder catalog CRUD (Phase 1b subscription prices on plans)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from src.core.config import settings
from src.core.security import create_platform_founder_access_token
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan
from src.infrastructure.database import base as db_base

LIST_PATH = "/api/v1/platform/internal/catalog/plans"
_EPHEMERAL_PLAN_SLUGS = ("qa_arch_test_plan", "public_echo_plan")


@pytest.fixture(autouse=True)
async def _cleanup_ephemeral_catalog_plans():
    yield
    async with db_base.AsyncSessionLocal() as session:
        await session.execute(
            delete(PlatformCatalogPlan).where(PlatformCatalogPlan.slug.in_(_EPHEMERAL_PLAN_SLUGS))
        )
        await session.commit()


@pytest.mark.asyncio
async def test_platform_founder_lists_catalog_plans(client: AsyncClient, seed_data: dict, monkeypatch):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(LIST_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    slugs = {row["slug"] for row in data}
    assert "starter_rf" in slugs
    starter = next(x for x in data if x["slug"] == "starter_rf")
    assert starter.get("price_monthly_rub") == "4990.00"
    assert starter.get("price_annual_rub") == "49900.00"
    assert "core.base" in (starter.get("option_keys") or [])


@pytest.mark.asyncio
async def test_platform_founder_upsert_plan_subscription_prices(client: AsyncClient, seed_data: dict, monkeypatch):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    slug = "qa_arch_test_plan"
    body = {
        "display_name": "QA test plan",
        "description": "ephemeral",
        "option_keys": ["core.base"],
        "is_active": True,
        "sort_order": 99,
        "price_monthly_rub": "1234.50",
        "price_annual_rub": "12000.00",
    }
    r = await client.put(
        f"/api/v1/platform/internal/catalog/plans/{slug}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["slug"] == slug
    assert row["price_monthly_rub"] == "1234.50"
    assert row["price_annual_rub"] == "12000.00"
    assert row["option_keys"] == ["core.base"]

    r2 = await client.put(
        f"/api/v1/platform/internal/catalog/plans/{slug}",
        json={
            **body,
            "price_monthly_rub": "2000.00",
            "display_name": "QA test plan v2",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["price_monthly_rub"] == "2000.00"
    assert r2.json()["display_name"] == "QA test plan v2"


@pytest.mark.asyncio
async def test_platform_founder_upsert_rejects_bad_slug(client: AsyncClient, seed_data: dict, monkeypatch):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.put(
        "/api/v1/platform/internal/catalog/plans/-bad-slug",
        json={
            "display_name": "x",
            "option_keys": [],
            "is_active": True,
            "sort_order": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_platform_founder_upsert_rejects_unknown_option_key(client: AsyncClient, seed_data: dict, monkeypatch):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.put(
        "/api/v1/platform/internal/catalog/plans/bad_keys_plan",
        json={
            "display_name": "Bad keys",
            "option_keys": ["definitely.not.in.catalog.zzz"],
            "is_active": True,
            "sort_order": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "unknown_option_keys"
    assert "definitely.not.in.catalog" in (body.get("detail") or "")


@pytest.mark.asyncio
async def test_public_catalog_shows_upserted_plan_prices(client: AsyncClient, seed_data: dict, monkeypatch):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    slug = "public_echo_plan"
    await client.put(
        f"/api/v1/platform/internal/catalog/plans/{slug}",
        json={
            "display_name": "Echo",
            "option_keys": ["core.base"],
            "is_active": True,
            "sort_order": 50,
            "price_monthly_rub": "100.00",
            "price_annual_rub": "1000.00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get("/api/v1/public/platform/catalog/plans")
    assert r.status_code == 200
    echo = next((x for x in r.json() if x.get("slug") == slug), None)
    assert echo is not None
    assert echo["price_monthly_rub"] == "100.00"
    assert echo["price_annual_rub"] == "1000.00"
