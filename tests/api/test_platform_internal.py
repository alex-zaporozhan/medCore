"""Phase 1a: platform founder JWT is separate from clinic admin (ADR-007)."""

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.core.datetime_utils import utc_now
from src.core.security import create_platform_founder_access_token
from src.domain.entities.organization import Organization
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.infrastructure.database import base as db_base

HEALTH_PATH = "/api/v1/platform/internal/health"
PROVISION_QUEUE_PATH = "/api/v1/platform/internal/provision-queue"
DASHBOARD_SUMMARY_PATH = "/api/v1/platform/internal/dashboard-summary"
SESSION_PATH = "/api/v1/admin/auth/session"
LOGIN_PATH = "/api/v1/platform/auth/login"


@pytest.mark.asyncio
async def test_platform_internal_health_requires_founder_jwt(client: AsyncClient, seed_data: dict):
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("scope") == "platform"
    assert body.get("status") == "ok"


@pytest.mark.asyncio
async def test_platform_internal_health_rejects_admin_jwt(client: AsyncClient, admin_auth: dict):
    r = await client.get(
        HEALTH_PATH,
        headers={"Authorization": f"Bearer {admin_auth['access_token']}"},
    )
    # 1a-E6: tenant JWT has iss/aud for clinic contour — founder verify rejects before type check → 401.
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_health_rejects_patient_jwt(client: AsyncClient, patient_auth: dict):
    r = await client.get(
        HEALTH_PATH,
        headers={"Authorization": f"Bearer {patient_auth['access_token']}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_health_unauthorized_without_bearer(client: AsyncClient):
    r = await client.get(HEALTH_PATH)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_rejects_admin_jwt_when_founder_secret_isolated(
    client: AsyncClient,
    admin_auth: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    QA_ARCH: with PLATFORM_FOUNDER_JWT_SECRET distinct from JWT_SECRET_KEY, tenant admin tokens
    must not decode as founder (401), not 403 after a false-positive decode.
    """
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    r = await client.get(
        HEALTH_PATH,
        headers={"Authorization": f"Bearer {admin_auth['access_token']}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_health_ok_with_isolated_founder_secret(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json().get("scope") == "platform"


@pytest.mark.asyncio
async def test_platform_internal_503_in_production_when_founder_secret_unset(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Deploy-friendly: API starts; platform-internal disabled until secret is provisioned."""
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "")
    r = await client.get(HEALTH_PATH)
    assert r.status_code == 503
    assert r.json().get("code") == "platform_founder_jwt_not_configured"


@pytest.mark.asyncio
async def test_admin_session_rejects_platform_founder_jwt(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """Cross-realm: tenant admin session endpoint must not accept platform_founder Bearer."""
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-signing-key-isolated-test")
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(SESSION_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_provision_queue_requires_founder_jwt(client: AsyncClient):
    r = await client.get(PROVISION_QUEUE_PATH)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_dashboard_summary_counts_active_org_and_mrr(client: AsyncClient, seed_data: dict):
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r0 = await client.get(DASHBOARD_SUMMARY_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r0.status_code == 200
    j0 = r0.json()
    baseline_active = int(j0.get("active_organizations") or 0)
    baseline_mrr = float(j0.get("mrr_rub_monthly") or 0)

    org_id = uuid4()
    intent_id = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Organization(id=org_id, name="Dash Summary Org"))
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="active",
                email="dash-summary@example.com",
                organization_id=org_id,
                tariff_snapshot={
                    "plan_slug": "start",
                    "billing_period": "monthly",
                    "extra_entitlement_keys": [],
                },
            )
        )
        await session.commit()

    r = await client.get(DASHBOARD_SUMMARY_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("active_organizations") == baseline_active + 1
    # mrr_partial может оставаться True из‑за других org в общей БД (session seed); важен прирост по каталогу.
    assert float(body.get("mrr_rub_monthly", "0")) == pytest.approx(baseline_mrr + 20.0)
    assert body.get("currency") == "USD"


@pytest.mark.asyncio
async def test_platform_internal_provision_queue_rejects_admin_jwt(client: AsyncClient, admin_auth: dict):
    r = await client.get(
        PROVISION_QUEUE_PATH,
        headers={"Authorization": f"Bearer {admin_auth['access_token']}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_internal_provision_queue_ok_for_founder(client: AsyncClient, seed_data: dict):
    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.get(PROVISION_QUEUE_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_platform_founder_login_returns_token(client: AsyncClient, seed_data: dict):
    r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("access_token")
    assert data.get("founder_id") == str(seed_data["platform_founder_id"])


@pytest.mark.asyncio
async def test_platform_founder_login_rejects_wrong_password(client: AsyncClient, seed_data: dict):
    r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": "definitely-not-the-seed-password",
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_platform_founder_login_503_in_production_when_founder_secret_unset(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "")
    r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert r.status_code == 503
    assert r.json().get("code") == "platform_founder_jwt_not_configured"


@pytest.mark.asyncio
async def test_platform_founder_login_token_valid_for_internal_health(client: AsyncClient, seed_data: dict):
    login_r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert login_r.status_code == 200, login_r.text
    token = login_r.json()["access_token"]
    health_r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert health_r.status_code == 200
    assert health_r.json().get("scope") == "platform"


@pytest.mark.asyncio
async def test_platform_internal_rejects_founder_jwt_unknown_sub(client: AsyncClient):
    """1a-E2: valid signature but no platform_founder_users row → 403."""
    from uuid import uuid4

    token = create_platform_founder_access_token(subject=uuid4())
    r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json().get("code") == "platform_founder_inactive_or_unknown"


@pytest.mark.asyncio
async def test_platform_internal_rejects_founder_jwt_wrong_audience_when_strict(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1a-E6 / QA_ARCH: founder key + wrong aud → 401 with invalid_token_audience when legacy off."""
    founder_key = "founder-signing-key-strict-aud-integration-test"
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", founder_key)
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    uid = seed_data["platform_founder_id"]
    expire = utc_now() + timedelta(minutes=10)
    payload = {
        "sub": str(uid),
        "type": "platform_founder",
        "iss": settings.jwt_issuer_platform,
        "aud": "wrong-audience-for-integration-test",
        "iat": utc_now(),
        "exp": expire,
    }
    token = jwt.encode(payload, founder_key, algorithm=settings.jwt_algorithm)
    r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json().get("code") == "invalid_token_audience"


@pytest.mark.asyncio
async def test_platform_internal_forbidden_when_totp_required_and_not_enrolled(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PRC-A2: prod policy blocks internal API until TOTP is enabled on the user row."""
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-key-totp-required-test")
    monkeypatch.setattr(settings, "platform_founder_totp_required", True)
    login_r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert login_r.status_code == 200, login_r.text
    token = login_r.json()["access_token"]
    health_r = await client.get(HEALTH_PATH, headers={"Authorization": f"Bearer {token}"})
    assert health_r.status_code == 403
    assert health_r.json().get("code") == "platform_founder_totp_enrollment_required"


@pytest.mark.asyncio
async def test_platform_totp_enroll_allowed_when_totp_required_not_yet_enrolled(
    client: AsyncClient,
    seed_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap: TOTP enroll must work while internal routes are gated."""
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "founder-key-totp-required-test")
    monkeypatch.setattr(settings, "platform_founder_totp_required", True)
    login_r = await client.post(
        LOGIN_PATH,
        json={
            "email": seed_data["platform_founder_email"],
            "password": seed_data["platform_founder_password"],
        },
    )
    assert login_r.status_code == 200, login_r.text
    token = login_r.json()["access_token"]
    enroll_r = await client.post(
        "/api/v1/platform/auth/totp/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enroll_r.status_code == 200, enroll_r.text
    assert enroll_r.json().get("otpauth_uri")


@pytest.mark.asyncio
async def test_platform_internal_manual_close_reconcile_success(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="dead_letter",
                email="manual-close@example.com",
                provision_dead_letter=True,
                provision_last_error="DLQ: provisioning crashed",
            )
        )
        await session.commit()

    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/manual-close",
        headers={"Authorization": f"Bearer {token}"},
        json={"note": "closed by founder after external reconcile"},
    )
    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "reconcile_closed_manual"
        assert intent.provision_dead_letter is False
        assert "external reconcile" in (intent.notes or "")


@pytest.mark.asyncio
async def test_platform_internal_manual_close_reconcile_idempotent(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="dead_letter",
                email="manual-close-idem@example.com",
                provision_dead_letter=True,
                provision_last_error="DLQ",
            )
        )
        await session.commit()

    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    body = {"note": "first close"}
    r1 = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/manual-close",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    assert r1.status_code == 200
    r2 = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/manual-close",
        headers={"Authorization": f"Bearer {token}"},
        json={"note": "second should noop"},
    )
    assert r2.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "reconcile_closed_manual"
        assert intent.provision_dead_letter is False
        assert intent.notes.count("first close") == 1
        assert "second should noop" not in (intent.notes or "")


@pytest.mark.asyncio
async def test_platform_internal_manual_close_reconcile_forbidden_for_pending(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="pending_payment",
                email="manual-close-forbidden@example.com",
            )
        )
        await session.commit()

    token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/manual-close",
        headers={"Authorization": f"Bearer {token}"},
        json={"note": "should fail"},
    )
    assert r.status_code == 409
    assert r.json().get("code") == "invalid_intent_status_for_manual_close"
