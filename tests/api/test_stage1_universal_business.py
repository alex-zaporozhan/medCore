"""Stage 1: universal business type and specialist roles — API smoke tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.clinic import Clinic
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_u011_unauthenticated_clinic_list_scrubs_pii(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """Anonymous GET /clinics strips PII; same request with admin Bearer returns full row."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = str(seed_data["clinic_id"])
    upd = await client.put(
        f"/api/v1/clinics/{cid}",
        headers=headers,
        json={
            "phone": "+79991112233",
            "email": "secret-clinic@example.com",
            "address": "Secret address 1",
            "yookassa_shop_id": "shop-leak-test",
        },
    )
    assert upd.status_code == 200, upd.text

    anon = await client.get("/api/v1/clinics")
    assert anon.status_code == 200, anon.text
    row = next(x for x in anon.json() if x["id"] == cid)
    assert row.get("phone") is None
    assert row.get("email") is None
    assert row.get("address") is None
    assert row.get("yookassa_shop_id") is None

    authed = await client.get("/api/v1/clinics", headers=headers)
    assert authed.status_code == 200, authed.text
    row2 = next(x for x in authed.json() if x["id"] == cid)
    assert row2.get("phone") == "+79991112233"
    assert row2.get("email") == "secret-clinic@example.com"
    assert row2.get("address") == "Secret address 1"
    assert row2.get("yookassa_shop_id") == "shop-leak-test"

    assert (await client.get(f"/api/v1/clinics/{cid}")).status_code == 404
    detail = await client.get(f"/api/v1/clinics/{cid}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == cid

    await client.put(
        f"/api/v1/clinics/{cid}",
        headers=headers,
        json={
            "phone": None,
            "email": None,
            "address": None,
            "yookassa_shop_id": None,
        },
    )


@pytest.mark.asyncio
async def test_u011_anonymous_list_omits_slugless_clinic_when_multiple_exist(
    client: AsyncClient, seed_data: dict
):
    """With >1 active clinics, only rows with non-empty clinic_slug appear in anonymous GET /clinics."""
    seed_id = uuid.UUID(str(seed_data["clinic_id"]))
    hidden_id = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        res = await session.execute(select(Clinic).where(Clinic.id == seed_id))
        seed_row = res.scalar_one()
        session.add(
            Clinic(
                id=hidden_id,
                name="Slugless Internal",
                organization_id=seed_row.organization_id,
                prepayment_amount=0,
                clinic_slug=None,
            )
        )
        await session.commit()

    r = await client.get("/api/v1/clinics")
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()}
    assert str(seed_id) in ids
    assert str(hidden_id) not in ids


@pytest.mark.asyncio
async def test_clinics_response_includes_business_type_and_lexicon(client: AsyncClient, seed_data: dict):
    """GET /api/v1/clinics returns business_type, custom_name and business_lexicon."""
    r = await client.get("/api/v1/clinics")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "business_type" in item
        assert item["business_type"] in ("stomatology", "clinic", "beauty_salon", "barbershop", "nail_salon", "massage_salon", "other")
        assert "business_type_custom_name" in item
        assert "business_lexicon" in item
        lex = item["business_lexicon"]
        assert "person_label_singular" in lex
        assert "person_label_plural" in lex
        assert "staff_label_plural" in lex
        assert isinstance(lex.get("role_display"), dict)


@pytest.mark.asyncio
async def test_clinic_update_business_type(client: AsyncClient, seed_data: dict, admin_auth: dict):
    """PUT /api/v1/clinics/{id} accepts business_type and business_type_custom_name."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = str(seed_data["clinic_id"])
    r = await client.put(
        f"/api/v1/clinics/{clinic_id}",
        headers=headers,
        json={
            "business_type": "beauty_salon",
            "business_type_custom_name": None,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["business_type"] == "beauty_salon"
    # Restore for other tests
    await client.put(
        f"/api/v1/clinics/{clinic_id}",
        headers=headers,
        json={"business_type": "stomatology"},
    )


@pytest.mark.asyncio
async def test_doctor_display_role_master(client: AsyncClient, seed_data: dict):
    """PUT doctor with specialist_role=master returns display_role 'Мастер'."""
    doctor_id = str(seed_data["doctor_id"])
    r = await client.put(
        f"/api/v1/doctors/{doctor_id}",
        json={"specialist_role": "master"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["display_role"] == "Мастер"
    assert data["specialist_role"] == "master"
    # Restore
    await client.put(
        f"/api/v1/doctors/{doctor_id}",
        json={"specialist_role": "doctor"},
    )
