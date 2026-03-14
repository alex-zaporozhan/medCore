"""API tests for patient forms endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.digital_form_template import DigitalFormTemplate


@pytest.mark.asyncio
async def test_patient_forms_pending_and_submit(
  client: AsyncClient,
  patient_auth: dict,
  db_session: AsyncSession,
  seed_data,
) -> None:
  """Smoke test: pending returns templates and submit creates submission."""
  clinic_id = seed_data["clinic_id"]

  template = DigitalFormTemplate(
    clinic_id=clinic_id,
    code="patient_form",
    name="Patient Test Form",
    description=None,
    version=1,
    schema={
      "fields": [
        {
          "id": "agreement",
          "label": "Соглашаюсь",
          "type": "checkbox",
          "required": True,
          "sensitive": False,
        }
      ]
    },
    requires_signature=False,
    active=True,
  )
  db_session.add(template)
  await db_session.commit()

  headers = {"Authorization": f"Bearer {patient_auth['access_token']}"}

  resp_pending = await client.get("/api/v1/patient/forms/pending", headers=headers)
  assert resp_pending.status_code == 200, resp_pending.text
  templates = resp_pending.json()
  assert any(t["code"] == "patient_form" for t in templates)

  resp_submit = await client.post(
    "/api/v1/patient/forms/patient_form/submit",
    headers=headers,
    json={"data": {"agreement": True}},
  )
  assert resp_submit.status_code == 200, resp_submit.text
  data = resp_submit.json()
  assert data["template_id"]

