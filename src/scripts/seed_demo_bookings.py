"""Seed many demo bookings for all doctors — наглядно для клиентов.

Заполняет записи на несколько дней (сегодня, завтра, послезавтра и ещё 2 дня),
у всех врачей клиники. Оставляет часть слотов пустыми (~40% свободно).

Запуск после seed_demo_data:
  poetry run python -m src.scripts.seed_demo_bookings
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
from src.domain.entities.payment import Payment  # для регистрации таблицы в metadata (FK bookings.payment_id)
from src.domain.entities.service import Service

# Слоты по 30 минут с 09:00 до 18:00 (последний старт 17:30)
SLOT_STARTS = [
    time(9, 0), time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30),
    time(12, 0), time(12, 30), time(13, 0), time(13, 30), time(14, 0), time(14, 30),
    time(15, 0), time(15, 30), time(16, 0), time(16, 30), time(17, 0), time(17, 30),
]

STATUSES = ["pending", "pending", "confirmed", "confirmed", "completed", "completed", "completed"]

# Доля слотов, которые заполняем (остальные остаются свободными). 0.55 = ~55% занято
FILL_RATIO = 0.55


async def seed_bookings() -> None:
    async with AsyncSessionLocal() as session:
        clinic_result = await session.execute(
            select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        if not clinic:
            print("Клиника не найдена. Сначала выполните: poetry run python -m src.scripts.seed_demo_data")
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

        patients_result = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.deleted_at.is_(None),
            )
        )
        patients = list(patients_result.scalars().all())
        if not patients:
            print("Пациенты не найдены. Сначала выполните seed_demo_data.")
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

        # Для демо: добавить рабочие часы в субботу (и воскресенье), чтобы записи отображались в любой день
        wh_saturday = await session.execute(
            select(DoctorWorkingHours.doctor_id).where(
                DoctorWorkingHours.weekday == 5,
            ).distinct()
        )
        have_sat = {r[0] for r in wh_saturday.all()}
        for doc in doctors:
            if doc.id not in have_sat:
                session.add(
                    DoctorWorkingHours(
                        doctor_id=doc.id,
                        weekday=5,
                        start_time=time(9, 0),
                        end_time=time(18, 0),
                    )
                )
        await session.flush()

        today = date.today()
        dates = [
            today - timedelta(days=1),
            today,
            today + timedelta(days=1),
            today + timedelta(days=2),
            today + timedelta(days=3),
            today + timedelta(days=4),
        ]

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
        for d in doctors:
            for day in dates:
                for slot_time in SLOT_STARTS:
                    if (d.id, day, slot_time) in occupied:
                        continue
                    if random.random() > FILL_RATIO:
                        continue
                    patient = random.choice(patients)
                    service = random.choice(services)
                    status = random.choice(STATUSES)
                    session.add(
                        Booking(
                            clinic_id=clinic.id,
                            patient_id=patient.id,
                            doctor_id=d.id,
                            service_id=service.id,
                            appointment_date=day,
                            appointment_time=slot_time,
                            status=status,
                            prepayment_amount=0,
                        )
                    )
                    occupied.add((d.id, day, slot_time))
                    added += 1

        await session.commit()
        print(f"Added bookings: {added}. Some slots left empty for demo.")

        # Сброс кэша расписания в Redis, чтобы сразу отображались новые записи
        try:
            from src.infrastructure.database.redis_client import get_redis
            redis = await get_redis()
            keys = []
            async for k in redis.scan_iter("schedule:*"):
                keys.append(k)
            if keys:
                await redis.delete(*keys)
                print("Schedule cache cleared.")
        except Exception as e:
            print(f"Redis cache not cleared (optional): {e}")


def main() -> None:
    asyncio.run(seed_bookings())


if __name__ == "__main__":
    main()
