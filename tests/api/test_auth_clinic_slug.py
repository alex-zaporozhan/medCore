"""Patient auth: optional clinic_slug resolves tenant clinic (public slug)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agreement_unknown_clinic_slug_400(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/agreement?clinic_slug=does-not-exist-slug-xyz")
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "UNKNOWN_CLINIC_SLUG"


@pytest.mark.asyncio
async def test_send_code_with_seed_clinic_slug_204(client: AsyncClient, seed_data: dict) -> None:
    slug = seed_data["clinic_slug"]
    r = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79005550101", "clinic_slug": slug},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_send_code_unknown_slug_400(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79005550102", "clinic_slug": "missing-slug-abc"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "UNKNOWN_CLINIC_SLUG"


@pytest.mark.asyncio
async def test_send_code_clinic_slug_required_when_flag(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """PATIENT_AUTH_REQUIRE_CLINIC_SLUG: no default clinic without slug (LEAD prod policy)."""
    from src.core.config import settings

    monkeypatch.setattr(settings, "patient_auth_require_clinic_slug", True)
    r = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79005550104"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "CLINIC_SLUG_REQUIRED"
