"""Integration tests for staff profile card endpoint."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_staff_profile_card_is_accessible_for_any_admin(client, admin_auth, doctor_auth):
    target_admin_id = admin_auth["admin_id"]
    headers_admin = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    r1 = await client.get(f"/api/v1/admin/staff/profiles/{target_admin_id}", headers=headers_admin)
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["id"] == target_admin_id
    assert body["clinic_id"] == admin_auth["clinic_id"]
    assert "email" in body
    assert "full_name" in body
    assert "employment_status" in body

    r2 = await client.get(f"/api/v1/admin/staff/profiles/{target_admin_id}", headers=headers_doctor)
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == target_admin_id


@pytest.mark.asyncio
async def test_staff_profile_card_hides_other_clinic(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    fake = uuid.uuid4()
    r = await client.get(f"/api/v1/admin/staff/profiles/{fake}", headers=headers)
    assert r.status_code == 404, r.text

