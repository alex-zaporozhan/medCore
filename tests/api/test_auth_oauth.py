"""Tests for patient OAuth authentication (VK and Yandex)."""

import json
from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_oauth_vk_start_persists_state_and_redirects(client: AsyncClient, redis_client):
    response = await client.get("/api/v1/auth/oauth/vk/start", params={"redirect": "/app"})
    assert response.status_code == 302
    assert "https://oauth.vk.com/authorize" in response.headers["location"]

    # extract state from location
    location = response.headers["location"]
    assert "state=" in location
    state = location.split("state=")[1].split("&")[0]

    raw = await redis_client.get(f"auth:vk:state:{state}")
    assert raw
    payload = raw.decode() if isinstance(raw, bytes) else raw
    data = json.loads(payload)
    assert data.get("redirect") == "/app"


@pytest.mark.asyncio
async def test_oauth_vk_callback_invalid_state_redirects_to_login(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/oauth/vk/callback",
        params={"code": "dummy", "state": "nonexistent"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith("/app/login")
    assert "status=state_invalid" in response.headers["location"]


@pytest.mark.asyncio
async def test_oauth_vk_callback_error_param_results_in_cancelled(client: AsyncClient, redis_client):
    # Seed state with redirect
    state = "vk_state_cancel"
    await redis_client.setex(f"auth:vk:state:{state}", 600, json.dumps({"redirect": "/app"}))

    response = await client.get(
        "/api/v1/auth/oauth/vk/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/app?oauth=vk&status=cancelled"


@pytest.mark.asyncio
async def test_oauth_yandex_start_persists_state_and_redirects(client: AsyncClient, redis_client):
    response = await client.get("/api/v1/auth/oauth/yandex/start", params={"redirect": "/app"})
    assert response.status_code == 302
    assert "https://oauth.yandex.ru/authorize" in response.headers["location"]

    location = response.headers["location"]
    assert "state=" in location
    state = location.split("state=")[1].split("&")[0]

    raw = await redis_client.get(f"auth:yandex:state:{state}")
    assert raw
    payload = raw.decode() if isinstance(raw, bytes) else raw
    data = json.loads(payload)
    assert data.get("redirect") == "/app"


@pytest.mark.asyncio
async def test_oauth_yandex_callback_invalid_state_redirects_to_login(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/oauth/yandex/callback",
        params={"code": "dummy", "state": "nonexistent"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith("/app/login")
    assert "status=state_invalid" in response.headers["location"]


@pytest.mark.asyncio
async def test_oauth_yandex_callback_error_param_results_in_cancelled(client: AsyncClient, redis_client):
    state = "yandex_state_cancel"
    await redis_client.setex(f"auth:yandex:state:{state}", 600, json.dumps({"redirect": "/app"}))

    response = await client.get(
        "/api/v1/auth/oauth/yandex/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/app?oauth=yandex&status=cancelled"

