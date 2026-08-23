from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy import delete, select, update

from src.application.dto.booking_dto import BookingCreateAdmin
from src.application.events.domain_event import DomainEvent
from src.application.events.erp_event_handlers import handle_erp_on_booking_completed
from src.application.events.standard_events import BOOKING_COMPLETED
from src.application.services.booking_service import BookingService
from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.entities.service import Service
from src.domain.entities.service_consumable import ServiceConsumable
from src.domain.entities.product import Product
from src.domain.entities.warehouse import Warehouse
from src.infrastructure.database import base as db_base
from src.domain.entities.payment import Payment
from src.application.services.wallet_service import WalletService, EarnPointsInput, SpendPointsInput
from tests.booking_slot import unique_booking_slot, unique_clock_time


def _admin_booking_create(
  clinic_id: UUID,
  patient_id: UUID,
  doctor_id: UUID,
  service_id: UUID,
  appointment_date: date,
  appointment_time: time,
  *,
  status: str = "confirmed",
  prepayment_amount: Decimal | None = Decimal("0.00"),
  notes: str | None = None,
) -> BookingCreateAdmin:
  return BookingCreateAdmin(
    clinic_id=clinic_id,
    patient_id=patient_id,
    doctor_id=doctor_id,
    service_id=service_id,
    appointment_date=appointment_date,
    appointment_time=appointment_time,
    status=status,
    prepayment_amount=prepayment_amount,
    notes=notes,
  )


@pytest.mark.asyncio
async def test_booking_completed_triggers_erp_and_creates_records(init_db, seed_data):
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, daily_time = unique_booking_slot(seed_data["date"], hour=10)

  async with db_base.AsyncSessionLocal() as session:
    wres = await session.execute(
      select(Warehouse).where(
        Warehouse.clinic_id == clinic_id,
        Warehouse.is_default.is_(True),
      ).limit(1)
    )
    warehouse = wres.scalar_one()

    product = Product(
      clinic_id=clinic_id,
      sku="MAT-1",
      name="Test Material",
      unit="pcs",
      is_active=True,
    )
    session.add(product)
    await session.flush()

    from src.domain.entities.inventory_transaction import InventoryTransaction

    incoming = InventoryTransaction(
      clinic_id=clinic_id,
      warehouse_id=warehouse.id,
      product_id=product.id,
      type="incoming",
      quantity=Decimal("5.000"),
      happened_at=utc_now(),
      description="Seed stock",
      booking_id=None,
    )
    session.add(incoming)

    service = await session.get(Service, service_id)
    assert service is not None
    service.price = Decimal("1000.00")
    session.add(service)

    tech = ServiceConsumable(
      clinic_id=clinic_id,
      service_id=service_id,
      product_id=product.id,
      quantity_per_service=Decimal("2.000"),
      unit="pcs",
    )
    session.add(tech)

    await session.commit()

  async with db_base.AsyncSessionLocal() as session:
    booking_service = BookingService(session)
    booking_read = await booking_service.create_admin_booking(
      clinic_id=clinic_id,
      data=_admin_booking_create(
        clinic_id,
        patient_id,
        doctor_id,
        service_id,
        day,
        daily_time,
      ),
    )

    booking = await session.get(Booking, booking_read.id)
    assert booking is not None
    assert booking.erp_processed is False

    await session.commit()

    event = DomainEvent(
      name=BOOKING_COMPLETED,
      payload={
        "booking_id": str(booking.id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "status": "completed",
        "appointment_date": day.isoformat(),
        "appointment_time": daily_time.isoformat(),
      },
    )

    await handle_erp_on_booking_completed(event)

  async with db_base.AsyncSessionLocal() as session:
    updated = await session.get(Booking, booking_read.id)
    assert updated is not None
    assert updated.erp_processed is True
    assert updated.erp_error_code is None

    fin_res = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.booking_id == updated.id)
    )
    fin_txs = list(fin_res.scalars().all())
    assert len(fin_txs) == 1
    assert fin_txs[0].amount == Decimal("1000.00")
    assert fin_txs[0].type == "income"

    sal_res = await session.execute(
      select(SalaryTransaction).where(SalaryTransaction.booking_id == updated.id)
    )
    sal_txs = list(sal_res.scalars().all())
    assert len(sal_txs) == 1
    assert sal_txs[0].amount == Decimal("200.00")

    from src.domain.entities.inventory_transaction import InventoryTransaction

    inv_res = await session.execute(
      select(InventoryTransaction).where(InventoryTransaction.booking_id == updated.id)
    )
    inv_txs = list(inv_res.scalars().all())
    assert len(inv_txs) == 1
    assert inv_txs[0].type == "outgoing"
    assert inv_txs[0].quantity == Decimal("2.000")


