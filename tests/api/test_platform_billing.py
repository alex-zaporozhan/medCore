"""Tests: platform billing webhook (contour B) — separate path and secret from patient payments."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY

from sqlalchemy import select

from src.core.config import settings
from src.domain.entities.clinic import Clinic
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment
from src.application.services.platform_billing_service import (
    BILLING_REVOKED_ENTITLEMENT_KEY,
    ENTITLEMENT_SOURCE_BILLING_REVOCATION,
    PlatformProvisionRetryNotAllowed,
    expire_stale_platform_signup_intents,
    record_platform_provision_failure,
    run_due_platform_provisions,
)
from src.core.security import create_platform_founder_access_token
from src.infrastructure.database import base as db_base
from src.infrastructure.external_apis.yookassa_client import YooKassaClientError

WEBHOOK_PATH = "/api/v1/platform/billing/webhooks/yookassa"
SECRET_HEADER = "X-Platform-Billing-Webhook-Secret"
TEST_SECRET = "test-platform-billing-webhook-secret"


def _ttl_expired_counter_value() -> float:
    base = "platform_signup_intent_ttl_expired"
    for family in REGISTRY.collect():
        if family.name != base:
            continue
        for sample in family.samples:
            if sample.name.endswith("_total") and not sample.labels:
                return float(sample.value)
    return 0.0


def _fake_yookassa_class(
    *,
    assert_payment_id: str | None = None,
    amount_value: str = "1000.00",
):
    """Return a YooKassaClient substitute that always returns succeeded."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "succeeded",
                "id": pid,
                "amount": {"value": amount_value, "currency": "RUB"},
            }

    return _FakeYooKassa


def _fake_yookassa_canceled(*, assert_payment_id: str | None = None):
    """YooKassa API says payment was canceled (no provisioning)."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "canceled",
                "id": pid,
                "amount": {"value": "1000.00", "currency": "RUB"},
            }

    return _FakeYooKassa


def _fake_yookassa_refunded(*, assert_payment_id: str | None = None):
    """YooKassa API says payment was refunded (ADR-012 revocation)."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "refunded",
                "id": pid,
                "amount": {"value": "1000.00", "currency": "RUB"},
            }

    return _FakeYooKassa


def _fake_yookassa_chargeback(*, assert_payment_id: str | None = None):
    """Provider dispute/chargeback terminal status (ADR-012)."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "chargeback",
                "id": pid,
                "amount": {"value": "1000.00", "currency": "RUB"},
            }

    return _FakeYooKassa


def _fake_yookassa_succeeded_full_refund_via_amount(
    *, assert_payment_id: str | None = None, amount_value: str = "1000.00"
):
    """OpenAPI: PaymentStatus stays succeeded; full refund via refunded_amount (YooKassa YAML)."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "succeeded",
                "id": pid,
                "amount": {"value": amount_value, "currency": "RUB"},
                "refunded_amount": {"value": amount_value, "currency": "RUB"},
            }

    return _FakeYooKassa


def _fake_yookassa_waiting_for_capture(*, assert_payment_id: str | None = None):
    """Two-phase payment: authorized, not captured yet (no provisioning)."""

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            if assert_payment_id is not None:
                assert pid == assert_payment_id
            return {
                "status": "waiting_for_capture",
                "id": pid,
                "amount": {"value": "1000.00", "currency": "RUB"},
            }

    return _FakeYooKassa


