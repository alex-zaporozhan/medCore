"""Patient chat API tests. Login with random phone (send-code -> Redis code -> verify-code), then chat."""

import pytest
from httpx import AsyncClient

from src.core.config import settings


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


@pytest.mark.asyncio
async def test_patient_chat_dedup_returns_same_message_id(client: AsyncClient, patient_auth: dict):
    patient_id = patient_auth["patient_id"]
    payload = {"body": "dedup test message"}
    r1 = await client.post(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        json=payload,
        headers=_auth_headers(patient_auth["access_token"]),
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        json=payload,
        headers=_auth_headers(patient_auth["access_token"]),
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["id"] == r1.json()["id"]


@pytest.mark.asyncio
async def test_patient_chat_rate_limit_429(client: AsyncClient, patient_auth: dict, monkeypatch):
    monkeypatch.setattr(settings, "rate_patient_chat_send_per_patient_limit", 1, raising=False)
    monkeypatch.setattr(settings, "rate_patient_chat_send_window_seconds", 60, raising=False)
    monkeypatch.setattr(settings, "rate_patient_chat_send_per_conversation_limit", 999, raising=False)
    patient_id = patient_auth["patient_id"]
    h = _auth_headers(patient_auth["access_token"])
    r1 = await client.post(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        json={"body": "rl test 1"},
        headers=h,
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        f"/api/v1/patient/chat/conversation/messages?patient_id={patient_id}",
        json={"body": "rl test 2"},
        headers=h,
    )
    assert r2.status_code == 429, r2.text
    assert r2.json().get("code") == "chat_rate_limited"


@pytest.mark.asyncio
async def test_patient_chat_upload_magic_mismatch_rejected(client: AsyncClient, patient_auth: dict):
    h = _auth_headers(patient_auth["access_token"])
    files = {
        "file": ("x.png", b"%PDF-1.7 test", "image/png"),
    }
    r = await client.post("/api/v1/patient/chat/conversation/messages/upload", files=files, headers=h)
    assert r.status_code == 400, r.text
