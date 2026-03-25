"""Коробка: employment_status (уволен), блокировка входа и PATCH."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_cannot_self_terminate(
    client: AsyncClient, admin_auth: dict
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    admin_id = admin_auth["admin_id"]
    r = await client.patch(
        f"/api/v1/admin/admins/{admin_id}",
        headers=headers,
        json={"employment_status": "terminated"},
    )
    assert r.status_code == 400, r.text
    assert "самого себя" in r.json().get("detail", "").lower() or "себя" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_terminated_admin_cannot_login(
    client: AsyncClient, admin_auth: dict
) -> None:
    """Сценарий: один доп. админ (не «второй из десяти» в списке сидов).

    Создаём ровно одного нового пользователя через POST, увольняем, проверяем 401 на login.
    Email уникален (uuid), чтобы при повторном прогоне pytest на той же БД не ловить
    unique violation на admins.email. Если бы в одном тесте создавали 10 админов — у каждого
    был бы свой уникальный local-part (цикл с uuid или счётчик).
    """
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    helper_email = f"helper-{uuid.uuid4().hex[:10]}@test-clinic.local"
    r = await client.post(
        "/api/v1/admin/admins",
        headers=headers,
        json={
            "email": helper_email,
            "password": "password123",
            "full_name": "Helper",
        },
    )
    assert r.status_code == 201, r.text
    helper_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/admin/admins/{helper_id}",
        headers=headers,
        json={"employment_status": "terminated"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["employment_status"] == "terminated"

    r3 = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": helper_email, "password": "password123"},
    )
    assert r3.status_code == 401, r3.text


@pytest.mark.asyncio
async def test_list_admins_includes_employment_status(
    client: AsyncClient, admin_auth: dict
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/admins", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) >= 1
    assert all("employment_status" in row for row in data)
    assert data[0]["employment_status"] == "active"
