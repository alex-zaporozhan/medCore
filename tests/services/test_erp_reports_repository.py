from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.erp_reports_repository import ErpReportsRepository
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.clinic import Clinic
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.product import Product
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.entities.visit_attribution import VisitAttribution
from src.domain.entities.warehouse import Warehouse
from tests.booking_slot import unique_clock_time


async def _seed_cashbox_id(db_session: AsyncSession, clinic_id) -> object:
    cashbox_id = await db_session.scalar(
        select(Cashbox.id).where(Cashbox.clinic_id == clinic_id).order_by(Cashbox.is_default.desc())
    )
    assert cashbox_id is not None
    return cashbox_id


async def _create_booking_id(db_session: AsyncSession, seed_data, day: date) -> object:
    booking = Booking(
        clinic_id=seed_data["clinic_id"],
        patient_id=seed_data["patient_id"],
        doctor_id=seed_data["doctor_id"],
        service_id=seed_data["service_id"],
        appointment_date=day,
        appointment_time=unique_clock_time(hour=11),
        status=BookingStatus.CONFIRMED,
        prepayment_amount=Decimal("0.00"),
        payment_id=None,
        paid_by_subscription=False,
        notes="erp reports repo test",
    )
    db_session.add(booking)
    await db_session.flush()
    return booking.id


