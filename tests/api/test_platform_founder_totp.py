"""1a-E3: platform founder TOTP enroll, confirm, login MFA."""

from uuid import UUID

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import update

from src.core.config import settings
from src.core.security import create_platform_founder_access_token
from src.domain.entities.platform_founder_user import PlatformFounderUser
from src.infrastructure.database import base as db_base

LOGIN = "/api/v1/platform/auth/login"
LOGIN_MFA = "/api/v1/platform/auth/login/mfa"
ENROLL = "/api/v1/platform/auth/totp/enroll"
CONFIRM = "/api/v1/platform/auth/totp/confirm"


@pytest.fixture(autouse=True)
async def _reset_platform_founder_totp_after_each_totp_test(seed_data: dict):
    """Тесты в этом файле меняют TOTP у session-scoped founder; сбрасываем, чтобы не ломать другие модули."""
    yield
    await _reset_seed_founder_totp(seed_data["platform_founder_id"])


async def _reset_seed_founder_totp(platform_founder_id: UUID) -> None:
    """Session-scoped seed mutates TOTP; later tests in file need a clean founder row."""
    async with db_base.AsyncSessionLocal() as session:
        await session.execute(
            update(PlatformFounderUser)
            .where(PlatformFounderUser.id == platform_founder_id)
            .values(totp_enabled=False, totp_secret_ciphertext=None)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_platform_founder_totp_enroll_confirm_then_login_requires_mfa(
    client: AsyncClient, seed_data: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")

    login1 = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert login1.status_code == 200
    token1 = login1.json().get("access_token")
    assert token1

    r_enroll = await client.post(ENROLL, headers={"Authorization": f"Bearer {token1}"})
    assert r_enroll.status_code == 200
    body = r_enroll.json()
    uri = body.get("otpauth_uri")
    assert uri
    totp = pyotp.parse_uri(uri)
    code = totp.now()

    r_confirm = await client.post(
        CONFIRM,
        headers={"Authorization": f"Bearer {token1}"},
        json={"code": code},
    )
    assert r_confirm.status_code == 200
    token_after = r_confirm.json().get("access_token")
    assert token_after

    login2 = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert login2.status_code == 200
    data2 = login2.json()
    assert data2.get("mfa_required") is True
    assert data2.get("mfa_token")
    assert data2.get("access_token") in (None, "")

    code2 = totp.now()
    r_mfa = await client.post(
        LOGIN_MFA,
        json={"mfa_token": data2["mfa_token"], "totp_code": code2},
    )
    assert r_mfa.status_code == 200
    assert r_mfa.json().get("access_token")

    login3 = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
            "totp_code": totp.now(),
        },
    )
    assert login3.status_code == 200
    assert login3.json().get("access_token")


@pytest.mark.asyncio
async def test_platform_founder_totp_rejects_wrong_code_on_login_with_totp(
    client: AsyncClient, seed_data: dict, monkeypatch: pytest.MonkeyPatch
):
    await _reset_seed_founder_totp(seed_data["platform_founder_id"])
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    login1 = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    token1 = login1.json()["access_token"]
    r_enroll = await client.post(ENROLL, headers={"Authorization": f"Bearer {token1}"})
    totp = pyotp.parse_uri(r_enroll.json()["otpauth_uri"])
    await client.post(
        CONFIRM,
        headers={"Authorization": f"Bearer {token1}"},
        json={"code": totp.now()},
    )

    bad = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
            "totp_code": "000000",
        },
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_platform_founder_totp_enroll_409_when_already_enabled(
    client: AsyncClient, seed_data: dict, monkeypatch: pytest.MonkeyPatch
):
    await _reset_seed_founder_totp(seed_data["platform_founder_id"])
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    login1 = await client.post(
        LOGIN,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    token1 = login1.json()["access_token"]
    r_enroll = await client.post(ENROLL, headers={"Authorization": f"Bearer {token1}"})
    totp = pyotp.parse_uri(r_enroll.json()["otpauth_uri"])
    await client.post(
        CONFIRM,
        headers={"Authorization": f"Bearer {token1}"},
        json={"code": totp.now()},
    )

    token2 = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    again = await client.post(ENROLL, headers={"Authorization": f"Bearer {token2}"})
    assert again.status_code == 409
