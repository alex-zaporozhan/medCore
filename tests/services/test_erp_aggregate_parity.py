"""Engine L2: ERP visit-revenue vitrine totals match canonical raw query."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete

from src.application.services.erp_aggregate_service import ErpAggregateService
from src.application.services.erp_reports_repository import ErpReportsRepository
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.erp_report_buckets import (
    NULL_BOOKING_BUCKET,
    NULL_CAMPAIGN_BUCKET,
    NULL_TRAFFIC_SOURCE_BUCKET,
)
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.product import Product
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.entities.visit_attribution import VisitAttribution
from src.domain.entities.warehouse import Warehouse
from src.infrastructure.database import base as db_base


def _sort_key(r):
    bid = r.booking_id if r.booking_id is not None else NULL_BOOKING_BUCKET
    return (r.visit_date, bid, r.total_revenue)


@pytest.mark.asyncio
async def test_visit_revenue_aggregate_matches_raw_repository(init_db, seed_data) -> None:
    """After refresh, sum and per-row grain match ErpReportsRepository.get_visit_revenue_by_period."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=(uuid.uuid4().int % 300) + 1)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                delete(Booking).where(
                    Booking.clinic_id == clinic_id,
                    Booking.doctor_id == doctor_id,
                    Booking.appointment_date == day,
                    Booking.appointment_time.in_([time(10, 0), time(14, 0)]),
                )
            )
            cashbox = Cashbox(
                clinic_id=clinic_id,
                name="Parity test",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            )
            session.add(cashbox)
            await session.flush()

            bid1 = uuid.uuid4()
            session.add(
                Booking(
                    id=bid1,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(10, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            bid2 = uuid.uuid4()
            session.add(
                Booking(
                    id=bid2,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(14, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            await session.flush()

            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("100.00"),
                    booking_id=bid1,
                    happened_at=datetime.combine(day, time(10, 0), tzinfo=timezone.utc),
                    source="test_parity",
                )
            )
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("25.50"),
                    booking_id=None,
                    happened_at=datetime.combine(day, time(18, 30), tzinfo=timezone.utc),
                    source="test_parity",
                )
            )
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("10.00"),
                    booking_id=bid2,
                    happened_at=datetime.combine(day, time(14, 5), tzinfo=timezone.utc),
                    source="test_parity",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        repo = ErpReportsRepository(session)
        raw_rows = await repo.get_visit_revenue_by_period(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        raw_total = sum((r.total_revenue for r in raw_rows), start=Decimal("0"))

        svc = ErpAggregateService(session)
        await svc.refresh_visit_revenue_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )

        agg_rows = await svc.fetch_visit_revenue_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    agg_total = sum((r.total_revenue for r in agg_rows), start=Decimal("0"))
    assert raw_total == agg_total == Decimal("135.50")

    assert sorted(raw_rows, key=_sort_key) == sorted(agg_rows, key=_sort_key)

    async with db_base.AsyncSessionLocal() as session:
        svc2 = ErpAggregateService(session)
        mx = await svc2.max_aggregate_updated_at_for_range(
            clinic_id=clinic_id, date_from=day, date_to=day
        )
        assert mx is not None


@pytest.mark.asyncio
async def test_visit_revenue_aggregate_parity_with_negative_income_adjustments(
    init_db, seed_data,
) -> None:
    """A16: net income may be below gross after adjustments; aggregate matches raw."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=15)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            cashbox = Cashbox(
                clinic_id=clinic_id,
                name="Neg parity",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            )
            session.add(cashbox)
            await session.flush()

            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(11, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            await session.flush()
            base = datetime.combine(day, time(11, 0), tzinfo=timezone.utc)
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("200.00"),
                    booking_id=bid,
                    happened_at=base,
                    source="test_parity_neg",
                )
            )
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("-45.00"),
                    booking_id=bid,
                    happened_at=base,
                    source="test_parity_neg_adj",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        repo = ErpReportsRepository(session)
        raw_rows = await repo.get_visit_revenue_by_period(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        raw_total = sum((r.total_revenue for r in raw_rows), start=Decimal("0"))

        svc = ErpAggregateService(session)
        await svc.refresh_visit_revenue_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )

        agg_rows = await svc.fetch_visit_revenue_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    agg_total = sum((r.total_revenue for r in agg_rows), start=Decimal("0"))
    assert raw_total == agg_total == Decimal("155.00")
    assert sorted(raw_rows, key=_sort_key) == sorted(agg_rows, key=_sort_key)


@pytest.mark.asyncio
async def test_visit_revenue_aggregate_stale_range_triggers_fallback_metadata(
    init_db, seed_data, monkeypatch
) -> None:
    """When rows exist but updated_at for the range is older than threshold, API uses raw + flags."""
    from datetime import timedelta

    from httpx import ASGITransport, AsyncClient

    from src.core.config import settings as settings_mod
    from src.main import app as fastapi_app

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    # Own day so totals are isolated from test_visit_revenue_aggregate_matches_raw_repository.
    day: date = seed_data["date"] + timedelta(days=2)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            cashbox = Cashbox(
                clinic_id=clinic_id,
                name="Stale test",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            )
            session.add(cashbox)
            await session.flush()
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(15, 30),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            await session.flush()
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("50.00"),
                    booking_id=bid,
                    happened_at=datetime.combine(day, time(15, 30), tzinfo=timezone.utc),
                    source="test_stale",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        svc = ErpAggregateService(session)
        await svc.refresh_visit_revenue_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test_stale",
        )
        await session.commit()

    old_ts = datetime.now(timezone.utc) - timedelta(hours=3)
    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            from sqlalchemy import update

            from src.domain.entities.erp_visit_revenue_aggregate import ErpVisitRevenueAggregate

            await session.execute(
                update(ErpVisitRevenueAggregate)
                .where(
                    ErpVisitRevenueAggregate.clinic_id == clinic_id,
                    ErpVisitRevenueAggregate.visit_date == day,
                )
                .values(updated_at=old_ts)
            )
        await session.commit()

    monkeypatch.setattr(settings_mod, "erp_aggregate_stale_max_seconds", 60, raising=False)
    monkeypatch.setattr(settings_mod, "erp_reports_read_from_aggregate", True, raising=False)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["admin_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            f"/api/v1/admin/clinics/{clinic_id}/reports/revenue-by-period",
            headers=headers,
            params={"date_from": day.isoformat(), "date_to": day.isoformat()},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data_source"] == "raw"
        assert body["aggregate_stale"] is True
        assert body["aggregate_max_updated_at"] is not None
        assert Decimal(body["total_revenue"]) == Decimal("50.00")


def _payroll_sort_key(r):
    bid = r.booking_id if r.booking_id is not None else NULL_BOOKING_BUCKET
    ps = r.period_start or date.min
    pe = r.period_end or date.min
    return (r.doctor_id, ps, pe, bid, r.amount)


def _inv_key(r):
    bid = r.booking_id if r.booking_id is not None else NULL_BOOKING_BUCKET
    return (r.product_id, bid, r.total_quantity)


def _attr_sort_key(r):
    ts = r.traffic_source_id if r.traffic_source_id is not None else NULL_TRAFFIC_SOURCE_BUCKET
    cid = r.campaign_id if r.campaign_id is not None else NULL_CAMPAIGN_BUCKET
    return (r.visit_date, ts, cid, r.total_revenue)


@pytest.mark.asyncio
async def test_payroll_aggregate_matches_raw_repository(init_db, seed_data) -> None:
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=10)
    period_start = day - timedelta(days=1)
    period_end = day + timedelta(days=1)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(10, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            session.add(
                SalaryTransaction(
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    booking_id=bid,
                    amount=Decimal("300.00"),
                    type="accrual",
                    period_start=period_start,
                    period_end=period_end,
                    description="parity_payroll",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        repo = ErpReportsRepository(session)
        raw_rows = await repo.get_visit_payroll_by_period(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        svc = ErpAggregateService(session)
        await svc.refresh_payroll_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        agg_rows = await svc.fetch_payroll_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    assert sorted(raw_rows, key=_payroll_sort_key) == sorted(agg_rows, key=_payroll_sort_key)


@pytest.mark.asyncio
async def test_payroll_aggregate_preserves_extreme_calendar_dates(init_db, seed_data) -> None:
    """Real period_start/end equal to former sentinels must not decode as NULL (flags disambiguate)."""
    from datetime import date as date_cls

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=40)
    ps = date_cls(1, 1, 1)
    pe = date_cls(9999, 12, 31)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(10, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            session.add(
                SalaryTransaction(
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    booking_id=bid,
                    amount=Decimal("1.00"),
                    type="accrual",
                    period_start=ps,
                    period_end=pe,
                    description="extreme_dates",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        svc = ErpAggregateService(session)
        await svc.refresh_payroll_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        agg_rows = await svc.fetch_payroll_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    assert len(agg_rows) == 1
    assert agg_rows[0].period_start == ps
    assert agg_rows[0].period_end == pe


@pytest.mark.asyncio
async def test_materials_aggregate_matches_raw_repository(init_db, seed_data) -> None:
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=(uuid.uuid4().int % 300) + 1)
    booking_minute = (uuid.uuid4().int % 50) + 5
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            session.add(
                Warehouse(
                    id=warehouse_id,
                    clinic_id=clinic_id,
                    name="Parity warehouse",
                    is_default=True,
                )
            )
            session.add(
                Product(
                    id=product_id,
                    clinic_id=clinic_id,
                    name="Parity material",
                    unit="pcs",
                    is_active=True,
                )
            )
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(11, booking_minute),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            await session.flush()
            session.add(
                InventoryTransaction(
                    clinic_id=clinic_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    type="outgoing",
                    quantity=Decimal("1.250"),
                    happened_at=datetime.combine(day, time(9, 0), tzinfo=timezone.utc),
                    booking_id=bid,
                )
            )
            session.add(
                InventoryTransaction(
                    clinic_id=clinic_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    type="outgoing",
                    quantity=Decimal("2.000"),
                    happened_at=datetime.combine(day, time(21, 0), tzinfo=timezone.utc),
                    booking_id=bid,
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        repo = ErpReportsRepository(session)
        raw_rows = await repo.get_visit_inventory_by_period(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        svc = ErpAggregateService(session)
        await svc.refresh_inventory_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        agg_rows = await svc.fetch_inventory_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    assert raw_rows == sorted(
        raw_rows, key=lambda r: (r.product_id, r.booking_id or NULL_BOOKING_BUCKET)
    )
    assert agg_rows == sorted(
        agg_rows, key=lambda r: (r.product_id, r.booking_id or NULL_BOOKING_BUCKET)
    )
    assert sorted(raw_rows, key=_inv_key) == sorted(agg_rows, key=_inv_key)


@pytest.mark.asyncio
async def test_attribution_aggregate_matches_raw_repository(init_db, seed_data) -> None:
    clinic_id = seed_data["clinic_id"]
    day: date = seed_data["date"] + timedelta(days=12)
    happened = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            cashbox = Cashbox(
                clinic_id=clinic_id,
                name="Attr parity",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            )
            session.add(cashbox)
            await session.flush()
            attr = VisitAttribution(
                clinic_id=clinic_id,
                patient_id=None,
                lead_id=None,
                traffic_source_id=uuid.uuid4(),
                campaign_id=uuid.uuid4(),
                session_id="parity_sess",
                landing_page=None,
                anchor=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                utm_content=None,
                utm_term=None,
                created_at=happened,
            )
            session.add(attr)
            await session.flush()
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("88.00"),
                    booking_id=None,
                    happened_at=happened,
                    source="parity_attr",
                    visit_attribution_id=attr.id,
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        repo = ErpReportsRepository(session)
        raw_rows = await repo.get_attribution_revenue_by_period(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        svc = ErpAggregateService(session)
        await svc.refresh_attribution_revenue_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        agg_rows = await svc.fetch_attribution_revenue_aggregate(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
        )
        await session.commit()

    def _attr_order(r):
        ts = r.traffic_source_id if r.traffic_source_id is not None else NULL_TRAFFIC_SOURCE_BUCKET
        cid = r.campaign_id if r.campaign_id is not None else NULL_CAMPAIGN_BUCKET
        return (r.visit_date, ts, cid)

    assert raw_rows == sorted(raw_rows, key=_attr_order)
    assert agg_rows == sorted(agg_rows, key=_attr_order)
    assert sorted(raw_rows, key=_attr_sort_key) == sorted(agg_rows, key=_attr_sort_key)


@pytest.mark.asyncio
async def test_payroll_by_period_stale_range_triggers_fallback_metadata(
    init_db, seed_data, monkeypatch
) -> None:
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import update

    from src.core.config import settings as settings_mod
    from src.domain.entities.erp_payroll_aggregate import ErpPayrollAggregate
    from src.main import app as fastapi_app

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=50)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(10, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            session.add(
                SalaryTransaction(
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    booking_id=bid,
                    amount=Decimal("10.00"),
                    type="accrual",
                    period_start=day - timedelta(days=1),
                    period_end=day + timedelta(days=1),
                    description="stale_payroll",
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        svc = ErpAggregateService(session)
        await svc.refresh_payroll_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        await session.commit()

    old_ts = datetime.now(timezone.utc) - timedelta(hours=3)
    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(ErpPayrollAggregate).where(ErpPayrollAggregate.clinic_id == clinic_id).values(
                    updated_at=old_ts
                )
            )
        await session.commit()

    monkeypatch.setattr(settings_mod, "erp_aggregate_stale_max_seconds", 60, raising=False)
    monkeypatch.setattr(settings_mod, "erp_reports_read_from_aggregate", True, raising=False)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["admin_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            f"/api/v1/admin/clinics/{clinic_id}/reports/payroll-by-period",
            headers=headers,
            params={"date_from": day.isoformat(), "date_to": day.isoformat()},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data_source"] == "raw"
        assert body["aggregate_stale"] is True
        assert body["aggregate_max_updated_at"] is not None


@pytest.mark.asyncio
async def test_materials_by_period_stale_range_triggers_fallback_metadata(
    init_db, seed_data, monkeypatch
) -> None:
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import update

    from src.core.config import settings as settings_mod
    from src.domain.entities.erp_inventory_movement_aggregate import ErpInventoryMovementAggregate
    from src.main import app as fastapi_app

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day: date = seed_data["date"] + timedelta(days=51)
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            session.add(
                Warehouse(
                    id=warehouse_id,
                    clinic_id=clinic_id,
                    name="Stale wh",
                    is_default=True,
                )
            )
            session.add(
                Product(
                    id=product_id,
                    clinic_id=clinic_id,
                    name="Stale mat",
                    unit="pcs",
                    is_active=True,
                )
            )
            bid = uuid.uuid4()
            session.add(
                Booking(
                    id=bid,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    service_id=service_id,
                    appointment_date=day,
                    appointment_time=time(11, 0),
                    status=BookingStatus.CONFIRMED,
                    prepayment_amount=Decimal("0.00"),
                )
            )
            await session.flush()
            session.add(
                InventoryTransaction(
                    clinic_id=clinic_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    type="outgoing",
                    quantity=Decimal("3.000"),
                    happened_at=datetime.combine(day, time(12, 0), tzinfo=timezone.utc),
                    booking_id=bid,
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        svc = ErpAggregateService(session)
        await svc.refresh_inventory_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        await session.commit()

    old_ts = datetime.now(timezone.utc) - timedelta(hours=3)
    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(ErpInventoryMovementAggregate)
                .where(ErpInventoryMovementAggregate.clinic_id == clinic_id)
                .values(updated_at=old_ts)
            )
        await session.commit()

    monkeypatch.setattr(settings_mod, "erp_aggregate_stale_max_seconds", 60, raising=False)
    monkeypatch.setattr(settings_mod, "erp_reports_read_from_aggregate", True, raising=False)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["admin_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            f"/api/v1/admin/clinics/{clinic_id}/reports/materials-by-period",
            headers=headers,
            params={"date_from": day.isoformat(), "date_to": day.isoformat()},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data_source"] == "raw"
        assert body["aggregate_stale"] is True


@pytest.mark.asyncio
async def test_roi_by_source_stale_range_triggers_fallback_metadata(
    init_db, seed_data, monkeypatch
) -> None:
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import update

    from src.core.config import settings as settings_mod
    from src.domain.entities.erp_attribution_revenue_aggregate import ErpAttributionRevenueAggregate
    from src.main import app as fastapi_app

    clinic_id = seed_data["clinic_id"]
    day: date = seed_data["date"] + timedelta(days=52)
    happened = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)

    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            cashbox = Cashbox(
                clinic_id=clinic_id,
                name="Stale attr",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            )
            session.add(cashbox)
            await session.flush()
            attr = VisitAttribution(
                clinic_id=clinic_id,
                patient_id=None,
                lead_id=None,
                traffic_source_id=uuid.uuid4(),
                campaign_id=uuid.uuid4(),
                session_id="stale_sess",
                landing_page=None,
                anchor=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                utm_content=None,
                utm_term=None,
                created_at=happened,
            )
            session.add(attr)
            await session.flush()
            session.add(
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox.id,
                    type="income",
                    amount=Decimal("33.00"),
                    booking_id=None,
                    happened_at=happened,
                    source="stale_roi",
                    visit_attribution_id=attr.id,
                )
            )

    async with db_base.AsyncSessionLocal() as session:
        svc = ErpAggregateService(session)
        await svc.refresh_attribution_revenue_range(
            clinic_id=clinic_id,
            date_from=day,
            date_to=day,
            job_type="test",
        )
        await session.commit()

    old_ts = datetime.now(timezone.utc) - timedelta(hours=3)
    async with db_base.AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(ErpAttributionRevenueAggregate)
                .where(ErpAttributionRevenueAggregate.clinic_id == clinic_id)
                .values(updated_at=old_ts)
            )
        await session.commit()

    monkeypatch.setattr(settings_mod, "erp_aggregate_stale_max_seconds", 60, raising=False)
    monkeypatch.setattr(settings_mod, "erp_reports_read_from_aggregate", True, raising=False)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["admin_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            f"/api/v1/admin/clinics/{clinic_id}/reports/roi-by-source",
            headers=headers,
            params={"date_from": day.isoformat(), "date_to": day.isoformat()},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data_source"] == "raw"
        assert body["aggregate_stale"] is True