@pytest.mark.asyncio
async def test_booking_completed_with_full_wallet_payment_results_in_zero_income(
  init_db,
  seed_data,
):
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, daily_time = unique_booking_slot(seed_data["date"], hour=11)

  async with db_base.AsyncSessionLocal() as session:
    await session.execute(
      delete(ServiceConsumable).where(ServiceConsumable.service_id == service_id)
    )
    service = await session.get(Service, service_id)
    assert service is not None
    service.price = Decimal("500.00")
    session.add(service)

    await session.commit()

  async with db_base.AsyncSessionLocal() as session:
    booking_service = BookingService(session)
    booking_read = await booking_service.create_admin_booking(
      clinic_id=clinic_id,
      data=_admin_booking_create(
        clinic_id,
        patient_id,
        doctor_id,
        service_id,
        day,
        daily_time,
      ),
    )

    booking = await session.get(Booking, booking_read.id)
    assert booking is not None

    wallet_service = WalletService(session)
    now = utc_now()
    await wallet_service.earn_points(
      EarnPointsInput(
        clinic_id=clinic_id,
        patient_id=patient_id,
        amount=Decimal("500.00"),
        happened_at=now,
        booking_id=None,
        subscription_id=None,
        description="seed wallet for full points payment",
      )
    )
    await wallet_service.spend_points(
      SpendPointsInput(
        clinic_id=clinic_id,
        patient_id=patient_id,
        amount=Decimal("500.00"),
        happened_at=now,
        booking_id=booking.id,
        description="pay visit fully by points",
      )
    )
    await session.commit()

    event = DomainEvent(
      name=BOOKING_COMPLETED,
      payload={
        "booking_id": str(booking.id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "status": "completed",
        "appointment_date": day.isoformat(),
        "appointment_time": daily_time.isoformat(),
      },
    )

    await handle_erp_on_booking_completed(event)

  async with db_base.AsyncSessionLocal() as session:
    updated = await session.get(Booking, booking_read.id)
    assert updated is not None
    assert updated.erp_processed is True

    fin_res = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.booking_id == updated.id)
    )
    fin_txs = list(fin_res.scalars().all())
    assert len(fin_txs) == 1
    # Визит полностью оплачен баллами — денежный приход должен быть ноль.
    assert fin_txs[0].amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_booking_completed_with_partial_wallet_and_payment(
  init_db,
  seed_data,
):
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, daily_time = unique_booking_slot(seed_data["date"], hour=12)

  async with db_base.AsyncSessionLocal() as session:
    await session.execute(
      delete(ServiceConsumable).where(ServiceConsumable.service_id == service_id)
    )
    service = await session.get(Service, service_id)
    assert service is not None
    service.price = Decimal("1000.00")
    session.add(service)

    await session.commit()

  async with db_base.AsyncSessionLocal() as session:
    booking_service = BookingService(session)
    booking_read = await booking_service.create_admin_booking(
      clinic_id=clinic_id,
      data=_admin_booking_create(
        clinic_id,
        patient_id,
        doctor_id,
        service_id,
        day,
        daily_time,
      ),
    )

    booking = await session.get(Booking, booking_read.id)
    assert booking is not None

    wallet_service = WalletService(session)
    now = utc_now()
    await wallet_service.earn_points(
      EarnPointsInput(
        clinic_id=clinic_id,
        patient_id=patient_id,
        amount=Decimal("600.00"),
        happened_at=now,
        booking_id=None,
        subscription_id=None,
        description="seed wallet for partial points payment",
      )
    )
    await wallet_service.spend_points(
      SpendPointsInput(
        clinic_id=clinic_id,
        patient_id=patient_id,
        amount=Decimal("600.00"),
        happened_at=now,
        booking_id=booking.id,
        description="pay part of visit by points",
      )
    )

    payment = Payment(
      clinic_id=clinic_id,
      booking_id=booking.id,
      provider="test",
      provider_payment_id="pay-1",
      amount=Decimal("400.00"),
      currency="RUB",
      status="succeeded",
      provider_metadata=None,
    )
    session.add(payment)
    await session.flush()
    booking.payment_id = payment.id
    session.add(booking)
    await session.commit()

    event = DomainEvent(
      name=BOOKING_COMPLETED,
      payload={
        "booking_id": str(booking.id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "status": "completed",
        "appointment_date": day.isoformat(),
        "appointment_time": daily_time.isoformat(),
      },
    )

    await handle_erp_on_booking_completed(event)

  async with db_base.AsyncSessionLocal() as session:
    updated = await session.get(Booking, booking_read.id)
    assert updated is not None

    fin_res = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.booking_id == updated.id)
    )
    fin_txs = list(fin_res.scalars().all())
    assert len(fin_txs) == 1
    # 600 оплачено баллами, 400 деньгами — ERP должен видеть только денежную часть.
    assert fin_txs[0].amount == Decimal("400.00")