@pytest.mark.asyncio
async def test_get_visit_revenue_by_period_basic(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    today = date.today()
    booking_id = await _create_booking_id(db_session, seed_data, today)
    cashbox_id = await _seed_cashbox_id(db_session, clinic_id)

    tx = FinancialTransaction(
        clinic_id=clinic_id,
        cashbox_id=cashbox_id,
        type="income",
        amount=Decimal("100.00"),
        currency="RUB",
        happened_at=datetime.combine(today, datetime.min.time()),
        description="test",
        booking_id=booking_id,
        payment_id=None,
        source="booking_completed",
    )
    db_session.add(tx)
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    rows = await repo.get_visit_revenue_by_period(
        clinic_id=clinic_id,
        date_from=today,
        date_to=today,
    )
    target = next((r for r in rows if r.booking_id == booking_id), None)
    assert target is not None
    assert target.clinic_id == clinic_id
    assert target.total_revenue == Decimal("100.00")


@pytest.mark.asyncio
async def test_crm_lead_income_sum_aligns_with_visit_revenue_for_same_booking(
    db_session: AsyncSession, seed_data
) -> None:
    """CRM ``actual_value`` aggregate uses the same income rows as ERP visit revenue reports."""
    clinic_id = seed_data["clinic_id"]
    lead_id = uuid4()
    today = date.today()
    happened = datetime.combine(today, datetime.min.time())
    booking_id = await _create_booking_id(db_session, seed_data, today)
    cashbox_id = await _seed_cashbox_id(db_session, clinic_id)

    db_session.add(
        FinancialTransaction(
            clinic_id=clinic_id,
            cashbox_id=cashbox_id,
            type="income",
            amount=Decimal("42.50"),
            currency="RUB",
            happened_at=happened,
            description="align",
            booking_id=booking_id,
            payment_id=None,
            source="test",
        )
    )
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    rows = await repo.get_visit_revenue_by_period(
        clinic_id=clinic_id,
        date_from=today,
        date_to=today,
    )
    assert any(r.booking_id == booking_id and r.total_revenue == Decimal("42.50") for r in rows)
    total = await repo.sum_income_revenue_for_crm_lead(
        clinic_id=clinic_id,
        lead_id=lead_id,
        booking_ids=[booking_id],
    )
    assert total == Decimal("42.50")


@pytest.mark.asyncio
async def test_sum_income_revenue_for_crm_lead_by_lead_id_and_bookings(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    lead_id = uuid4()
    happened = datetime.combine(date.today(), datetime.min.time())
    booking_a = await _create_booking_id(db_session, seed_data, date.today())
    booking_b = await _create_booking_id(db_session, seed_data, date.today())
    cashbox_id = await _seed_cashbox_id(db_session, clinic_id)

    db_session.add_all(
        [
            FinancialTransaction(
                clinic_id=clinic_id,
                cashbox_id=cashbox_id,
                type="income",
                amount=Decimal("80.00"),
                currency="RUB",
                happened_at=happened,
                description="via lead",
                booking_id=None,
                payment_id=None,
                lead_id=lead_id,
                source="erp",
            ),
            FinancialTransaction(
                clinic_id=clinic_id,
                cashbox_id=cashbox_id,
                type="income",
                amount=Decimal("70.00"),
                currency="RUB",
                happened_at=happened,
                description="via booking b",
                booking_id=booking_b,
                payment_id=None,
                lead_id=None,
                source="erp",
            ),
            FinancialTransaction(
                clinic_id=clinic_id,
                cashbox_id=cashbox_id,
                type="expense",
                amount=Decimal("999.00"),
                currency="RUB",
                happened_at=happened,
                description="noise",
                booking_id=booking_a,
                payment_id=None,
                lead_id=lead_id,
                source="erp",
            ),
        ]
    )
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    total = await repo.sum_income_revenue_for_crm_lead(
        clinic_id=clinic_id,
        lead_id=lead_id,
        booking_ids=[booking_a, booking_b],
    )
    assert total == Decimal("150.00")


@pytest.mark.asyncio
async def test_get_attribution_revenue_by_period_filters_by_clinic(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    today = date.today() + timedelta(days=(uuid4().int % 120) + 30)
    happened = datetime.combine(today, datetime.min.time())
    cashbox_id = await _seed_cashbox_id(db_session, clinic_id)

    attr = VisitAttribution(
        clinic_id=clinic_id,
        patient_id=None,
        lead_id=None,
        traffic_source_id=uuid4(),
        campaign_id=uuid4(),
        session_id="s1",
        landing_page=None,
        anchor=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        utm_term=None,
        created_at=happened,
    )
    db_session.add(attr)
    await db_session.flush()

    good_tx = FinancialTransaction(
        clinic_id=clinic_id,
        cashbox_id=cashbox_id,
        type="income",
        amount=Decimal("50.00"),
        currency="RUB",
        happened_at=happened,
        description="good",
        booking_id=None,
        payment_id=None,
        lead_id=None,
        visit_attribution_id=attr.id,
        source="booking_completed",
    )
    bad_tx = FinancialTransaction(
        clinic_id=clinic_id,
        cashbox_id=cashbox_id,
        type="expense",
        amount=Decimal("999.00"),
        currency="RUB",
        happened_at=happened,
        description="noise",
        booking_id=None,
        payment_id=None,
        lead_id=None,
        visit_attribution_id=attr.id,
        source="booking_completed",
    )
    db_session.add_all([good_tx, bad_tx])
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    rows = await repo.get_attribution_revenue_by_period(
        clinic_id=clinic_id,
        date_from=today,
        date_to=today,
    )
    target = next(
        (
            r
            for r in rows
            if r.traffic_source_id == attr.traffic_source_id
            and r.campaign_id == attr.campaign_id
        ),
        None,
    )
    assert target is not None
    assert target.clinic_id == clinic_id
    assert target.total_revenue == Decimal("50.00")


@pytest.mark.asyncio
async def test_get_visit_inventory_by_period_basic(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    product_id = uuid4()
    today = date.today()
    happened = datetime.combine(today, datetime.min.time())
    booking_id = await _create_booking_id(db_session, seed_data, today)
    warehouse_id = uuid4()
    db_session.add(
        Warehouse(id=warehouse_id, clinic_id=clinic_id, name="ERP Repo W", is_default=False)
    )
    db_session.add(
        Product(id=product_id, clinic_id=clinic_id, name="ERP Repo P", unit="pcs", is_active=True)
    )
    await db_session.flush()

    tx = InventoryTransaction(
        clinic_id=clinic_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        type="outgoing",
        quantity=Decimal("2.500"),
        happened_at=happened,
        description=None,
        booking_id=booking_id,
    )
    db_session.add(tx)
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    rows = await repo.get_visit_inventory_by_period(
        clinic_id=clinic_id,
        date_from=today,
        date_to=today,
    )
    target = next((r for r in rows if r.product_id == product_id and r.booking_id == booking_id), None)
    assert target is not None
    assert target.total_quantity == Decimal("2.500")


@pytest.mark.asyncio
async def test_get_visit_payroll_by_period_overlapping(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    today = date.today()
    period_start = today - timedelta(days=1)
    period_end = today + timedelta(days=1)
    booking_id = await _create_booking_id(db_session, seed_data, today)

    tx = SalaryTransaction(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        booking_id=booking_id,
        amount=Decimal("200.00"),
        type="accrual",
        period_start=period_start,
        period_end=period_end,
        description=None,
    )
    db_session.add(tx)
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    rows = await repo.get_visit_payroll_by_period(
        clinic_id=clinic_id,
        date_from=today,
        date_to=today,
    )
    target = next((r for r in rows if r.booking_id == booking_id and r.doctor_id == doctor_id), None)
    assert target is not None
    assert target.amount == Decimal("200.00")


@pytest.mark.asyncio
async def test_visit_inventory_daily_sums_to_period_total(db_session: AsyncSession) -> None:
    """Daily grain sums to the same totals per (product, booking) as period aggregate."""
    clinic_id = uuid4()
    product_id = uuid4()
    warehouse_id = uuid4()
    d1 = date.today()
    d2 = d1 + timedelta(days=1)

    db_session.add(
        Clinic(
            id=clinic_id,
            name="Daily inv test",
            prepayment_amount=0,
        )
    )
    db_session.add(
        Warehouse(id=warehouse_id, clinic_id=clinic_id, name="W", is_default=True)
    )
    db_session.add(
        Product(id=product_id, clinic_id=clinic_id, name="P", unit="pcs", is_active=True)
    )
    await db_session.flush()
    db_session.add_all(
        [
            InventoryTransaction(
                clinic_id=clinic_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                type="outgoing",
                quantity=Decimal("1.000"),
                happened_at=datetime.combine(d1, datetime.min.time()),
                booking_id=None,
            ),
            InventoryTransaction(
                clinic_id=clinic_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                type="outgoing",
                quantity=Decimal("2.500"),
                happened_at=datetime.combine(d1, datetime.max.time()),
                booking_id=None,
            ),
            InventoryTransaction(
                clinic_id=clinic_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                type="outgoing",
                quantity=Decimal("4.000"),
                happened_at=datetime.combine(d2, datetime.min.time()),
                booking_id=None,
            ),
        ]
    )
    await db_session.commit()

    repo = ErpReportsRepository(db_session)
    daily = await repo.get_visit_inventory_daily_by_period(
        clinic_id=clinic_id,
        date_from=d1,
        date_to=d2,
    )
    period = await repo.get_visit_inventory_by_period(
        clinic_id=clinic_id,
        date_from=d1,
        date_to=d2,
    )
    sum_daily = sum((d.quantity_day for d in daily), start=Decimal("0"))
    sum_period = sum((p.total_quantity for p in period), start=Decimal("0"))
    assert sum_daily == sum_period == Decimal("7.500")

    agg_day = defaultdict(Decimal)
    for d in daily:
        agg_day[(d.product_id, d.booking_id)] += d.quantity_day
    agg_period = {(p.product_id, p.booking_id): p.total_quantity for p in period}
    assert dict(agg_day) == agg_period

