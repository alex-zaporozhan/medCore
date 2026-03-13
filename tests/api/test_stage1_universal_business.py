"""Stage 1: universal business type and specialist roles — API smoke tests."""

import pytest
from httpx import AsyncClient


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
async def test_clinic_update_business_type(client: AsyncClient, seed_data: dict):
    """PUT /api/v1/clinics/{id} accepts business_type and business_type_custom_name."""
    clinic_id = str(seed_data["clinic_id"])
    r = await client.put(
        f"/api/v1/clinics/{clinic_id}",
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
