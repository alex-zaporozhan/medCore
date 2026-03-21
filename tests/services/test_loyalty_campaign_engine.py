"""Tests for loyalty campaign engine (LOY_AI_014)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.application.services.loyalty_campaign_engine import (
    get_or_create_loyalty_campaign_settings,
    run_campaigns_for_clinic,
)
from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.task import Task
from src.domain.entities.wallet import Wallet
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_get_or_create_settings_idempotent(seed_data):
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        a = await get_or_create_loyalty_campaign_settings(session, clinic_id)
        b = await get_or_create_loyalty_campaign_settings(session, clinic_id)
        assert a.id == b.id
        await session.commit()


@pytest.mark.asyncio
async def test_run_campaigns_creates_expiring_task(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    service_id = seed_data["service_id"]

    async with db_base.AsyncSessionLocal() as session:
        pkg = SubscriptionPackage(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            code="t_pkg",
            name="Test Pkg",
            kind="visits",
            price=Decimal("1000.00"),
            services_included=[service_id],
            total_visits=5,
            total_amount=None,
            validity_days=365,
            description=None,
            is_active=True,
        )
        session.add(pkg)
        exp = utc_now() + timedelta(days=7)
        sub = CustomerSubscription(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient_id,
            subscription_package_id=pkg.id,
            status="active",
            purchased_at=utc_now(),
            activated_at=utc_now(),
            expires_at=exp,
            remaining_visits=3,
            remaining_amount=None,
        )
        session.add(sub)
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        r = await run_campaigns_for_clinic(session, clinic_id, limit=50)
        await session.commit()
        assert r.created_expiring >= 1

    async with db_base.AsyncSessionLocal() as session:
        q = await session.execute(
            select(Task).where(
                Task.clinic_id == clinic_id,
                Task.patient_id == patient_id,
                Task.attention_kind == "LOYALTY_EXPIRING_PACKAGE",
            )
        )
        tasks = list(q.scalars().all())
        assert len(tasks) >= 1
        assert tasks[0].source == "system"


@pytest.mark.asyncio
async def test_high_balance_skips_when_recent_visit(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Wallet(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                patient_id=patient_id,
                balance=Decimal("500.00"),
            )
        )
        today = date.today()
        session.add(
            Booking(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=today,
                appointment_time=datetime.now(timezone.utc).time().replace(tzinfo=None),
                status=BookingStatus.COMPLETED,
            )
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        r = await run_campaigns_for_clinic(session, clinic_id, limit=50)
        await session.commit()
        assert r.created_high_balance == 0


@pytest.mark.asyncio
async def test_channel_tasks_disabled_returns_zero(seed_data):
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        s = await get_or_create_loyalty_campaign_settings(session, clinic_id)
        s.channel_tasks_enabled = False
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        r = await run_campaigns_for_clinic(session, clinic_id)
        await session.commit()
        assert (
            r.created_expiring
            + r.created_high_balance
            + r.created_reengagement
            == 0
        )

    async with db_base.AsyncSessionLocal() as session:
        s = await get_or_create_loyalty_campaign_settings(session, clinic_id)
        s.channel_tasks_enabled = True
        await session.commit()