async def _insert_intent_and_payment(
    *,
    intent_id: UUID,
    pay_row_id: UUID,
    provider_pid: str,
    email: str,
    tariff_snapshot: dict | None = None,
) -> None:
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="pending_payment",
                email=email,
                tariff_snapshot=tariff_snapshot,
            )
        )
        session.add(
            PlatformSubscriptionPayment(
                id=pay_row_id,
                signup_intent_id=intent_id,
                provider="yookassa",
                provider_payment_id=provider_pid,
                amount=1000,
                currency="RUB",
                status="pending",
            )
        )
        await session.commit()


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_requires_secret(client: AsyncClient):
    r = await client.post(
        WEBHOOK_PATH,
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "x"}},
        headers={SECRET_HEADER: "wrong"},
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("code") == "platform_webhook_invalid_signature"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_yookassa_unavailable_returns_502(client: AsyncClient):
    """P0-3: known platform payment row but get_payment fails → 502, no paid transition."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-fail-{uuid4().hex[:12]}"
    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="verify-fail@example.com",
        tariff_snapshot=None,
    )

    class _BoomYooKassa:
        def get_payment(self, pid: str) -> dict:
            assert pid == provider_pid
            raise YooKassaClientError("simulated upstream")

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_BoomYooKassa(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json={
                "type": "notification",
                "event": "payment.succeeded",
                "object": {"id": provider_pid},
            },
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 502
    assert r.json().get("code") == "provider_verify_failed"

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert intent is not None
        assert intent.status == "pending_payment"
        assert pay is not None
        assert pay.status == "pending"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_succeeded_twice_idempotent(client: AsyncClient):
    """
    Two payment.succeeded notifications for contour B with same provider_payment_id:
    one Organization, idempotent second POST (U-006 / ADR-011).
    """
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="owner@example.com",
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r1 = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
        r2 = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert intent is not None
        assert intent.status == "active"
        assert intent.organization_id is not None
        assert pay is not None
        assert pay.status == "succeeded"

        org = await session.get(Organization, intent.organization_id)
        assert org is not None
        res = await session.execute(
            select(Clinic).where(Clinic.organization_id == intent.organization_id)
        )
        assert len(list(res.scalars().all())) == 1


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_writes_organization_entitlements(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="entitlements@example.com",
        tariff_snapshot={"keys": ["tasks.kanban"]},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        res = await session.execute(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == intent.organization_id
            )
        )
        keys = sorted({row.entitlement_key for row in res.scalars().all()})
        assert "core.base" in keys
        assert "tasks.kanban" in keys


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_owner_invite_mint_and_accept(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"
    owner_email = f"owner-{uuid4().hex[:12]}@example.com"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email=owner_email,
        tariff_snapshot={"keys": ["core.base"]},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        wh = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert wh.status_code == 200

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    mint_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/owner-invite-token",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert mint_r.status_code == 200
    raw_token = mint_r.json()["token"]

    accept_r = await client.post(
        "/api/v1/public/platform/owner-invite/accept",
        json={"token": raw_token, "password": "AcceptP1bPass!"},
    )
    assert accept_r.status_code == 200

    login_r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_email, "password": "AcceptP1bPass!"},
    )
    assert login_r.status_code == 200
    assert login_r.json().get("access_token")


@pytest.mark.regression_payments
@pytest.mark.security
@pytest.mark.asyncio
async def test_platform_provisioned_clinic_not_accessible_to_other_admin(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """
    Phase 1a / ADR-007 track B: after contour B provisions a new org+clinic,
    an existing clinic admin must not read that clinic via tenant admin API.

    U-011: unauthenticated GET /clinics/{id} must not resolve UUID → clinic (404).
    """
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="other-owner@example.com",
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class()(),
    ):
        wh = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert wh.status_code == 200

    new_clinic_id: UUID | None = None
    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        res = await session.execute(
            select(Clinic).where(Clinic.organization_id == intent.organization_id)
        )
        clinics = list(res.scalars().all())
        assert len(clinics) == 1
        new_clinic_id = clinics[0].id

    assert new_clinic_id is not None
    assert new_clinic_id != seed_data["clinic_id"]

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{new_clinic_id}/services",
        headers=headers,
    )
    assert r.status_code == 404

    r_pub = await client.get(f"/api/v1/clinics/{new_clinic_id}")
    assert r_pub.status_code == 404


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_canceled_updates_payment_only(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="canceled@example.com",
    )

    payload = {
        "type": "notification",
        "event": "payment.canceled",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_canceled(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert intent is not None
        assert pay is not None
        assert pay.status == "canceled"
        assert intent.organization_id is None
        assert intent.status == "pending_payment"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_tariff_plan_slug_merges_catalog_option_keys(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="planslug@example.com",
        tariff_snapshot={"plan_slug": "start"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        res = await session.execute(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == intent.organization_id
            )
        )
        keys = sorted({row.entitlement_key for row in res.scalars().all()})
        assert "core.base" in keys
        assert "tasks.kanban" in keys


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_tariff_plan_slug_case_insensitive_merge_keys(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="planslugcase@example.com",
        tariff_snapshot={"plan_slug": "START"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        res = await session.execute(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == intent.organization_id
            )
        )
        keys = sorted({row.entitlement_key for row in res.scalars().all()})
        assert "tasks.kanban" in keys


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_webhook_tariff_gate_invalid_billing_period_no_provision(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="badperiod@example.com",
        tariff_snapshot={"plan_slug": "start", "billing_period": "weekly"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.organization_id is None
        assert intent.status == "pending_payment"
        assert intent.provision_last_error and "invalid_billing_period" in intent.provision_last_error


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_webhook_tariff_gate_amount_mismatch_no_provision(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="amountbad@example.com",
        tariff_snapshot={"plan_slug": "start", "billing_period": "monthly"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid, amount_value="1000.00")(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.organization_id is None
        assert intent.status == "pending_payment"
        assert intent.provision_last_error and "amount_mismatch_catalog" in intent.provision_last_error


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_webhook_tariff_gate_monthly_price_matches_catalog(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="amountok@example.com",
        tariff_snapshot={"plan_slug": "start", "billing_period": "monthly"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid, amount_value="20.00")(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.organization_id is not None
        assert intent.status == "active"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_force_retry_409_when_payment_not_succeeded(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="unpaid-retry@example.com",
    )

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    retry_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/retry-provision",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert retry_r.status_code == 409
    body = retry_r.json()
    # main.py HTTP handler: machine code on top level, detail is human string
    assert body.get("code") == "payment_not_succeeded"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_force_retry_succeeds_when_intent_expired_but_payment_succeeded(
    client: AsyncClient,
    seed_data: dict,
):
    """QA_ARCH: reconcile — intent помечен expired TTL-job'ом, но платёж в БД уже succeeded."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="expired-paid-retry@example.com",
    )
    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert intent is not None and pay is not None
        pay.status = "succeeded"
        intent.status = "expired"
        await session.commit()

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    retry_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/retry-provision",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert retry_r.status_code == 200


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_force_retry_409_when_execute_catalog_gate_blocks(
    client: AsyncClient,
    seed_data: dict,
):
    """1b-E5: founder retry must not bypass catalog amount gate (same as Celery path)."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="gate-retry@example.com",
        tariff_snapshot={"plan_slug": "start", "billing_period": "monthly"},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(
            assert_payment_id=provider_pid,
            amount_value="20.00",
        )(),
    ):
        with patch(
            "src.application.services.platform_billing_service.execute_platform_provision",
            side_effect=RuntimeError("simulated provision failure"),
        ):
            wh = await client.post(
                WEBHOOK_PATH,
                json=payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
    assert wh.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert pay is not None
        pay.amount = Decimal("1000.00")
        await session.commit()

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    retry_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/retry-provision",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert retry_r.status_code == 409
    assert retry_r.json().get("code") == "amount_mismatch_catalog"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_record_provision_permanent_block_no_retry_increment(init_db):
    """QA_ARCH: гейт/данные без автоисправления — не сжигать backoff и не крутить Celery впустую.

    Depends on init_db (not only HTTP client): TESTING=1 defers AsyncSessionLocal until init_engine_for_testing().
    """
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="perm-block@example.com",
        tariff_snapshot={"plan_slug": "start", "billing_period": "monthly"},
    )

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        intent.status = "paid"
        intent.provision_retry_count = 0
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        await record_platform_provision_failure(
            session,
            intent_id,
            PlatformProvisionRetryNotAllowed("amount_mismatch_catalog"),
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert int(intent.provision_retry_count or 0) == 0
        assert intent.provision_last_error and intent.provision_last_error.startswith("provision_blocked:")
        assert intent.provision_next_attempt_at is None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_run_due_skips_provision_blocked_intent(init_db):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="skip-celery@example.com",
    )

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert intent is not None and pay is not None
        intent.status = "paid"
        intent.provision_last_error = "provision_blocked:amount_mismatch_catalog"
        pay.status = "succeeded"
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        n = await run_due_platform_provisions(session, limit=20)
    assert n == 0


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_waiting_for_capture_updates_payment_only(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="wfc@example.com",
    )

    payload = {
        "type": "notification",
        "event": "payment.waiting_for_capture",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_waiting_for_capture(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )

    assert r.status_code == 200
    async with db_base.AsyncSessionLocal() as session:
        pay = await session.get(PlatformSubscriptionPayment, pay_row_id)
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert pay is not None and intent is not None
        assert pay.status == "waiting_for_capture"
        assert intent.organization_id is None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_provision_fails_when_owner_email_already_registered(
    client: AsyncClient,
    seed_data: dict,
):
    """QA_ARCH: same email as existing clinic admin → fail closed, no fake-active tenant."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email=seed_data["admin_email"],
        tariff_snapshot={"keys": ["core.base"]},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        wh = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert wh.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "provision_failed"
        assert intent.organization_id is None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_provision_failure_then_founder_retry_succeeds(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="retry@example.com",
        tariff_snapshot={"keys": ["core.base"]},
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        with patch(
            "src.application.services.platform_billing_service.execute_platform_provision",
            side_effect=RuntimeError("simulated provision failure"),
        ):
            wh = await client.post(
                WEBHOOK_PATH,
                json=payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
    assert wh.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "provision_failed"
        assert int(intent.provision_retry_count or 0) >= 1
        assert intent.organization_id is None

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    retry_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/retry-provision",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert retry_r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "active"
        assert intent.organization_id is not None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_succeeded_on_expired_intent_provisions(client: AsyncClient):
    """Late payment.succeeded after TTL marked intent expired — still reconcile (STREAM cross-cutting / privacy TTL)."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="latepay@example.com",
    )
    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        intent.status = "expired"
        intent.expires_at = datetime.now(UTC) - timedelta(days=1)
        await session.commit()

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        r = await client.post(
            WEBHOOK_PATH,
            json=payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "active"
        assert intent.organization_id is not None


@pytest.mark.asyncio
async def test_expire_stale_platform_signup_intents_marks_pending_over_ttl(init_db):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="stale@example.com",
    )
    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        intent.expires_at = datetime.now(UTC) - timedelta(hours=2)
        await session.commit()

    before_m = _ttl_expired_counter_value()
    async with db_base.AsyncSessionLocal() as session:
        n = await expire_stale_platform_signup_intents(session, limit=50)
        await session.commit()
        assert n >= 1
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "expired"
    assert _ttl_expired_counter_value() == before_m + 1.0


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_rate_limit_second_request_429(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
    from src.main import app

    monkeypatch.setattr(settings, "rate_platform_billing_webhook_ip_limit", 10)

    class _CountingRl:
        def __init__(self) -> None:
            self.n = 0

        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            self.n += 1
            if self.n > 1:
                raise RateLimitExceeded(key=key, limit=limit, window=window)

    rl = _CountingRl()

    async def _fake_dep():
        return rl

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        body = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": "no-row-but-rate-limit-first"},
        }
        r1 = await client.post(
            WEBHOOK_PATH,
            json=body,
            headers={SECRET_HEADER: TEST_SECRET},
        )
        r2 = await client.post(
            WEBHOOK_PATH,
            json=body,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)

    assert r1.status_code != 429
    assert r2.status_code == 429
    assert r2.json().get("code") == "rate_limited"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_webhook_rate_limit_uses_xff_when_trusted_proxy(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """PRC-B7: behind edge with PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS, limit key uses X-Forwarded-For client."""
    from src.infrastructure.rate_limiter import get_rate_limiter
    from src.main import app

    # ASGITransport peer may be 127.0.0.1 or test harness-specific; trust all so XFF is honored in CI.
    monkeypatch.setattr(settings, "public_rate_limit_trusted_proxy_cidrs", "0.0.0.0/0")
    monkeypatch.setattr(settings, "rate_platform_billing_webhook_ip_limit", 100)

    seen_keys: list[str] = []

    class _CaptureRl:
        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            seen_keys.append(key)

    cap = _CaptureRl()

    async def _fake_dep():
        return cap

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        body = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": "no-such-payment-xff"},
        }
        await client.post(
            WEBHOOK_PATH,
            json=body,
            headers={
                SECRET_HEADER: TEST_SECRET,
                "x-forwarded-for": "203.0.113.44, 127.0.0.1",
            },
        )
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)

    assert seen_keys, "rate limiter should run when limit > 0"
    assert seen_keys[0] == "rate:platform_billing_webhook:ip:203.0.113.44"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_refund_after_provision_revokes_entitlements_and_blocks_login(
    client: AsyncClient,
    seed_data: dict,
):
    """ADR-012: succeeded → provision → refunded → suspended + marker entitlement; owner login 403."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"
    owner_email = f"revoke-{uuid4().hex[:12]}@example.com"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email=owner_email,
        tariff_snapshot={"keys": ["tasks.kanban"]},
    )

    ok_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    refund_payload = {
        "type": "notification",
        "event": "payment.refunded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        wh_ok = await client.post(
            WEBHOOK_PATH,
            json=ok_payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert wh_ok.status_code == 200

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    mint_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/owner-invite-token",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert mint_r.status_code == 200
    raw_token = mint_r.json()["token"]

    accept_r = await client.post(
        "/api/v1/public/platform/owner-invite/accept",
        json={"token": raw_token, "password": "RefundRevokeP1b!"},
    )
    assert accept_r.status_code == 200

    login_before = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_email, "password": "RefundRevokeP1b!"},
    )
    assert login_before.status_code == 200
    access_token = login_before.json()["access_token"]

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_refunded(assert_payment_id=provider_pid)(),
    ):
        wh_ref = await client.post(
            WEBHOOK_PATH,
            json=refund_payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert wh_ref.status_code == 200

    session_r = await client.get(
        "/api/v1/admin/auth/session",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert session_r.status_code == 403

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "suspended"
        assert intent.billing_revoked_at is not None
        assert intent.organization_id is not None
        res = await session.execute(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == intent.organization_id
            )
        )
        rows = list(res.scalars().all())
        assert len(rows) == 1
        assert rows[0].entitlement_key == BILLING_REVOKED_ENTITLEMENT_KEY
        assert rows[0].source == ENTITLEMENT_SOURCE_BILLING_REVOCATION

    login_after = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_email, "password": "RefundRevokeP1b!"},
    )
    assert login_after.status_code == 403


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_refund_webhook_twice_idempotent(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="idemp-refund@example.com",
    )

    ok_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    refund_payload = {
        "type": "notification",
        "event": "payment.refunded",
        "object": {"id": provider_pid},
    }

    fake_refunded = _fake_yookassa_refunded(assert_payment_id=provider_pid)

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=ok_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=fake_refunded(),
    ):
        r1 = await client.post(
            WEBHOOK_PATH,
            json=refund_payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
        r2 = await client.post(
            WEBHOOK_PATH,
            json=refund_payload,
            headers={SECRET_HEADER: TEST_SECRET},
        )
    assert r1.status_code == 200
    assert r2.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        res = await session.execute(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == intent.organization_id
            )
        )
        assert len(list(res.scalars().all())) == 1


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_chargeback_revokes_entitlements(client: AsyncClient):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="chargeback@example.com",
        tariff_snapshot={"keys": ["tasks.kanban"]},
    )

    succeeded_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    chargeback_payload = {
        "type": "notification",
        "event": "payment.chargeback",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=succeeded_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_chargeback(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=chargeback_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "suspended"
        assert intent.billing_revoked_at is not None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_billing_openapi_succeeded_with_refunded_amount_revokes(client: AsyncClient):
    """Full refund per OpenAPI: status=succeeded, refunded_amount covers amount (not a separate status)."""
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="openapi-refund-amount@example.com",
        tariff_snapshot={"keys": ["tasks.kanban"]},
    )

    ok_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    refund_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=ok_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_succeeded_full_refund_via_amount(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=refund_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "suspended"
        assert intent.billing_revoked_at is not None


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_platform_retry_provision_409_when_billing_revoked(client: AsyncClient, seed_data: dict):
    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-yk-{uuid4().hex[:16]}"

    await _insert_intent_and_payment(
        intent_id=intent_id,
        pay_row_id=pay_row_id,
        provider_pid=provider_pid,
        email="retry-revoked@example.com",
    )

    ok_payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    refund_payload = {
        "type": "notification",
        "event": "payment.refunded",
        "object": {"id": provider_pid},
    }

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=ok_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    with patch(
        "src.application.services.platform_billing_service.YooKassaClient",
        return_value=_fake_yookassa_refunded(assert_payment_id=provider_pid)(),
    ):
        assert (
            await client.post(
                WEBHOOK_PATH,
                json=refund_payload,
                headers={SECRET_HEADER: TEST_SECRET},
            )
        ).status_code == 200

    founder_token = create_platform_founder_access_token(subject=seed_data["platform_founder_id"])
    retry_r = await client.post(
        f"/api/v1/platform/internal/signup-intents/{intent_id}/retry-provision",
        headers={"Authorization": f"Bearer {founder_token}"},
    )
    assert retry_r.status_code == 409
    assert retry_r.json().get("code") == "billing_revoked"


@pytest.mark.asyncio
async def test_platform_billing_webhook_unknown_provider_returns_404(client: AsyncClient):
    r = await client.post(
        "/api/v1/platform/billing/webhooks/stripe",
        headers={"X-Platform-Billing-Webhook-Secret": TEST_SECRET},
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "x"}},
    )
    assert r.status_code == 404
    assert r.json().get("code") == "unknown_provider"
