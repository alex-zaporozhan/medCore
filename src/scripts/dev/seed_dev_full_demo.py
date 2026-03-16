"""
DEV ONLY: Fill DB with a large demo dataset for internal testing.

- Past ~1 month: bookings (completed/cancelled/no_show/confirmed), payments, financial_transactions,
  so that analytics, reports, visits, and ERP look populated.
- Cashboxes and discounts for the clinic.
- Future ~2 weeks: bookings (pending/confirmed) for testing calendar and lists.

Requires: seed_demo_data already run (clinic, Demo Dr.*, +7000000* patients, demo services).

Run:
  poetry run python -m src.scripts.dev.seed_dev_full_demo
  docker compose run --rm backend python -m src.scripts.dev.seed_dev_full_demo
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.booking import Booking
from src.domain.entities.payment import Payment
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.discount import Discount
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.patient import Patient
from src.domain.entities.service import Service
from src.domain.entities.conversation import Conversation
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.owner_integration_settings import OwnerIntegrationSettings

# --- Config ---
PAST_DAYS = 30
FUTURE_DAYS = 45  # ~1.5 months ahead for calendar/testing
SLOTS_PER_DAY = [time(9, 0), time(10, 0), time(11, 0), time(14, 0), time(16, 0)]
# Status mix for past: completed -> payment+fin_tx; others no payment
PAST_STATUS_WEIGHTS = ("completed", "completed", "completed", "cancelled", "no_show", "confirmed")
PROVIDER = "yookassa"


async def seed_dev_full_demo() -> None:
    async with AsyncSessionLocal() as session:
        # 1) Clinic + doctors, patients, services (demo only)
        res = await session.execute(
            select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1)
        )
        clinic = res.scalar_one_or_none()
        if not clinic:
            print("Ошибка: нет клиники. Сначала: poetry run python -m src.scripts.seed_demo_data")
            return

        res = await session.execute(
            select(Doctor).where(
                Doctor.clinic_id == clinic.id,
                Doctor.deleted_at.is_(None),
            ).order_by(Doctor.full_name)
        )
        doctors = list(res.scalars().all())
        res = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.deleted_at.is_(None),
            ).order_by(Patient.phone)
        )
        patients = list(res.scalars().all())
        res = await session.execute(
            select(Service).where(
                Service.clinic_id == clinic.id,
                Service.deleted_at.is_(None),
            ).order_by(Service.name)
        )
        services = list(res.scalars().all())

        if not doctors or not patients or not services:
            print("Ошибка: нужны врачи, пациенты и услуги. Запустите seed_demo_data.")
            return

        clinic_id = clinic.id
        today = date.today()
        past_start = today - timedelta(days=PAST_DAYS)
        future_end = today + timedelta(days=FUTURE_DAYS)

        # 2) Cashboxes (if none)
        res = await session.execute(
            select(Cashbox).where(
                Cashbox.clinic_id == clinic_id,
            ).limit(1)
        )
        if res.scalar_one_or_none() is None:
            session.add(
                Cashbox(
                    clinic_id=clinic_id,
                    name="Касса (наличные)",
                    type="cash",
                    currency="RUB",
                    is_default=True,
                    is_active=True,
                )
            )
            session.add(
                Cashbox(
                    clinic_id=clinic_id,
                    name="Банковские переводы",
                    type="card",
                    currency="RUB",
                    is_default=False,
                    is_active=True,
                )
            )
            await session.flush()

        res = await session.execute(
            select(Cashbox).where(Cashbox.clinic_id == clinic_id).order_by(Cashbox.name)
        )
        cashboxes = list(res.scalars().all())
        default_cashbox = next((c for c in cashboxes if c.is_default), cashboxes[0] if cashboxes else None)

        # 3) Discounts (dev demo)
        res = await session.execute(
            select(Discount).where(Discount.clinic_id == clinic_id).limit(1)
        )
        if res.scalar_one_or_none() is None and services:
            session.add(
                Discount(
                    clinic_id=clinic_id,
                    name="Первый визит -10%",
                    discount_type="first_visit",
                    percent_off=Decimal("10.00"),
                    is_active=True,
                )
            )
            session.add(
                Discount(
                    clinic_id=clinic_id,
                    name="Чистка зубов -15%",
                    discount_type="service",
                    service_id=next((s.id for s in services if "Чистка" in s.name), services[0].id),
                    percent_off=Decimal("15.00"),
                    is_active=True,
                )
            )
            session.add(
                Discount(
                    clinic_id=clinic_id,
                    name="Март -5%",
                    discount_type="period",
                    valid_from=today.replace(day=1) - timedelta(days=30),
                    valid_until=today + timedelta(days=60),
                    percent_off=Decimal("5.00"),
                    is_active=True,
                )
            )
            await session.flush()

        # 4) Past bookings + payments + financial_transactions
        n_docs = len(doctors)
        n_pat = len(patients)
        n_svc = len(services)
        used_slots: set[tuple[uuid.UUID, date, time]] = set()

        def _norm_time(t: time) -> time:
            return time(t.hour, t.minute, t.second)

        # Load already existing slots in range so we don't duplicate (idempotent run)
        existing = await session.execute(
            select(Booking.doctor_id, Booking.appointment_date, Booking.appointment_time).where(
                Booking.clinic_id == clinic_id,
                Booking.appointment_date >= past_start,
                Booking.appointment_date <= future_end,
                Booking.deleted_at.is_(None),
            )
        )
        for row in existing.all():
            doc_id, app_date, app_time = row[0], row[1], row[2]
            used_slots.add((doc_id, app_date, _norm_time(app_time)))

        def next_slot(d: date, doc_idx: int, slot_idx: int) -> time:
            return SLOTS_PER_DAY[slot_idx % len(SLOTS_PER_DAY)]

        past_bookings: list[Booking] = []
        day = past_start
        while day < today:
            for doc_idx, doc in enumerate(doctors):
                for slot_idx in range(3):  # 3 slots per doctor per day
                    t = next_slot(day, doc_idx, slot_idx)
                    slot_key = (doc.id, day, _norm_time(t))
                    if slot_key in used_slots:
                        continue
                    used_slots.add(slot_key)
                    patient = patients[(hash((day, doc_idx, slot_idx)) % n_pat + n_pat) % n_pat]
                    service = services[(hash((day, doc_idx, slot_idx + 1)) % n_svc + n_svc) % n_svc]
                    status = PAST_STATUS_WEIGHTS[(hash((day, doc_idx, slot_idx)) % len(PAST_STATUS_WEIGHTS))]
                    b = Booking(
                        clinic_id=clinic_id,
                        patient_id=patient.id,
                        doctor_id=doc.id,
                        service_id=service.id,
                        appointment_date=day,
                        appointment_time=t,
                        status=status,
                        prepayment_amount=Decimal("0.00"),
                        notes="[dev demo]",
                        erp_processed=(status == "completed"),
                    )
                    session.add(b)
                    await session.flush()
                    past_bookings.append((b, service.price, status))
            day += timedelta(days=1)

        # Payments for completed past bookings; then financial_transactions
        for (b, amount, status) in past_bookings:
            if status != "completed":
                continue
            pay = Payment(
                clinic_id=clinic_id,
                booking_id=b.id,
                provider=PROVIDER,
                provider_payment_id=f"dev_demo_{b.id}_{uuid.uuid4().hex[:8]}",
                amount=amount,
                currency="RUB",
                status="succeeded",
            )
            session.add(pay)
            await session.flush()
            b.payment_id = pay.id
            if default_cashbox:
                session.add(
                    FinancialTransaction(
                        clinic_id=clinic_id,
                        cashbox_id=default_cashbox.id,
                        type="income",
                        amount=amount,
                        currency="RUB",
                        happened_at=datetime.combine(b.appointment_date, b.appointment_time),
                        description=f"Оплата визита (dev demo) #{b.id}",
                        booking_id=b.id,
                        payment_id=pay.id,
                        source="booking_completed",
                    )
                )
        await session.flush()

        # 5) Future bookings (2 weeks)
        day = today
        while day <= future_end:
            for doc_idx, doc in enumerate(doctors):
                for slot_idx in range(2):
                    t = next_slot(day, doc_idx, slot_idx)
                    slot_key = (doc.id, day, _norm_time(t))
                    if slot_key in used_slots:
                        continue
                    used_slots.add(slot_key)
                    patient = patients[(hash((day, doc_idx, slot_idx + 100)) % n_pat + n_pat) % n_pat]
                    service = services[(hash((day, doc_idx, slot_idx + 101)) % n_svc + n_svc) % n_svc]
                    status = "confirmed" if (hash((day, doc_idx)) % 2 == 0) else "pending"
                    session.add(
                        Booking(
                            clinic_id=clinic_id,
                            patient_id=patient.id,
                            doctor_id=doc.id,
                            service_id=service.id,
                            appointment_date=day,
                            appointment_time=t,
                            status=status,
                            prepayment_amount=Decimal("0.00"),
                            notes="[dev demo]",
                            erp_processed=False,
                        )
                    )
            day += timedelta(days=1)

        # 6) Owner integration settings (optional: so Telegram briefs can use DB)
        res_owner = await session.execute(
            select(OwnerIntegrationSettings).where(OwnerIntegrationSettings.clinic_id == clinic_id).limit(1)
        )
        if res_owner.scalar_one_or_none() is None:
            session.add(
                OwnerIntegrationSettings(
                    clinic_id=clinic_id,
                    owner_morning_brief_enabled=False,
                    owner_telegram_chat_id=None,
                    morning_brief_send_at_utc="09:00",
                    ai_supervisor_enabled=False,
                    ai_supervisor_send_at_utc="20:00",
                    ai_supervisor_recipient_chat_ids=None,
                )
            )
            await session.flush()

        # 7) Conversations + chat messages for a subset of patients (so chats aren't empty)
        from src.domain.entities.admin_user import AdminUser
        res_admin = await session.execute(
            select(AdminUser).where(AdminUser.clinic_id == clinic_id, AdminUser.deleted_at.is_(None)).limit(1)
        )
        admin_user = res_admin.scalar_one_or_none()
        admin_id = admin_user.id if admin_user else None
        sample_patients = patients[: min(7, len(patients))]
        demo_messages = [
            "Здравствуйте! Хотел бы записаться на чистку.",
            "Добрый день! Конечно, есть окно в четверг в 10:00.",
            "Подойдёт, записывайте пожалуйста.",
            "Записал. Ждём вас в четверг в 10:00.",
            "Спасибо! Напомните пожалуйста за день.",
            "Напоминание придёт автоматически за 24 часа.",
        ]
        for i, patient in enumerate(sample_patients):
            res_conv = await session.execute(
                select(Conversation).where(
                    Conversation.clinic_id == clinic_id,
                    Conversation.patient_id == patient.id,
                    Conversation.deleted_at.is_(None),
                ).limit(1)
            )
            if res_conv.scalar_one_or_none() is not None:
                continue
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient.id,
                assigned_admin_id=admin_id,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            session.add(conv)
            await session.flush()
            last_at = datetime.now() - timedelta(days=min(i + 2, 14))
            for j, body in enumerate(demo_messages[: 4 + (i % 3)]):
                sender = "patient" if j % 2 == 0 else "admin"
                msg = ChatMessage(
                    clinic_id=clinic_id,
                    conversation_id=conv.id,
                    patient_id=patient.id,
                    admin_id=admin_id if sender == "admin" else None,
                    sender_type=sender,
                    message_type="text",
                    body=body,
                    sticker_key=None,
                    read_by_admin_at=last_at if sender == "patient" else None,
                    read_by_patient_at=last_at if sender == "admin" else None,
                )
                session.add(msg)
                await session.flush()
                last_at = last_at + timedelta(minutes=5 + (j % 10))
            conv.last_message_at = last_at
            conv.last_message_sender_type = "admin"
            await session.flush()

        await session.commit()
        print(
            f"DEV demo: cashboxes={len(cashboxes)}, discounts, past ~{PAST_DAYS}d, future ~{FUTURE_DAYS}d, "
            f"chats for {len(sample_patients)} patients. Done."
        )


def main() -> None:
    asyncio.run(seed_dev_full_demo())


if __name__ == "__main__":
    main()
