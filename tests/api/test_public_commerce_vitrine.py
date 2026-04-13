"""Public commerce vitrine (PWA storefront read model)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, update

from src.domain.entities.clinic import Clinic
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.core.config import settings
from src.domain.entities.organization import Organization
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.main import app


@pytest.mark.asyncio
async def test_public_vitrine_off_when_clinic_flag_false(
    client: AsyncClient,
    seed_data: dict,
) -> None:
    cid = seed_data["clinic_id"]
    r = await client.get(f"/api/v1/public/clinics/{cid}/commerce/vitrine")
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is False
    assert j["items"] == []


@pytest.mark.asyncio
async def test_public_vitrine_lists_active_nomenclature_when_enabled(
    client: AsyncClient,
    seed_data: dict,
    db_session,
) -> None:
    cid = uuid.UUID(str(seed_data["clinic_id"]))
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Vitrine test org"))
    await db_session.flush()
    await db_session.execute(update(Clinic).where(Clinic.id == cid).values(organization_id=org_id))
    await db_session.execute(
        update(Clinic)
        .where(Clinic.id == cid)
        .values(patient_store_visible=True, patient_store_title="Витрина тест")
    )
    db_session.add(
        CommerceNomenclatureItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            clinic_id=cid,
            sku="T-SKU-1",
            name="Тестовая зубная щётка",
            unit="pcs",
            is_active=True,
        )
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/public/clinics/{cid}/commerce/vitrine")
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is True
    assert j["section_title"] == "Витрина тест"
    assert len(j["items"]) >= 1
    names = {x["name"] for x in j["items"]}
    assert "Тестовая зубная щётка" in names

    await db_session.execute(delete(CommerceNomenclatureItem).where(CommerceNomenclatureItem.clinic_id == cid))
    await db_session.execute(
        update(Clinic)
        .where(Clinic.id == cid)
        .values(
            patient_store_visible=False,
            patient_store_title=None,
            organization_id=None,
        )
    )
    await db_session.execute(delete(Organization).where(Organization.id == org_id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_public_vitrine_rate_limited_by_ip(client: AsyncClient, seed_data: dict, monkeypatch: pytest.MonkeyPatch):
    cid = seed_data["clinic_id"]

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

    monkeypatch.setattr(settings, "rate_public_commerce_vitrine_ip_limit", 2)
    app.dependency_overrides[get_rate_limiter] = _fake_dep
    path = f"/api/v1/public/clinics/{cid}/commerce/vitrine"
    try:
        assert (await client.get(path)).status_code == 200
        assert (await client.get(path)).status_code == 200
        r3 = await client.get(path)
        assert r3.status_code == 429
        assert r3.json().get("code") == "rate_limited"
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)
