"""Multi-tenant showcase: several organizations, SaaS intents, staff RBAC, clinical demo data.

Fills the **platform founder** dashboard (`compute_platform_founder_dashboard_summary`):
active organizations with non-revoked ``platform_signup_intents`` and catalog-backed MRR.

Also seeds per clinic: owner (RBAC owner), 2× admin, 2× manager (маркетолог / широкий доступ),
doctors, patients, recent completed bookings + payments, one omnichannel inbound thread.

**Not** an Alembic migration: schema stays in Alembic only; run ``alembic upgrade head`` first.

Idempotent: if any ``platform_signup_intents.notes == SEED_MARKER``, the script exits.

Usage:
  poetry run python -m src.scripts.seed_multi_tenant_showcase
  poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials

Credentials (local demo only): see ``documentation/DEMO_MULTI_TENANT_CREDENTIALS.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from passlib.hash import pbkdf2_sha256
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.omnichannel_dto import NormalizedMessageDTO
from src.application.services.integration_gateway_service import IntegrationGatewayService
from src.application.services.platform_billing_service import resolve_entitlement_keys_for_intent
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.domain.entities.patient import Patient
from src.domain.entities.payment import Payment
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.infrastructure.database.base import AsyncSessionLocal
from src.scripts.seed_rbac_baseline import (
    ensure_role_permissions,
    ensure_user_owner_role,
    ensure_user_role_by_code,
)

SEED_MARKER = "seed:multi_tenant_showcase_v1"
SHOWCASE_PASSWORD = "ShowcaseMT2026!"

ORG_SPECS: list[dict[str, object]] = [
    {
        "key": "kazan",
        "org_name": "ООО «Улыбка Плюс»",
        "clinic_name": "Стоматология «Улыбка Плюс» — Казань",
        "slug": "showcase-kazan",
        "plan_slug": "start",
        "owner_email": "owner.kazan@showcase-mt.demo",
        "owner_name": "Рафаэль Ильдарович Мухаметзянов",
        "admins": [
            ("admin1.kazan@showcase-mt.demo", "Светлана Олеговна Кириллова"),
            ("admin2.kazan@showcase-mt.demo", "Дмитрий Павлович Ершов"),
        ],
        "marketers": [
            ("marketing1.kazan@showcase-mt.demo", "Алина Сергеевна Волкова"),
            ("marketing2.kazan@showcase-mt.demo", "Кирилл Андреевич Назаров"),
        ],
    },
    {
        "key": "nizhny",
        "org_name": "ООО «Дентал-Про НН»",
        "clinic_name": "Клиника «Дентал-Про» — Нижний Новгород",
        "slug": "showcase-nizhny",
        "plan_slug": "growth",
        "owner_email": "owner.nizhny@showcase-mt.demo",
        "owner_name": "Елена Викторовна Смирнова",
        "admins": [
            ("admin1.nizhny@showcase-mt.demo", "Игорь Николаевич Зайцев"),
            ("admin2.nizhny@showcase-mt.demo", "Марина Олеговна Фролова"),
        ],
        "marketers": [
            ("marketing1.nizhny@showcase-mt.demo", "Ольга Игоревна Лебедева"),
            ("marketing2.nizhny@showcase-mt.demo", "Павел Сергеевич Орлов"),
        ],
    },
    {
        "key": "samara",
        "org_name": "ООО «Семейная стоматология Самара»",
        "clinic_name": "«Семейная стоматология» — Самара",
        "slug": "showcase-samara",
        "plan_slug": "business_os",
        "owner_email": "owner.samara@showcase-mt.demo",
        "owner_name": "Андрей Олегович Белов",
        "admins": [
            ("admin1.samara@showcase-mt.demo", "Наталья Евгеньевна Павлова"),
            ("admin2.samara@showcase-mt.demo", "Сергей Владимирович Тихонов"),
        ],
        "marketers": [
            ("marketing1.samara@showcase-mt.demo", "Юлия Викторовна Егорова"),
            ("marketing2.samara@showcase-mt.demo", "Максим Андреевич Зайцев"),
        ],
    },
    {
        "key": "krasnodar",
        "org_name": "ООО «Имплант-Эксперт Юг»",
        "clinic_name": "«Имплант-Эксперт» — Краснодар",
        "slug": "showcase-krasnodar",
        "plan_slug": "growth",
        "owner_email": "owner.krasnodar@showcase-mt.demo",
        "owner_name": "Оксана Валерьевна Волкова",
        "admins": [
            ("admin1.krasnodar@showcase-mt.demo", "Роман Сергеевич Никитин"),
            ("admin2.krasnodar@showcase-mt.demo", "Ирина Викторовна Лебедева"),
        ],
        "marketers": [
            ("marketing1.krasnodar@showcase-mt.demo", "Дарья Викторовна Орлова"),
            ("marketing2.krasnodar@showcase-mt.demo", "Константин Юрьевич Тарасов"),
        ],
    },
    {
        "key": "rostov",
        "org_name": "ООО «Премьер Дент Юг»",
        "clinic_name": "«Премьер Дент» — Ростов-на-Дону",
        "slug": "showcase-rostov",
        "plan_slug": "start",
        "owner_email": "owner.rostov@showcase-mt.demo",
        "owner_name": "Виктор Николаевич Крылов",
        "admins": [
            ("admin1.rostov@showcase-mt.demo", "Алёна Сергеевна Михайлова"),
            ("admin2.rostov@showcase-mt.demo", "Владислав Игоревич Тимофеев"),
        ],
        "marketers": [
            ("marketing1.rostov@showcase-mt.demo", "Полина Викторовна Гусева"),
            ("marketing2.rostov@showcase-mt.demo", "Алексей Игоревич Семёнов"),
        ],
    },
]

DOCTORS_TEMPLATE: list[dict[str, object]] = [
    {"full_name": "Волкова Марина Евгеньевна", "specialization": "Врач-стоматолог-терапевт", "experience_years": 12},
    {"full_name": "Семёнов Виктор Павлович", "specialization": "Хирург-имплантолог", "experience_years": 10},
    {"full_name": "Ларина Ольга Сергеевна", "specialization": "Ортодонт", "experience_years": 8},
]

SERVICES_TEMPLATE: list[tuple[str, str, str, Decimal, int]] = [
    ("Первичная консультация", "therapy", "Осмотр и план лечения", Decimal("1800"), 30),
    ("Профессиональная гигиена", "hygiene", "Удаление отложений, полировка", Decimal("7200"), 60),
    ("Лечение кариеса (одна поверхность)", "therapy", "Пломба", Decimal("6500"), 60),
    ("Удаление зуба простое", "surgery", "Амбулаторно", Decimal("4200"), 45),
]

PATIENT_NAMES: list[str] = [
    "Козлов Иван Сергеевич",
    "Соколова Мария Андреевна",
    "Нестеров Павел Дмитриевич",
    "Филиппова Ольга Игоревна",
    "Громов Артём Владимирович",
    "Вишневская Татьяна Сергеевна",
    "Морозов Денис Николаевич",
    "Кузнецова Екатерина Павловна",
    "Романов Илья Олегович",
    "Смирнова Анна Викторовна",
    "Белова Светлана Михайловна",
    "Тарасов Константин Юрьевич",
]


def _tariff_snapshot(plan_slug: str) -> dict[str, object]:
    return {
        "plan_slug": plan_slug,
        "billing_period": "monthly",
        "extra_entitlement_keys": [],
    }


async def _replace_org_entitlements(
    session: AsyncSession,
    organization_id: uuid.UUID,
    tariff_snapshot: dict[str, object],
) -> None:
    keys = await resolve_entitlement_keys_for_intent(session, tariff_snapshot)
    await session.execute(
        delete(OrganizationEntitlement).where(
            OrganizationEntitlement.organization_id == organization_id,
        )
    )
    for key in keys:
        session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=organization_id,
                entitlement_key=key[:128],
                source="tariff_snapshot",
            )
        )
    await session.flush()


async def _seed_one_org(
    session: AsyncSession,
    spec: dict[str, object],
    org_index: int,
) -> None:
    org = Organization(
        id=uuid.uuid4(),
        name=str(spec["org_name"]),
    )
    session.add(org)
    await session.flush()

    clinic = Clinic(
        id=uuid.uuid4(),
        organization_id=org.id,
        name=str(spec["clinic_name"]),
        phone=f"+7495{1000000 + org_index * 11111:07d}",
        email=f"info.{spec['key']}@showcase-mt.demo",
        address=f"Демо-адрес, филиал «{spec['key']}»",
        business_type="stomatology",
        clinic_slug=str(spec["slug"]),
    )
    session.add(clinic)
    await session.flush()

    owner = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=str(spec["owner_email"]).strip().lower(),
        password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
        full_name=str(spec["owner_name"]),
    )
    session.add(owner)
    await session.flush()
    await ensure_user_owner_role(session, admin_id=owner.id, clinic_id=clinic.id)

    admins_spec = spec["admins"]
    assert isinstance(admins_spec, list)
    for email, full_name in admins_spec:
        u = AdminUser(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=str(email).strip().lower(),
            password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
            full_name=str(full_name),
        )
        session.add(u)
        await session.flush()
        await ensure_user_role_by_code(
            session, admin_id=u.id, clinic_id=clinic.id, role_code="admin"
        )

    marketers_spec = spec["marketers"]
    assert isinstance(marketers_spec, list)
    for email, full_name in marketers_spec:
        u = AdminUser(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=str(email).strip().lower(),
            password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
            full_name=str(full_name),
        )
        session.add(u)
        await session.flush()
        await ensure_user_role_by_code(
            session, admin_id=u.id, clinic_id=clinic.id, role_code="manager"
        )

    snap = _tariff_snapshot(str(spec["plan_slug"]))
    intent = PlatformSignupIntent(
        id=uuid.uuid4(),
        status="active",
        email=owner.email,
        tariff_snapshot=snap,
        organization_id=org.id,
        provisioned_admin_id=owner.id,
        paid_at=datetime.now(timezone.utc) - timedelta(days=30 - org_index * 3),
        notes=SEED_MARKER,
    )
    session.add(intent)
    await session.flush()

    await _replace_org_entitlements(session, org.id, snap)

    doctors: list[Doctor] = []
    for d in DOCTORS_TEMPLATE:
        doc = Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name=str(d["full_name"]),
            specialization=str(d["specialization"]),
            experience_years=int(d["experience_years"]),
            specialist_role="doctor",
        )
        session.add(doc)
        doctors.append(doc)
    await session.flush()

    for doc in doctors:
        for weekday in range(0, 7):
            session.add(
                DoctorWorkingHours(
                    doctor_id=doc.id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(18, 0),
                )
            )
    await session.flush()

    services: list[Service] = []
    for name, cat, desc, price, dur in SERVICES_TEMPLATE:
        svc = Service(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            name=name,
            category=cat,
            description=desc,
            price=price,
            duration_minutes=dur,
        )
        session.add(svc)
        services.append(svc)
    await session.flush()

    for di, doc in enumerate(doctors):
        for si, svc in enumerate(services):
            if (di + si) % 2 == 0:
                session.add(
                    ServiceDoctor(
                        service_id=svc.id,
                        doctor_id=doc.id,
                        is_active=True,
                    )
                )
    await session.flush()

    patients: list[Patient] = []
    for i, pn in enumerate(PATIENT_NAMES):
        tail = 9000000000 + org_index * 10000 + i
        phone = f"+7{tail}"
        local = f"p{org_index}.{i}@showcase-mt.demo"
        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            phone=phone,
            full_name=pn,
            email=local,
            birth_date=date(1978 + (i % 25), 1 + (i % 11), 1 + (i % 20)),
        )
        session.add(patient)
        patients.append(patient)
    await session.flush()

    rng = random.Random(100 + org_index)
    today = date.today()
    for day_offset in range(-21, 1):
        d = today + timedelta(days=day_offset)
        if d.weekday() >= 5:
            continue
        for doc in doctors:
            if rng.random() > 0.35:
                continue
            pat = rng.choice(patients)
            svc = rng.choice(services)
            slot = time(10 + rng.randint(0, 6), rng.choice((0, 30)), 0)
            st = "completed" if day_offset < -1 else rng.choice(["completed", "confirmed", "pending"])
            b = Booking(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                patient_id=pat.id,
                doctor_id=doc.id,
                service_id=svc.id,
                appointment_date=d,
                appointment_time=slot,
                status=st,
                prepayment_amount=Decimal("0"),
                erp_processed=st == "completed",
                erp_error_code=None,
            )
            session.add(b)
            await session.flush()
            if st == "completed":
                pay = Payment(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    booking_id=b.id,
                    provider="YOOKASSA",
                    provider_payment_id=f"showcase-{b.id}",
                    amount=svc.price,
                    status="succeeded",
                )
                session.add(pay)
                await session.flush()
                b.payment_id = pay.id
                b.prepayment_amount = svc.price

    gateway = IntegrationGatewayService(session=session, business_account_id=clinic.id)
    ext = f"tg_showcase_{spec['key']}"
    await gateway.handle_inbound_normalized_message(
        NormalizedMessageDTO(
            provider="TELEGRAM",
            external_message_id=f"tg-{clinic.id}-showcase",
            from_id=ext,
            chat_external_id=ext,
            text="Здравствуйте, хочу уточнить интервал между приёмами после имплантации.",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
    )


async def seed_main() -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(PlatformSignupIntent).where(PlatformSignupIntent.notes == SEED_MARKER).limit(1)
        )
        if res.scalar_one_or_none() is not None:
            print(
                "Multi-tenant showcase already applied (notes marker on platform_signup_intents). "
                "To re-run: reset DB, then alembic upgrade head."
            )
            return

        await ensure_role_permissions(session)

        for i, spec in enumerate(ORG_SPECS):
            await _seed_one_org(session, spec, i)

        await session.commit()
        print("Multi-tenant showcase seed OK (5 orgs, founder KPIs + per-clinic staff).")
        print(f"  Shared password: {SHOWCASE_PASSWORD}")
        print("  Human-readable list: documentation/DEMO_MULTI_TENANT_CREDENTIALS.md")


def list_credentials() -> None:
    # ASCII-only lines so `python -m ... --list-credentials` works on Windows cp1252 consoles.
    print("# Demo credentials (multi-tenant showcase)\n")
    print(f"Single password for all accounts below: `{SHOWCASE_PASSWORD}`\n")
    print("| Role / site | Email |")
    print("|---|---|")
    for spec in ORG_SPECS:
        key = spec["key"]
        print(f"| Owner ({key}) | {spec['owner_email']} |")
        admins = spec["admins"]
        assert isinstance(admins, list)
        for email, _ in admins:
            print(f"| Admin ({key}) | {email} |")
        marketers = spec["marketers"]
        assert isinstance(marketers, list)
        for email, _ in marketers:
            print(f"| Marketer / manager ({key}) | {email} |")
    print(
        "\nPlatform founder user is not created here; use "
        "`python -m src.scripts.create_platform_founder_user`."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list-credentials",
        action="store_true",
        help="Print markdown table to stdout (for docs)",
    )
    args = parser.parse_args()
    if args.list_credentials:
        list_credentials()
        return
    asyncio.run(seed_main())


if __name__ == "__main__":
    main()
