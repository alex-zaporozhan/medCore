"""API tests for admin forms endpoints (templates and submissions)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.patient import Patient
from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.digital_form_submission import DigitalFormSubmission


@pytest.mark.asyncio
async def test_admin_forms_templates_list_smoke(client: AsyncClient, admin_auth: dict) -> None:
  """GET /admin/forms/templates returns list (possibly empty) for clinic."""
  headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
  resp = await client.get("/api/v1/admin/forms/templates", headers=headers)
  assert resp.status_code == 200
  assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_forms_create_template_and_submission_flow(
  client: AsyncClient,
  admin_auth: dict,
  db_session: AsyncSession,
  seed_data,
) -> None:
  """Create template then submit form via admin test-submit and see it in submissions."""
  clinic_id = seed_data["clinic_id"]

  # Seed patient for submission linkage
  patient = Patient(clinic_id=clinic_id, phone="+79990002233", full_name="Forms Test", email=None)
  db_session.add(patient)
  await db_session.flush()
  await db_session.refresh(patient)

  headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

  template_body = {
    "code": "test_form",
    "name": "Test Form",
    "description": None,
    "schema": {
      "fields": [
        {
          "id": "full_name",
          "label": "ФИО",
          "type": "text",
          "required": True,
          "sensitive": True,
        },
        {
          "id": "comment",
          "label": "Комментарий",
          "type": "textarea",
          "required": False,
          "sensitive": False,
        },
      ]
    },
    "requires_signature": False,
    "active": True,
  }
  resp_create = await client.post(
    "/api/v1/admin/forms/templates",
    headers=headers,
    json=template_body,
  )
  assert resp_create.status_code == 201, resp_create.text
  tmpl = resp_create.json()
  assert tmpl["code"] == "test_form"

  # Submit form using admin test endpoint
  submit_body = {
    "template_code": "test_form",
    "patient_id": str(patient.id),
    "booking_id": None,
    "data": {
      "full_name": "Тест Тестович",
      "comment": "Все хорошо",
    },
    "signature_payload": None,
  }
  resp_submit = await client.post(
    "/api/v1/admin/forms/submissions/test-submit",
    headers=headers,
    json=submit_body,
  )
  assert resp_submit.status_code == 200, resp_submit.text
  submission = resp_submit.json()
  assert submission["patient_id"] == str(patient.id)
  assert submission.get("status") == "signed"

  # Ensure submission appears in admin list
  resp_list = await client.get(
    "/api/v1/admin/forms/submissions",
    headers=headers,
    params={"patient_id": str(patient.id)},
  )
  assert resp_list.status_code == 200, resp_list.text
  items = resp_list.json()
  assert any(it["id"] == submission["id"] for it in items)

