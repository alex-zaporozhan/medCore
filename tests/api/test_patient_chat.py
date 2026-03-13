"""Patient chat API tests. Login with random phone (send-code -> Redis code -> verify-code), then chat."""

import pytest
from httpx import AsyncClient


def _auth_headers(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_get_or_create_conversation(client: AsyncClient, patient_auth: dict):
    patient_id = patient_auth["patient_id"]
    r = await client.get(
        f"/api/v1/patient/chat/conversation?patient_id={patient_id}",
        headers=_auth_headers(patient_auth["access_token"]),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "conversation_id" in data
    assert "unread_by_patient_count" in data
    assert "unread_by_admin_count" in data


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_get_conversation_messages(client: AsyncClient, patient_auth: dict):
    patient_id = patient_auth["patient_id"]
    r = await client.get(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        headers=_auth_headers(patient_auth["access_token"]),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "next_cursor" in data
    assert isinstance(data["items"], list)


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_send_patient_message(client: AsyncClient, patient_auth: dict):
    """POST message — key test: 201 and MessageDto; on 500 gives full traceback."""
    patient_id = patient_auth["patient_id"]
    r = await client.post(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        json={"body": "test message"},
        headers=_auth_headers(patient_auth["access_token"]),
    )
    assert r.status_code == 201, (r.status_code, r.text)
    data = r.json()
    assert "id" in data
    assert data.get("body") == "test message"
    assert "created_at" in data
    assert data.get("sender_type") == "patient"
    assert data.get("is_mine") is True
