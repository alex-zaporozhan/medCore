"""Публичные заявки на корпоративный тариф и кабинет Основателя."""

import csv
import io

import pytest
from httpx import AsyncClient

from src.api.v1.routers import platform_enterprise_leads as platform_enterprise_leads_router
from src.core.config import settings
from src.core.security import create_platform_founder_access_token
from src.infrastructure.database.redis_client import get_redis

CREATE_PATH = "/api/v1/platform-leads/"


async def _clear_enterprise_lead_rate_limit_keys() -> None:
    rconn = await get_redis()
    async for key in rconn.scan_iter(match="rate:public_enterprise_lead:*"):
        await rconn.delete(key)
LIST_PATH = "/api/v1/platform/internal/enterprise-leads"
EXPORT_PATH = "/api/v1/platform/internal/enterprise-leads/export"


@pytest.mark.asyncio
async def test_create_enterprise_lead_public(client: AsyncClient):
    r = await client.post(
        CREATE_PATH,
        json={
            "name": "Иван",
            "company_name": "ООО Тест",
            "phone_or_email": "+79990001122",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body.get("status") == "NEW"
    assert body.get("lead_source") == "corporate"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_enterprise_lead_sandbox_source(client: AsyncClient):
    r = await client.post(
        CREATE_PATH,
        json={
            "name": "Ранний доступ к демо",
            "company_name": "Публичная страница",
            "phone_or_email": "demo_waitlist_1@example.com",
            "lead_source": "sandbox_demo",
        },
    )
    assert r.status_code == 201
    assert r.json().get("lead_source") == "sandbox_demo"


@pytest.mark.asyncio
async def test_enterprise_lead_rate_limited_by_ip(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await _clear_enterprise_lead_rate_limit_keys()
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_ip_limit", 2)
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_ip_window_seconds", 600)
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_contact_limit", 0)
    base = {"name": "T", "company_name": "C", "phone_or_email": "x1@y.z"}
    assert (await client.post(CREATE_PATH, json={**base, "phone_or_email": "a1@ip.z"})).status_code == 201
    assert (await client.post(CREATE_PATH, json={**base, "phone_or_email": "a2@ip.z"})).status_code == 201
    r3 = await client.post(CREATE_PATH, json={**base, "phone_or_email": "a3@ip.z"})
    assert r3.status_code == 429
    j3 = r3.json()
    assert j3.get("code") == "rate_limited"
    assert isinstance(j3.get("detail"), str)


@pytest.mark.asyncio
async def test_enterprise_lead_rate_limited_by_contact(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await _clear_enterprise_lead_rate_limit_keys()
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_ip_limit", 0)
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_contact_limit", 2)
    monkeypatch.setattr(settings, "rate_public_enterprise_lead_contact_window_seconds", 3600)
    body = {"name": "T", "company_name": "C", "phone_or_email": "same@contact.limit"}
    assert (await client.post(CREATE_PATH, json=body)).status_code == 201
    assert (await client.post(CREATE_PATH, json=body)).status_code == 201
    r3 = await client.post(CREATE_PATH, json=body)
    assert r3.status_code == 429


@pytest.mark.asyncio
async def test_list_enterprise_leads_requires_founder(client: AsyncClient):
    r = await client.get(LIST_PATH)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_export_enterprise_leads_requires_founder(client: AsyncClient):
    r = await client.get(EXPORT_PATH)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_export_enterprise_leads_csv_founder(client: AsyncClient, seed_data: dict):
    cr = await client.post(
        CREATE_PATH,
        json={
            "name": "Экспорт",
            "company_name": "ООО CSV",
            "phone_or_email": "csv_export@example.com",
        },
    )
    assert cr.status_code == 201
    lead_id = cr.json()["id"]
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(EXPORT_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "text/csv" in (r.headers.get("content-type") or "")
    text = r.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][0] == "id"
    assert "lead_source" in rows[0]
    data_rows = [x for x in rows[1:] if x and x[0] == lead_id]
    assert len(data_rows) == 1


@pytest.mark.asyncio
async def test_create_enterprise_lead_requires_turnstile_when_enabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "turnstile_enabled", True)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key-enterprise-lead")
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret-test")

    async def _verify_turnstile(token, *, remote_ip):
        from src.application.services.turnstile_service import TurnstileVerifyResult

        if token and str(token).strip():
            return TurnstileVerifyResult(ok=True, error_codes=[])
        return TurnstileVerifyResult(ok=False, error_codes=["missing-input-response"])

    monkeypatch.setattr(platform_enterprise_leads_router, "verify_turnstile", _verify_turnstile)

    body = {"name": "T", "company_name": "C", "phone_or_email": "turnstile@enterprise.test"}
    r1 = await client.post(CREATE_PATH, json=body)
    assert r1.status_code == 403
    j1 = r1.json()
    assert j1.get("code") == "captcha_required"
    assert (j1.get("details") or {}).get("site_key") == "site-key-enterprise-lead"

    r2 = await client.post(CREATE_PATH, json={**body, "phone_or_email": "turnstile2@enterprise.test", "turnstile_token": "ok"})
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_enterprise_lead_notify_webhook_scheduled_when_url_set(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    captured: list[dict] = []

    async def fake_notify(*, payload: dict):
        captured.append(payload)

    monkeypatch.setattr(platform_enterprise_leads_router, "send_enterprise_lead_created_webhook", fake_notify)
    monkeypatch.setattr(settings, "enterprise_lead_notify_webhook_url", "https://hooks.example/leads")

    r = await client.post(
        CREATE_PATH,
        json={
            "name": "Webhook",
            "company_name": "ООО Hook",
            "phone_or_email": "webhook_lead@example.com",
        },
    )
    assert r.status_code == 201
    assert len(captured) == 1
    assert captured[0].get("event") == "enterprise_lead.created"
    assert captured[0].get("phone_or_email") == "webhook_lead@example.com"


@pytest.mark.asyncio
async def test_list_and_patch_enterprise_leads_founder(client: AsyncClient, seed_data: dict):
    cr = await client.post(
        CREATE_PATH,
        json={
            "name": "Пётр",
            "company_name": "ИП Петров",
            "phone_or_email": "petr@example.com",
        },
    )
    assert cr.status_code == 201
    lead_id = cr.json()["id"]
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(LIST_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    match = next((x for x in rows if x["id"] == lead_id), None)
    assert match is not None
    assert match["status"] == "NEW"
    assert match.get("lead_source") == "corporate"

    p = await client.patch(
        f"{LIST_PATH}/{lead_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert p.status_code == 200
    assert p.json().get("status") == "IN_PROGRESS"

    p2 = await client.patch(
        f"{LIST_PATH}/{lead_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CLOSED"},
    )
    assert p2.status_code == 200
    assert p2.json().get("status") == "CLOSED"
