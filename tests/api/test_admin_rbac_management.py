"""Integration tests for admin RBAC management endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_rbac_catalog_requires_rbac_manage(client, admin_auth, doctor_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    ok = await client.get("/api/v1/admin/rbac/catalog", headers=owner_headers)
    assert ok.status_code == 200, ok.text
    payload = ok.json()
    assert isinstance(payload.get("roles"), list)
    assert isinstance(payload.get("permissions"), list)
    presets = payload.get("role_presets")
    assert isinstance(presets, list)
    preset_codes = {p["code"] for p in presets}
    assert preset_codes == {"manager", "admin", "doctor"}

    forbidden = await client.get("/api/v1/admin/rbac/catalog", headers=doctor_headers)
    assert forbidden.status_code == 403, forbidden.text


@pytest.mark.asyncio
async def test_owner_can_grant_personal_permission_and_doctor_session_reflects_it(
    client,
    admin_auth,
    doctor_auth,
):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    doctor_id = doctor_auth["admin_id"]

    before_session = await client.get("/api/v1/admin/auth/session", headers=doctor_headers)
    assert before_session.status_code == 200, before_session.text
    assert "view_reports" not in set(before_session.json()["permissions"])

    patch_resp = await client.patch(
        f"/api/v1/admin/rbac/users/{doctor_id}/permissions",
        json={
            "overrides": [
                {"permission_code": "view_reports", "effect": "grant"},
            ]
        },
        headers=owner_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text

    after_session = await client.get("/api/v1/admin/auth/session", headers=doctor_headers)
    assert after_session.status_code == 200, after_session.text
    assert "view_reports" in set(after_session.json()["permissions"])


@pytest.mark.asyncio
async def test_owner_invariants_are_protected(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    owner_id = admin_auth["admin_id"]

    catalog = await client.get("/api/v1/admin/rbac/catalog", headers=owner_headers)
    assert catalog.status_code == 200, catalog.text
    owner_role = next((r for r in catalog.json()["roles"] if r["code"] == "owner"), None)
    assert owner_role is not None

    # owner role permissions are immutable
    role_patch = await client.patch(
        f"/api/v1/admin/rbac/roles/{owner_role['id']}/permissions",
        json={"permission_codes": owner_role["permission_codes"]},
        headers=owner_headers,
    )
    assert role_patch.status_code == 403, role_patch.text

    # cannot remove owner role from owner user
    remove_owner_role = await client.patch(
        f"/api/v1/admin/rbac/users/{owner_id}/roles",
        json={"role_codes": ["admin"]},
        headers=owner_headers,
    )
    assert remove_owner_role.status_code == 403, remove_owner_role.text

    # cannot apply personal overrides to owner user
    owner_override = await client.patch(
        f"/api/v1/admin/rbac/users/{owner_id}/permissions",
        json={"overrides": [{"permission_code": "rbac.manage", "effect": "deny"}]},
        headers=owner_headers,
    )
    assert owner_override.status_code == 403, owner_override.text


@pytest.mark.asyncio
async def test_owner_can_create_clinic_role_with_permissions(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    create = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "reception_lead",
            "name": "Ресепшен (лид)",
            "permission_codes": ["view_dashboard", "view_tasks"],
        },
        headers=owner_headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["code"] == "reception_lead"
    assert body["clinic_id"] is not None
    assert set(body["permission_codes"]) == {"view_dashboard", "view_tasks"}

    catalog = await client.get("/api/v1/admin/rbac/catalog", headers=owner_headers)
    assert catalog.status_code == 200, catalog.text
    codes = {r["code"] for r in catalog.json()["roles"]}
    assert "reception_lead" in codes


@pytest.mark.asyncio
async def test_create_clinic_role_rejects_system_code(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    bad = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "admin",
            "name": "Fake admin",
            "permission_codes": ["view_dashboard"],
        },
        headers=owner_headers,
    )
    assert bad.status_code == 422, bad.text
    assert "Reserved for system roles" in bad.json()["detail"]


@pytest.mark.asyncio
async def test_create_clinic_role_reserved_code_localized_ru(client, admin_auth):
    owner_headers = {
        "Authorization": f"Bearer {admin_auth['access_token']}",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    bad = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "manager",
            "name": "X",
            "permission_codes": ["view_dashboard"],
        },
        headers=owner_headers,
    )
    assert bad.status_code == 422, bad.text
    assert "Зарезервировано" in bad.json()["detail"]


@pytest.mark.asyncio
async def test_create_clinic_role_requires_nonempty_permissions(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    bad = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "empty_perms",
            "name": "Empty",
            "permission_codes": [],
        },
        headers=owner_headers,
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_create_clinic_role_forbidden_for_doctor(client, doctor_auth):
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    resp = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "x_role",
            "name": "X",
            "permission_codes": ["view_tasks"],
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_owner_can_delete_clinic_role_without_users(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    create = await client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "temp_role_del",
            "name": "Temp",
            "permission_codes": ["view_dashboard"],
        },
        headers=owner_headers,
    )
    assert create.status_code == 201, create.text
    role_id = create.json()["id"]

    deleted = await client.delete(f"/api/v1/admin/rbac/roles/{role_id}", headers=owner_headers)
    assert deleted.status_code == 204, deleted.text

    catalog = await client.get("/api/v1/admin/rbac/catalog", headers=owner_headers)
    assert catalog.status_code == 200, catalog.text
    codes = {r["code"] for r in catalog.json()["roles"]}
    assert "temp_role_del" not in codes


@pytest.mark.asyncio
async def test_cannot_delete_global_role(client, admin_auth):
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    catalog = await client.get("/api/v1/admin/rbac/catalog", headers=owner_headers)
    assert catalog.status_code == 200, catalog.text
    global_role = next((r for r in catalog.json()["roles"] if r.get("clinic_id") is None), None)
    if global_role is None:
        pytest.skip("No global roles in catalog for this DB (all roles may be clinic-scoped)")
    resp = await client.delete(f"/api/v1/admin/rbac/roles/{global_role['id']}", headers=owner_headers)
    assert resp.status_code == 403, resp.text
    assert "Global" in resp.json()["detail"] or "глобальн" in resp.json()["detail"].lower() or "system" in resp.json()["detail"].lower()

