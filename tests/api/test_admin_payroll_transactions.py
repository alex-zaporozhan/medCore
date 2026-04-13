"""GET /admin/clinics/{id}/payroll/transactions — optional doctor_id (regression: empty select deadlock)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_salary_transactions_without_doctor_id_ok(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
) -> None:
    """Optional doctor_id: list all salary transactions for clinic (may be empty list)."""
    clinic_id = seed_data["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/payroll/transactions",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_salary_transactions_with_doctor_id_ok(
    init_db, seed_data, client: AsyncClient, admin_auth: dict
) -> None:
    """With doctor_id filter: still 200 and list."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/payroll/transactions",
        params={"doctor_id": str(doctor_id)},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
