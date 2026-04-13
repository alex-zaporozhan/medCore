"""Contour B: platform signup provision via domain_outbox (ADR-009 §17.1 / 2-E1)."""

from datetime import time
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.domain_outbox import DomainOutbox
from src.infrastructure.database import base as db_base

WEBHOOK_PATH = "/api/v1/platform/billing/webhooks/yookassa"
SECRET_HEADER = "X-Platform-Billing-Webhook-Secret"
TEST_SECRET = "test-platform-billing-webhook-secret"


@pytest.fixture(autouse=True)
async def _empty_domain_outbox_for_isolation(init_db):
    async with db_base.engine.begin() as conn:
        await conn.execute(text("DELETE FROM domain_outbox"))
    yield


def _fake_yookassa_class(*, assert_payment_id: str | None = None, amount_value: str = "1000.00"):
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


@pytest.mark.asyncio
async def test_platform_webhook_outbox_row_published_and_provisioned(seed_data: dict):
    """Succeeded webhook enqueues PlatformSignupProvision; dispatch leaves row published + org active."""
    from src.domain.entities.platform_signup_intent import PlatformSignupIntent
    from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment

    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-outbox-{uuid4().hex[:12]}"
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="pending_payment",
                email="outbox-owner@example.com",
                tariff_snapshot=None,
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

    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "src.application.services.platform_billing_service.YooKassaClient",
            return_value=_fake_yookassa_class(assert_payment_id=provider_pid)(),
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
    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        ob = (
            await session.execute(
                select(DomainOutbox).where(
                    DomainOutbox.dedup_key == f"platform_signup_provision:{intent_id}"
                )
            )
        ).scalar_one_or_none()
        assert ob is not None
        assert ob.published_at is not None
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent is not None
        assert intent.status == "active"
        assert intent.organization_id is not None


@pytest.mark.asyncio
async def test_dispatch_platform_outbox_redelivery_no_extra_org_rows(seed_data: dict):
    """Second dispatch after success does not create duplicate organizations."""
    from src.application.services.domain_outbox_service import (
        dispatch_domain_outbox_batch,
        enqueue_platform_signup_provision,
    )
    from src.domain.entities.platform_signup_intent import PlatformSignupIntent
    from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment
    from src.domain.entities.organization import Organization

    intent_id = uuid4()
    pay_row_id = uuid4()
    provider_pid = f"platform-redel-{uuid4().hex[:10]}"
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="paid",
                email="redel@example.com",
                tariff_snapshot=None,
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
                status="succeeded",
            )
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        await enqueue_platform_signup_provision(session, intent_id)
        await session.commit()

    n1 = await dispatch_domain_outbox_batch(limit=10)
    assert n1 >= 1
    n2 = await dispatch_domain_outbox_batch(limit=10)
    assert n2 == 0

    async with db_base.AsyncSessionLocal() as session:
        intent = await session.get(PlatformSignupIntent, intent_id)
        assert intent and intent.organization_id is not None
        org_count = await session.scalar(
            select(func.count()).select_from(Organization).where(Organization.id == intent.organization_id)
        )
        assert org_count == 1


@pytest.mark.asyncio
async def test_booking_outbox_dedup_and_second_dispatch_empty(seed_data: dict):
    """Same dedup_id: single row; second dispatch batch is empty."""
    from src.application.services.domain_outbox_service import (
        dispatch_domain_outbox_batch,
        enqueue_domain_event,
    )
    from src.application.events.standard_events import make_booking_created_event

    booking_id = uuid4()
    clinic_id = seed_data["clinic_id"]
    appt_time = time(14, 30, 0)
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=seed_data["date"],
                appointment_time=appt_time,
                status=BookingStatus.PENDING,
                prepayment_amount=0,
            )
        )
        await session.flush()
        booking = await session.get(Booking, booking_id)
        assert booking is not None
        ev = make_booking_created_event(booking, trace_id="t-redel", omnichannel_contact_id=None)
        await enqueue_domain_event(session, ev)
        await enqueue_domain_event(session, ev)
        await session.commit()

    n1 = await dispatch_domain_outbox_batch(limit=10)
    assert n1 == 1
    n2 = await dispatch_domain_outbox_batch(limit=10)
    assert n2 == 0

    async with db_base.AsyncSessionLocal() as session:
        cnt = await session.scalar(select(func.count()).select_from(DomainOutbox))
        assert int(cnt or 0) == 1


@pytest.mark.asyncio
async def test_booking_outbox_redelivery_republishes_event(seed_data: dict):
    """Simulate at-least-once: unpublish row and dispatch again — handler runs without duplicate DB row constraint."""
    from src.application.services.domain_outbox_service import (
        dispatch_domain_outbox_batch,
        enqueue_domain_event,
    )
    from src.application.events.standard_events import make_booking_created_event

    booking_id = uuid4()
    clinic_id = seed_data["clinic_id"]
    appt_time = time(15, 0, 0)
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=seed_data["date"],
                appointment_time=appt_time,
                status=BookingStatus.PENDING,
                prepayment_amount=0,
            )
        )
        await session.flush()
        booking = await session.get(Booking, booking_id)
        assert booking is not None
        await enqueue_domain_event(session, make_booking_created_event(booking, trace_id="t1"))
        await session.commit()

    assert await dispatch_domain_outbox_batch(limit=10) == 1

    async with db_base.AsyncSessionLocal() as session:
        row = (
            await session.execute(select(DomainOutbox).where(DomainOutbox.aggregate_id == booking_id))
        ).scalar_one()
        row.published_at = None
        row.attempts = 0
        await session.commit()

    assert await dispatch_domain_outbox_batch(limit=10) == 1
