"""Seed database with demo data for local testing (legacy single-clinic demo).

For the first (or only) clinic creates or supplements:
- one clinic (if none),
- 4 doctors with working hours (Mon–Fri 09:00–18:00),
- 10 demo patients (phones +70000000001 … +70000000010),
- 10 demo services.

For buyer-facing presentation (3 clinics, realistic names): prefer
`poetry run python -m src.scripts.seed_presentation_showcase`.

Run: poetry run python -m src.scripts.seed_demo_data
Or:  docker compose run --rm api python -m src.scripts.seed_demo_data
"""

import asyncio
import uuid
from datetime import date, time

from sqlalchemy import select, func

from passlib.hash import pbkdf2_sha256

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.service import Service
from src.domain.entities.doctor import Doctor
from src.domain.entities.patient import Patient
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.service_doctor import ServiceDoctor

DEMO_DOCTORS = [
    {"full_name": "Demo Dr. Иванов", "specialization": "Терапевт", "experience_years": 5},
    {"full_name": "Demo Dr. Петрова", "specialization": "Хирург", "experience_years": 8},
    {"full_name": "Demo Dr. Сидорова", "specialization": "Ортодонт", "experience_years": 6},
    {"full_name": "Demo Dr. Козлов", "specialization": "Гигиенист", "experience_years": 4},
]

DEMO_PATIENTS = [
    ("+70000000001", "Демо Пациент 1", "demo1@example.test", date(1990, 1, 1)),
    ("+70000000002", "Демо Пациент 2", "demo2@example.test", date(1985, 5, 15)),
    ("+70000000003", "Демо Пациент 3", "demo3@example.test", date(1995, 7, 20)),
    ("+70000000004", "Демо Пациент 4", "demo4@example.test", date(1988, 3, 10)),
    ("+70000000005", "Демо Пациент 5", "demo5@example.test", date(1992, 11, 22)),
    ("+70000000006", "Демо Пациент 6", "demo6@example.test", date(1980, 7, 5)),
    ("+70000000007", "Демо Пациент 7", "demo7@example.test", date(1998, 2, 14)),
    ("+70000000008", "Демо Пациент 8", "demo8@example.test", date(1982, 9, 30)),
    ("+70000000009", "Демо Пациент 9", "demo9@example.test", date(1975, 12, 1)),
    ("+70000000010", "Демо Пациент 10", "demo10@example.test", date(1991, 6, 18)),
]

