"""Негативные сценарии: админ с JWT одной клиники не получает данные чужого tenant по path clinic_id."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.security
async def test_admin_finance_foreign_clinic_returns_not_found(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """GET .../finance/cashboxes с чужим clinic_id — не 200 (маскировка как 404)."""
    foreign = uuid.uuid4()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{foreign}/finance/cashboxes",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
@pytest.mark.security
async def test_admin_finance_liability_foreign_clinic_returns_not_found(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    foreign = uuid.uuid4()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{foreign}/finance/liability",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
@pytest.mark.security
async def test_admin_services_foreign_clinic_returns_not_found(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """Список услуг админки при несовпадении clinic в path — не 200 (здесь 404)."""
    foreign = uuid.uuid4()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{foreign}/services",
        headers=headers,
    )
    assert r.status_code == 404
