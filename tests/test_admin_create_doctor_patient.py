import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_doctor_uses_default_clinic(client: AsyncClient):
  """
  Creating a doctor without clinic_id should still succeed and attach default clinic.

  This confirms backend behavior for admin \"Создать врача\" кнопки.
  """
  payload = {
    "full_name": "Audit Doctor",
    "specialization": "Therapist",
    "experience_years": 5,
    "rating": "4.5",
    "is_active": True,
    "specialist_role": "doctor",
  }
  resp = await client.post("/api/v1/doctors", json=payload)
  assert resp.status_code == 201
  data = resp.json()
  assert data["clinic_id"], "clinic_id must be set by backend default clinic logic"
  assert data["full_name"] == payload["full_name"]
  assert "display_role" in data
  assert data["display_role"] == "Врач"


@pytest.mark.asyncio
async def test_create_patient_uses_default_clinic(client: AsyncClient):
  """
  Creating a patient without clinic_id should still succeed and attach default clinic.

  This confirms backend behavior for admin \"Создать пациента\" кнопки.
  """
  payload = {
    "phone": "+79991234567",
    "full_name": "Audit Patient",
  }
  resp = await client.post("/api/v1/patients", json=payload)
  assert resp.status_code == 201
  data = resp.json()
  assert data["clinic_id"], "clinic_id must be set by backend default clinic logic"
  assert data["phone"] == payload["phone"]