DEMO_SERVICES = [
    ("Консультация", "therapy", "Первичный приём и осмотр", 1500, 30),
    ("Чистка зубов", "hygiene", "Профессиональная гигиена", 3000, 60),
    ("Пломба", "therapy", "Лечение кариеса, пломбирование", 4500, 60),
    ("Удаление зуба", "surgery", "Простое удаление", 2500, 30),
    ("Рентген", "diagnostics", "Прицельный снимок", 800, 15),
    ("Отбеливание", "cosmetic", "Профессиональное отбеливание", 8000, 90),
    ("Имплант", "surgery", "Установка имплантата (под ключ)", 45000, 60),
    ("Брекеты (консультация)", "orthodontics", "Осмотр ортодонта, план лечения", 2000, 45),
    ("Детский приём", "pediatrics", "Осмотр и консультация детского стоматолога", 1800, 40),
    ("Пародонтология", "therapy", "Лечение дёсен", 3500, 45),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1))
        clinic = result.scalar_one_or_none()

        if clinic is None:
            clinic = Clinic(
                id=uuid.uuid4(),
                name="Демо Стоматология",
                phone="+78001234567",
                email="demo@clinic.test",
                address="ул. Демо, 1",
            )
            session.add(clinic)
            await session.flush()

        clinic_id = clinic.id

        # Doctors: ensure 4 demo doctors for this clinic
        count_doctors = await session.execute(
            select(func.count()).select_from(Doctor).where(
                Doctor.clinic_id == clinic_id,
                Doctor.full_name.like("Demo Dr.%"),
                Doctor.deleted_at.is_(None),
            )
        )
        n_doctors = int(count_doctors.scalar() or 0)
        if n_doctors < 4:
            to_add = DEMO_DOCTORS[n_doctors:4]
            new_doctors = [
                Doctor(clinic_id=clinic_id, **d)
                for d in to_add
            ]
            session.add_all(new_doctors)
            await session.flush()
            doctors_for_wh = new_doctors
        else:
            doctors_for_wh = []

        # Working hours: for any doctor of this clinic without hours, add Mon–Fri 09:00–18:00
        if doctors_for_wh:
            for doc in doctors_for_wh:
                for weekday in range(5):
                    session.add(
                        DoctorWorkingHours(
                            doctor_id=doc.id,
                            weekday=weekday,
                            start_time=time(9, 0),
                            end_time=time(18, 0),
                        )
                    )
            await session.flush()
        else:
            res = await session.execute(
                select(Doctor).where(
                    Doctor.clinic_id == clinic_id,
                    Doctor.deleted_at.is_(None),
                )
            )
            all_docs = list(res.scalars().all())
            res_wh = await session.execute(
                select(DoctorWorkingHours.doctor_id).where(
                    DoctorWorkingHours.doctor_id.in_(d.id for d in all_docs)
                ).distinct()
            )
            have_wh = set(res_wh.scalars().all())
            for doc in all_docs:
                if (doc.id,) not in have_wh:
                    for weekday in range(5):
                        session.add(
                            DoctorWorkingHours(
                                doctor_id=doc.id,
                                weekday=weekday,
                                start_time=time(9, 0),
                                end_time=time(18, 0),
                            )
                        )
            if all_docs:
                await session.flush()

        # Patients: ensure 10 demo patients (by phone) for this clinic
        res_pat = await session.execute(
            select(Patient.phone).where(
                Patient.clinic_id == clinic_id,
                Patient.phone.like("+7000000%"),
                Patient.deleted_at.is_(None),
            )
        )
        existing_phones = {r[0] for r in res_pat.all()}
        for phone, full_name, email, birth_date in DEMO_PATIENTS:
            if phone not in existing_phones:
                session.add(
                    Patient(
                        clinic_id=clinic_id,
                        phone=phone,
                        full_name=full_name,
                        email=email,
                        birth_date=birth_date,
                    )
                )
        await session.flush()

        # Services: ensure 10 demo services for this clinic
        count_svc = await session.execute(
            select(func.count()).select_from(Service).where(
                Service.clinic_id == clinic_id,
                Service.name.in_([s[0] for s in DEMO_SERVICES]),
                Service.deleted_at.is_(None),
            )
        )
        n_svc = int(count_svc.scalar() or 0)
        if n_svc < 10:
            existing_names = await session.execute(
                select(Service.name).where(
                    Service.clinic_id == clinic_id,
                    Service.deleted_at.is_(None),
                )
            )
            existing_names_set = {r[0] for r in existing_names.all()}
            for name, category, desc, price, dur in DEMO_SERVICES:
                if name not in existing_names_set:
                    session.add(
                        Service(
                            clinic_id=clinic_id,
                            name=name,
                            category=category,
                            description=desc,
                            price=price,
                            duration_minutes=dur,
                        )
                    )
                    existing_names_set.add(name)
            await session.flush()

        # ServiceDoctor: link all demo doctors to all demo services so booking flow works
        res_docs = await session.execute(
            select(Doctor).where(
                Doctor.clinic_id == clinic_id,
                Doctor.full_name.like("Demo Dr.%"),
                Doctor.deleted_at.is_(None),
            )
        )
        demo_doctors = list(res_docs.scalars().all())
        res_svc = await session.execute(
            select(Service).where(
                Service.clinic_id == clinic_id,
                Service.name.in_([s[0] for s in DEMO_SERVICES]),
                Service.deleted_at.is_(None),
            )
        )
        demo_services = list(res_svc.scalars().all())
        if demo_doctors and demo_services:
            existing = await session.execute(
                select(ServiceDoctor.service_id, ServiceDoctor.doctor_id).where(
                    ServiceDoctor.service_id.in_(s.id for s in demo_services),
                    ServiceDoctor.doctor_id.in_(d.id for d in demo_doctors),
                )
            )
            existing_pairs = set(existing.all())
            for svc in demo_services:
                for doc in demo_doctors:
                    if (svc.id, doc.id) not in existing_pairs:
                        session.add(
                            ServiceDoctor(
                                service_id=svc.id,
                                doctor_id=doc.id,
                                is_active=True,
                            )
                        )
            await session.flush()

        # Admin: ensure one admin for this clinic (email admin@example.com, password admin12345)
        admin_email = "admin@example.com"
        res_admin = await session.execute(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        if res_admin.scalar_one_or_none() is None:
            session.add(
                AdminUser(
                    clinic_id=clinic_id,
                    email=admin_email,
                    password_hash=pbkdf2_sha256.hash("admin12345"),
                    full_name="Администратор",
                )
            )
            await session.flush()

        await session.commit()


def main() -> None:
  asyncio.run(seed())


if __name__ == "__main__":
  main()

