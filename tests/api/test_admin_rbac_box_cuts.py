import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_doctor_forbidden_waitlist_list(
  client: AsyncClient,
  seed_data,
  doctor_auth: dict,
) -> None:
  headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
  resp = await client.get(
    f"/api/v1/admin/clinics/{seed_data['clinic_id']}/waitlist",
    headers=headers,
  )
  assert resp.status_code == 403, resp.text
  body = resp.json()
  assert body.get("code") == "forbidden"


@pytest.mark.asyncio
async def test_doctor_forbidden_retention_segments(
  client: AsyncClient,
  seed_data,
  doctor_auth: dict,
) -> None:
  headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
  resp = await client.get(
    f"/api/v1/admin/clinics/{seed_data['clinic_id']}/retention/segments",
    headers=headers,
  )
  assert resp.status_code == 403, resp.text
  body = resp.json()
  assert body.get("code") == "forbidden"


@pytest.mark.asyncio
async def test_box_edition_blocks_retention_even_owner(
  client: AsyncClient,
  seed_data,
  admin_auth: dict,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv("EDITION", "box")
  headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
  resp = await client.get(
    f"/api/v1/admin/clinics/{seed_data['clinic_id']}/retention/segments",
    headers=headers,
  )
  assert resp.status_code == 403, resp.text
  body = resp.json()
  assert body.get("code") == "box_forbidden"


@pytest.mark.asyncio
async def test_box_edition_blocks_crm_pipelines_even_with_view_crm(
  client: AsyncClient,
  admin_auth: dict,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv("EDITION", "box")
  headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
  resp = await client.get("/api/v1/admin/crm/pipelines", headers=headers)
  assert resp.status_code == 403, resp.text
  body = resp.json()
  assert body.get("code") == "box_forbidden"

