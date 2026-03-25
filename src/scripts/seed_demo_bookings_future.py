"""Создать демо-записи только в будущем (через 3–6 дней) для проверки модалки и отмены.

Использует только демо-пациентов (телефоны +70000000001 … +70000000010).
Даты: сегодня+3, сегодня+4, сегодня+5, сегодня+6 — чтобы в расписании были
«окна в будущее» для теста переноса и отмены записи.

Запуск после seed_demo_data:
  poetry run python -m src.scripts.seed_demo_bookings_future

Или в Docker:
  docker compose run --rm api python -m src.scripts.seed_demo_bookings_future
"""

import asyncio
import random
from datetime import date, time, timedelta

from sqlalchemy import select

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.patient import Patient
from src.domain.entities.service import Service

# Демо-пациенты: телефоны +70000000001 … +70000000010
DEMO_PHONE_PREFIX = "+7000000000"

SLOT_STARTS = [
    time(9, 0), time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30),
    time(12, 0), time(12, 30), time(13, 0), time(13, 30), time(14, 0), time(14, 30),
    time(15, 0), time(15, 30), time(16, 0), time(16, 30), time(17, 0), time(17, 30),
]

# Статусы для будущих записей — только активные, чтобы можно было тестировать отмену/перенос
FUTURE_STATUSES = ["pending", "pending", "confirmed", "confirmed"]
FILL_RATIO = 0.5


async def seed_future_bookings() -> None:
    async with AsyncSessionLocal() as session:
        clinic_result = await session.execute(
            select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        if not clinic:
            print("Клиника не найдена. Сначала: poetry run python -m src.scripts.seed_demo_data")
            return

        doctors_result = await session.execute(
            select(Doctor).where(
                Doctor.clinic_id == clinic.id,
                Doctor.deleted_at.is_(None),
            )
        )
        doctors = list(doctors_result.scalars().all())
        if not doctors:
            print("Врачи не найдены. Сначала выполните seed_demo_data.")
            return

        # Только демо-пациенты
        patients_result = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.phone.like(f"{DEMO_PHONE_PREFIX}%"),
                Patient.deleted_at.is_(None),
            )
        )
        patients = list(patients_result.scalars().all())
        if not patients:
            print("Демо-пациенты не найдены (телефоны +70000000001…10). Выполните seed_demo_data.")
            return

        services_result = await session.execute(
            select(Service).where(
                Service.clinic_id == clinic.id,
                Service.deleted_at.is_(None),
            )
        )
        services = list(services_result.scalars().all())
        if not services:
            print("Услуги не найдены. Сначала выполните seed_demo_data.")
            return

        today = date.today()
        future_dates = [
            today + timedelta(days=3),
            today + timedelta(days=4),
            today + timedelta(days=5),
            today + timedelta(days=6),
        ]

        # Рабочие часы на все дни недели (0=пн … 6=вс), чтобы слоты были доступны в любой день
        for doc in doctors:
            for weekday in range(7):
                exists = await session.execute(
                    select(DoctorWorkingHours).where(
                        DoctorWorkingHours.doctor_id == doc.id,
                        DoctorWorkingHours.weekday == weekday,
                    ).limit(1)
                )
                if exists.scalar_one_or_none() is None:
                    session.add(
                        DoctorWorkingHours(
                            doctor_id=doc.id,
                            weekday=weekday,
                            start_time=time(9, 0),
                            end_time=time(18, 0),
                        )
                    )
        await session.flush()

        existing = await session.execute(
            select(
                Booking.doctor_id,
                Booking.appointment_date,
                Booking.appointment_time,
            ).where(
                Booking.clinic_id == clinic.id,
                Booking.deleted_at.is_(None),
            )
        )
        occupied = {(r[0], r[1], r[2]) for r in existing.all()}

        added = 0
        for doc in doctors:
            for day in future_dates:
                for slot_time in SLOT_STARTS:
                    if (doc.id, day, slot_time) in occupied:
                        continue
                    if random.random() > FILL_RATIO:
                        continue
                    patient = random.choice(patients)
                    svc = random.choice(services)
                    status = random.choice(FUTURE_STATUSES)
                    session.add(
                        Booking(
                            clinic_id=clinic.id,
                            patient_id=patient.id,
                            doctor_id=doc.id,
                            service_id=svc.id,
                            appointment_date=day,
                            appointment_time=slot_time,
                            status=status,
                            prepayment_amount=0,
                        )
                    )
                    occupied.add((doc.id, day, slot_time))
                    added += 1

        await session.commit()
        print(f"Добавлено записей в будущее (через 3–6 дней): {added}.")
        print(f"Даты: {[d.isoformat() for d in future_dates]}. Откройте расписание на эти дни для проверки модалки и отмены.")

        try:
            from src.infrastructure.database.redis_client import get_redis
            redis = await get_redis()
            keys = []
            async for k in redis.scan_iter("schedule:*"):
                keys.append(k)
            if keys:
                await redis.delete(*keys)
                print("Кэш расписания сброшен.")
        except Exception as e:
            print(f"Redis не сброшен (необязательно): {e}")


def main() -> None:
    asyncio.run(seed_future_bookings())


if __name__ == "__main__":
    main()