@pytest.mark.asyncio
async def test_erp_handles_many_bookings_sequentially(init_db, seed_data):
  """ERP-узел устойчиво обрабатывает серию завершений визитов без подвисаний."""
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, _ = unique_booking_slot(seed_data["date"], hour=16)

  async with db_base.AsyncSessionLocal() as session:
    await session.execute(
      delete(ServiceConsumable).where(ServiceConsumable.service_id == service_id)
    )
    service = await session.get(Service, service_id)
    assert service is not None
    service.price = Decimal("700.00")
    session.add(service)

    await session.commit()

  # Уникальные слоты (doctor_id + day + time): минуты 17:00–17:29 не пересекаются с другими тестами на тот же день.
  total_bookings = 30
  booking_ids: list[str] = []

  async with db_base.AsyncSessionLocal() as session:
    booking_service = BookingService(session)
    for _ in range(total_bookings):
      daily_time = unique_clock_time(hour=17)
      booking_read = await booking_service.create_admin_booking(
        clinic_id=clinic_id,
        data=_admin_booking_create(
          clinic_id,
          patient_id,
          doctor_id,
          service_id,
          day,
          daily_time,
        ),
      )
      booking_ids.append(str(booking_read.id))

    await session.commit()

  # Последовательно отправляем события BOOKING_COMPLETED.
  for bid in booking_ids:
    event = DomainEvent(
      name=BOOKING_COMPLETED,
      payload={
        "booking_id": bid,
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "status": "completed",
        "appointment_date": day.isoformat(),
        "appointment_time": daily_time.isoformat(),
      },
    )
    await handle_erp_on_booking_completed(event)

  # Проверяем, что все визиты обработаны и нет подвисших ERP-состояний.
  async with db_base.AsyncSessionLocal() as session:
    processed_count = 0
    for bid in booking_ids:
      booking = await session.get(Booking, UUID(bid))
      assert booking is not None
      assert booking.erp_error_code is None
      assert booking.erp_processed is True
      processed_count += 1

    assert processed_count == total_bookings

    fin_res = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.clinic_id == clinic_id)
    )
    fin_txs = list(fin_res.scalars().all())
    # Ожидаем по одному приходу на каждый визит.
    assert len(fin_txs) >= total_bookings


