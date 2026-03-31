"""Integration tests for staff directory (profession categories, clinic scope)."""

from __future__ import annotations

import uuid

import pytest


async def _role_codes_from_rbac_users(client, headers: dict[str, str], admin_id: str) -> list[str]:
    r = await client.get("/api/v1/admin/rbac/users", headers=headers)
    assert r.status_code == 200, r.text
    for item in r.json()["items"]:
        if item["admin_id"] == admin_id:
            return sorted(item["role_codes"])
    raise AssertionError(f"admin {admin_id} not in rbac users")


@pytest.mark.asyncio
async def test_staff_directory_categories_and_cache(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = admin_auth["clinic_id"]

    empty = await client.get(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

    create = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Маркетологи", "sort_order": 1, "default_role_codes": ["doctor"]},
    )
    assert create.status_code == 201, create.text
    row = create.json()
    assert row["name"] == "Маркетологи"
    assert row["clinic_id"] == cid

    listed = await client.get(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_staff_directory_forbidden_for_doctor(client, doctor_auth):
    headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    cid = doctor_auth["clinic_id"]
    r = await client.get(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_staff_directory_wrong_clinic_is_hidden(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    fake = uuid.uuid4()
    r = await client.get(
        f"/api/v1/admin/clinics/{fake}/staff-directory/profession-categories",
        headers=headers,
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_patch_profession_category_for_existing_staff(client, admin_auth):
    """PATCH must apply profession_category_id when sent alone (Pydantic model_fields_set)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    cat = await client.post(
        f"/api/v1/admin/clinics/{admin_auth['clinic_id']}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Врачи", "sort_order": 0, "default_role_codes": ["doctor"]},
    )
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    staff = await client.get(
        f"/api/v1/admin/clinics/{admin_auth['clinic_id']}/staff-directory/admins",
        headers=headers,
    )
    assert staff.status_code == 200, staff.text
    other = next(
        (x for x in staff.json() if x["email"] != "admin@test-clinic.local"),
        None,
    )
    assert other is not None
    sid = other["id"]

    patch = await client.patch(
        f"/api/v1/admin/clinics/{admin_auth['clinic_id']}/staff-directory/admins/{sid}",
        headers=headers,
        json={"profession_category_id": cat_id},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["profession_category_id"] == cat_id

    clear = await client.patch(
        f"/api/v1/admin/clinics/{admin_auth['clinic_id']}/staff-directory/admins/{sid}",
        headers=headers,
        json={"profession_category_id": None},
    )
    assert clear.status_code == 200, clear.text
    assert clear.json()["profession_category_id"] is None


@pytest.mark.asyncio
async def test_admin_session_includes_accessible_clinics(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    s = await client.get("/api/v1/admin/auth/session", headers=headers)
    assert s.status_code == 200, s.text
    body = s.json()
    assert "accessible_clinic_ids" in body
    assert isinstance(body["accessible_clinic_ids"], list)
    assert admin_auth["clinic_id"] in body["accessible_clinic_ids"]


@pytest.mark.asyncio
async def test_create_staff_admin_assigns_user_roles(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = admin_auth["clinic_id"]

    cat = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Синк-тест", "sort_order": 0, "default_role_codes": ["doctor"]},
    )
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    email = f"staff_{uuid.uuid4().hex[:8]}@test.local"
    create = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/admins",
        headers=headers,
        json={
            "email": email,
            "password": "password123",
            "full_name": "Role Test",
            "profession_category_id": cat_id,
            "role_codes": ["doctor"],
        },
    )
    assert create.status_code == 201, create.text
    new_id = create.json()["id"]

    roles = await _role_codes_from_rbac_users(client, headers, new_id)
    assert roles == ["doctor"]


@pytest.mark.asyncio
async def test_patch_category_syncs_roles_for_staff_in_category(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = admin_auth["clinic_id"]

    cat = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Шаблон A", "sort_order": 0, "default_role_codes": ["doctor"]},
    )
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    email = f"sync_{uuid.uuid4().hex[:8]}@test.local"
    cr = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/admins",
        headers=headers,
        json={
            "email": email,
            "password": "password123",
            "role_codes": ["doctor"],
            "profession_category_id": cat_id,
        },
    )
    assert cr.status_code == 201, cr.text
    new_id = cr.json()["id"]
    assert await _role_codes_from_rbac_users(client, headers, new_id) == ["doctor"]

    patch = await client.patch(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories/{cat_id}",
        headers=headers,
        json={"default_role_codes": ["owner"]},
    )
    assert patch.status_code == 200, patch.text

    roles_after = await _role_codes_from_rbac_users(client, headers, new_id)
    assert roles_after == ["owner"]


@pytest.mark.asyncio
async def test_category_sync_preserves_owner_role(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = admin_auth["clinic_id"]
    owner_id = admin_auth["admin_id"]

    cat = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Владельцы", "sort_order": 0, "default_role_codes": ["owner"]},
    )
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    assign = await client.patch(
        f"/api/v1/admin/clinics/{cid}/staff-directory/admins/{owner_id}",
        headers=headers,
        json={"profession_category_id": cat_id},
    )
    assert assign.status_code == 200, assign.text

    patch = await client.patch(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories/{cat_id}",
        headers=headers,
        json={"default_role_codes": ["doctor"]},
    )
    assert patch.status_code == 200, patch.text

    roles = await _role_codes_from_rbac_users(client, headers, owner_id)
    assert "owner" in roles
    assert "doctor" in roles


@pytest.mark.asyncio
async def test_soft_delete_category_clears_profession_fk(client, admin_auth):
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = admin_auth["clinic_id"]

    cat = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories",
        headers=headers,
        json={"name": "Скоро удалим", "sort_order": 0, "default_role_codes": ["doctor"]},
    )
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    email = f"fk_{uuid.uuid4().hex[:8]}@test.local"
    cr = await client.post(
        f"/api/v1/admin/clinics/{cid}/staff-directory/admins",
        headers=headers,
        json={
            "email": email,
            "password": "password123",
            "role_codes": ["doctor"],
            "profession_category_id": cat_id,
        },
    )
    assert cr.status_code == 201, cr.text
    new_id = cr.json()["id"]
    assert cr.json()["profession_category_id"] == cat_id

    dele = await client.delete(
        f"/api/v1/admin/clinics/{cid}/staff-directory/profession-categories/{cat_id}",
        headers=headers,
    )
    assert dele.status_code == 204, dele.text

    staff = await client.get(
        f"/api/v1/admin/clinics/{cid}/staff-directory/admins",
        headers=headers,
    )
    assert staff.status_code == 200, staff.text
    row = next(x for x in staff.json() if x["id"] == new_id)
    assert row["profession_category_id"] is None
    assert row["profession_category_name"] is None
