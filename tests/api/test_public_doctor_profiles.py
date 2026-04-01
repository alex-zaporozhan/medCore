"""Integration tests for public doctor profiles (admin CRUD + public read)."""

from __future__ import annotations

import uuid

import pytest

from src.domain.entities.doctor import Doctor
from src.domain.entities.public_doctor_profile import PublicDoctorProfile
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_admin_can_create_and_public_can_read_profile_by_slugs(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    doctor_id = str(seed_data["doctor_id"])

    # Ensure clinic has slug for URL lookup
    upd = await client.put(
        f"/api/v1/clinics/{clinic_id}",
        headers=headers,
        json={"clinic_slug": "test-clinic"},
    )
    assert upd.status_code == 200, upd.text

    create = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/public-doctor-profiles",
        headers=headers,
        json={
            "doctor_id": doctor_id,
            "doctor_slug": "doctor-ivanov",
            "is_published": True,
            "short_bio": "Bio",
            "about_md": "About",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["clinic_id"] == clinic_id
    assert body["doctor_id"] == doctor_id
    assert body["doctor_slug"] == "doctor-ivanov"
    assert body["is_published"] is True

    # Public read by slugs
    public = await client.get(
        "/api/v1/public/clinics/by-slug/test-clinic/doctors/doctor-ivanov"
    )
    assert public.status_code == 200, public.text
    p = public.json()
    assert p["clinic_slug"] == "test-clinic"
    assert p["doctor_slug"] == "doctor-ivanov"
    assert p["doctor_id"] == doctor_id
    assert p["short_bio"] == "Bio"
    assert p["about_md"] == "About"


@pytest.mark.asyncio
async def test_public_profile_hidden_when_unpublished(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    # Create a separate doctor so this test is isolated from other tests using seed doctor_id.
    async with db_base.AsyncSessionLocal() as session:
        new_doctor_id = uuid.uuid4()
        session.add(
            Doctor(
                id=new_doctor_id,
                clinic_id=uuid.UUID(clinic_id),
                full_name="Hidden Doctor",
                specialization="Therapy",
                is_active=True,
            )
        )
        await session.commit()
    doctor_id = str(new_doctor_id)

    upd = await client.put(
        f"/api/v1/clinics/{clinic_id}",
        headers=headers,
        json={"clinic_slug": "hidden-clinic"},
    )
    assert upd.status_code == 200, upd.text

    create = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/public-doctor-profiles",
        headers=headers,
        json={"doctor_id": doctor_id, "doctor_slug": "hidden-doc", "is_published": False},
    )
    assert create.status_code == 201, create.text

    r = await client.get("/api/v1/public/clinics/by-slug/hidden-clinic/doctors/hidden-doc")
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_public_profile_is_clinic_isolated(client, admin_auth):
    """If clinic slug does not exist, public endpoint returns 404 (no leakage)."""
    r = await client.get("/api/v1/public/clinics/by-slug/nope/doctors/any")
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_admin_list_filter_by_doctor_id(client, admin_auth, seed_data):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        new_doctor_id = uuid.uuid4()
        session.add(
            Doctor(
                id=new_doctor_id,
                clinic_id=uuid.UUID(clinic_id),
                full_name="List Doctor",
                specialization="Therapy",
                is_active=True,
            )
        )
        await session.commit()
    doctor_id = str(new_doctor_id)

    # Create row directly in DB to keep test small
    async with db_base.AsyncSessionLocal() as session:
        row = PublicDoctorProfile(
            id=uuid.uuid4(),
            clinic_id=uuid.UUID(clinic_id),
            doctor_id=uuid.UUID(doctor_id),
            doctor_slug="list-doc",
            is_published=False,
        )
        session.add(row)
        await session.commit()

    listed = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/public-doctor-profiles",
        params={"doctor_id": doctor_id},
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert any(x["doctor_slug"] == "list-doc" for x in items)