@pytest.mark.asyncio
async def test_erp_configuration_error_sets_error_code_on_booking(init_db, seed_data):
  """При ошибке конфигурации ERP помечает визит кодом ошибки и не создаёт приход."""
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, slot_time = unique_booking_slot(seed_data["date"], hour=17)

  # Убираем расходники по услуге, иначе ERP упадёт по складу раньше, чем по кассе.
  async with db_base.AsyncSessionLocal() as session:
    await session.execute(
      delete(ServiceConsumable).where(ServiceConsumable.service_id == service_id)
    )
    await session.commit()

  default_cashbox_ids: list[UUID] = []
  try:
    # Session-scoped seed: другие тесты могли оставить default-кассы — снимаем флаг, иначе не сработает missing_cashbox.
    async with db_base.AsyncSessionLocal() as session:
      default_ids_res = await session.execute(
        select(Cashbox.id).where(
          Cashbox.clinic_id == clinic_id,
          Cashbox.is_default.is_(True),
        )
      )
      default_cashbox_ids = list(default_ids_res.scalars().all())
      await session.execute(
        update(Cashbox).where(Cashbox.clinic_id == clinic_id).values(is_default=False)
      )
      await session.commit()

    # Не создаём кассу намеренно, чтобы спровоцировать missing_cashbox.
    async with db_base.AsyncSessionLocal() as session:
      booking_service = BookingService(session)
      booking_read = await booking_service.create_admin_booking(
        clinic_id=clinic_id,
        data=_admin_booking_create(
          clinic_id,
          patient_id,
          doctor_id,
          service_id,
          day,
          slot_time,
        ),
      )
      await session.commit()

    event = DomainEvent(
      name=BOOKING_COMPLETED,
      payload={
        "booking_id": str(booking_read.id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "status": "completed",
        "appointment_date": day.isoformat(),
        "appointment_time": slot_time.isoformat(),
      },
    )

    await handle_erp_on_booking_completed(event)

    async with db_base.AsyncSessionLocal() as session:
      updated = await session.get(Booking, booking_read.id)
      assert updated is not None
      # ERP-узел не должен помечать визит как обработанный.
      assert updated.erp_processed is False
      # Код ошибки конфигурации должен быть выставлен.
      assert updated.erp_error_code == "missing_cashbox"

      fin_res = await session.execute(
        select(FinancialTransaction).where(FinancialTransaction.booking_id == updated.id)
      )
      fin_txs = list(fin_res.scalars().all())
      # При конфигурационной ошибке приход не создаётся.
      assert len(fin_txs) == 0
  finally:
    # Restore original default cashbox state so later tests keep ERP prerequisites.
    async with db_base.AsyncSessionLocal() as session:
      await session.execute(
        update(Cashbox).where(Cashbox.clinic_id == clinic_id).values(is_default=False)
      )
      if default_cashbox_ids:
        await session.execute(
          update(Cashbox).where(Cashbox.id.in_(default_cashbox_ids)).values(is_default=True)
        )
      await session.commit()


@pytest.mark.asyncio
async def test_erp_fatal_error_rolls_back_no_stale_state(init_db, seed_data):
  """При фатальной ошибке внутри ERP транзакция откатывается, визит не в подвисшем состоянии."""
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]
  service_id = seed_data["service_id"]
  patient_id = seed_data["patient_id"]
  day, slot_time = unique_booking_slot(seed_data["date"], hour=14)

  # seed_data provides default cashbox, warehouse, and payroll policy; no extra ERP rows needed here.

  async with db_base.AsyncSessionLocal() as session:
    booking_service = BookingService(session)
    booking_read = await booking_service.create_admin_booking(
      clinic_id=clinic_id,
      data=_admin_booking_create(
        clinic_id,
        patient_id,
        doctor_id,
        service_id,
        day,
        slot_time,
      ),
    )
    await session.commit()

  booking_id = str(booking_read.id)
  event = DomainEvent(
    name=BOOKING_COMPLETED,
    payload={
      "booking_id": booking_id,
      "clinic_id": str(clinic_id),
      "patient_id": str(patient_id),
      "doctor_id": str(doctor_id),
      "service_id": str(service_id),
      "status": "completed",
      "appointment_date": day.isoformat(),
      "appointment_time": slot_time.isoformat(),
    },
  )

  with patch(
    "src.application.events.erp_event_handlers.BookingErpService.process_booking_completed",
    new_callable=AsyncMock,
    side_effect=Exception("simulated DB failure"),
  ):
    await handle_erp_on_booking_completed(event)

  async with db_base.AsyncSessionLocal() as session:
    booking = await session.get(Booking, UUID(booking_id))
    assert booking is not None
    assert booking.erp_processed is False
    assert booking.erp_error_code is None

    fin_res = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.booking_id == booking.id)
    )
    fin_txs = list(fin_res.scalars().all())
    assert len(fin_txs) == 0

