"""Presentation seed: одна клиника, ~30 пациентов, 3 месяца записей, лояльность, омниканал.

Соответствует текущей модели продукта: один логин админа = одна клиника.
Идемпотентность: если найден admin `admin@dentapro.demo` (или legacy `filial1@dentapro.demo`),
скрипт завершается без изменений.
Полный сброс: очистить БД и выполнить `alembic upgrade head`, затем этот скрипт.

Запуск:
  poetry run python -m src.scripts.seed_presentation_showcase

Требуется: Redis/Postgres как в .env; для RBAC сначала можно выполнить
  poetry run python -m src.scripts.seed_rbac_baseline
(внутри вызывается ensure_role_permissions автоматически).
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from passlib.hash import pbkdf2_sha256

from src.application.dto.omnichannel_dto import NormalizedMessageDTO
from src.application.services.integration_gateway_service import IntegrationGatewayService
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.clinic import Clinic
from src.domain.entities.clinic_ai_settings import ClinicAiSettings
from src.domain.entities.conversation import Conversation
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.discount import Discount
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.family_link import FamilyLink
from src.domain.entities.loyalty_group import LoyaltyGroup  # noqa: F401 — FK family_links.group_id
from src.domain.entities.loyalty_campaign_settings import LoyaltyCampaignSettings
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_stage_semantic_map import LeadStageSemanticMap
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.traffic_source import TrafficSource
from src.domain.entities.campaign import Campaign
from src.domain.entities.visit_attribution import VisitAttribution
from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.patient import Patient
from src.domain.entities.payment import Payment
from src.domain.entities.product import Product  # noqa: F401 — FK tasks.inventory_product_id
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.task import Task
from src.domain.entities.wallet import Wallet
from src.infrastructure.database.base import AsyncSessionLocal
from src.core.datetime_utils import utc_now_naive
from src.scripts.seed_rbac_baseline import (
    ensure_role_permissions,
    ensure_user_manager_role,
    ensure_user_owner_role,
)

# --- Конфигурация демо (пароль только для локальной презентации) ---
DEMO_PASSWORD = "Presentation2026!"
MARKER_ADMIN_EMAIL = "admin@dentapro.demo"
MANAGER_EMAIL = "manager@dentapro.demo"
# Старый маркер трёхклинического сида — считаем БД уже заполненной
LEGACY_MARKER_ADMIN_EMAIL = "filial1@dentapro.demo"

CLINIC_SPEC: dict = {
    "name": "Стоматология «Дентал Про» — Центральная клиника",
    "phone": "+74951201001",
    "email": "info@dentapro.demo",
    "address": "125047, Москва, ул. Тверская, д. 12, оф. 45 (вход со двора, домофон 45)",
    "admin_email": "admin@dentapro.demo",
    "admin_name": "Анна Викторовна Смирнова",
}

SLOT_STARTS: list[time] = [
    time(9, 0),
    time(9, 30),
    time(10, 0),
    time(10, 30),
    time(11, 0),
    time(11, 30),
    time(12, 0),
    time(12, 30),
    time(13, 0),
    time(13, 30),
    time(14, 0),
    time(14, 30),
    time(15, 0),
    time(15, 30),
    time(16, 0),
    time(16, 30),
    time(17, 0),
    time(17, 30),
]

SERVICES_TEMPLATE: list[tuple[str, str, str, Decimal, int]] = [
    ("Первичная консультация", "therapy", "Осмотр, сбор анамнеза, план лечения", Decimal("1800"), 30),
    ("Профессиональная гигиена", "hygiene", "Удаление зубных отложений, полировка", Decimal("7200"), 60),
    ("Лечение кариеса (одно поверхностное)", "therapy", "Анестезия, препарирование, пломба", Decimal("6500"), 60),
    ("Удаление зуба простое", "surgery", "Показания: разрушенный зуб, фрагмент корня", Decimal("4200"), 45),
    ("Дентальный имплант (работа)", "surgery", "Постановка импланта с остеосинтезом", Decimal("38000"), 90),
    ("Имплантация (коронка временная)", "surgery", "Временная коронка на импланте", Decimal("12000"), 60),
    ("Консультация ортодонта", "orthodontics", "Осмотр, снимки, план выравнивания", Decimal("2500"), 45),
    ("Детский приём", "pediatrics", "Осмотр, гигиена, рекомендации родителям", Decimal("2200"), 40),
    ("Панорамный снимок (ОПТГ)", "diagnostics", "Ортопантомография", Decimal("1200"), 15),
    ("Отбеливание кабинетное", "cosmetic", "Профессиональное отбеливание", Decimal("18500"), 90),
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
    "Орлова Дарья Викторовна",
    "Зайцев Максим Андреевич",
    "Павлова Наталья Евгеньевна",
    "Семёнов Алексей Игоревич",
    "Егорова Юлия Викторовна",
    "Баранов Сергей Олегович",
    "Киселева Марина Владимировна",
    "Никитин Роман Сергеевич",
    "Волкова Оксана Валерьевна",
    "Соловьёв Дмитрий Павлович",
    "Лебедева Ирина Викторовна",
    "Крылов Виктор Николаевич",
    "Михайлова Алёна Сергеевна",
    "Фёдоров Андрей Олегович",
    "Гусева Полина Викторовна",
    "Тимофеев Владислав Игоревич",
    "Андреева Кристина Викторовна",
    "Крюкова Марина Олеговна",
    "Жукова Елена Викторовна",
    "Королёв Игорь Сергеевич",
]

DOCTORS_TEMPLATE: list[dict] = [
    {"full_name": "Волкова Марина Евгеньевна", "specialization": "Врач-стоматолог-терапевт", "experience_years": 14},
    {"full_name": "Семёнов Виктор Павлович", "specialization": "Хирург-имплантолог", "experience_years": 11},
    {"full_name": "Ларина Ольга Сергеевна", "specialization": "Ортодонт", "experience_years": 9},
    {"full_name": "Петрова Алина Викторовна", "specialization": "Врач-гигиенист", "experience_years": 7},
]


def _month_bounds(ref: date) -> tuple[date, date]:
    """Первый день прошлого месяца и последний день следующего относительно ref."""
    y, m = ref.year, ref.month
    first_this = date(y, m, 1)
    prev_last = first_this - timedelta(days=1)
    first_prev = date(prev_last.year, prev_last.month, 1)
    if m == 12:
        first_next_month = date(y + 1, 1, 1)
    else:
        first_next_month = date(y, m + 1, 1)
    last_next = (first_next_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return first_prev, last_next


def _iter_days(start: date, end: date) -> Sequence[date]:
    d = start
    out: list[date] = []
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


async def _seed_clinic_bundle(
    session: AsyncSession,
    spec: dict,
    clinic_idx: int,
    phone_prefix: str,
) -> tuple[uuid.UUID, AdminUser, list[Doctor], list[Patient], list[Service]]:
    clinic = Clinic(
        id=uuid.uuid4(),
        name=spec["name"],
        phone=spec["phone"],
        email=spec["email"],
        address=spec["address"],
        business_type="stomatology",
        business_type_custom_name=None,
    )
    session.add(clinic)
    await session.flush()

    admin = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=spec["admin_email"].strip().lower(),
        password_hash=pbkdf2_sha256.hash(DEMO_PASSWORD),
        full_name=spec["admin_name"],
    )
    session.add(admin)
    await session.flush()
    await ensure_user_owner_role(session, admin_id=admin.id, clinic_id=clinic.id)

    manager = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=MANAGER_EMAIL.strip().lower(),
        password_hash=pbkdf2_sha256.hash(DEMO_PASSWORD),
        full_name="Елена Сергеевна Орлова",
    )
    session.add(manager)
    await session.flush()
    await ensure_user_manager_role(session, admin_id=manager.id, clinic_id=clinic.id)

    # AI / omni
    session.add(
        ClinicAiSettings(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            ai_enabled=True,
            ai_tasks_enabled=True,
            ai_mode="safe_autoreply",
            ai_provider_type="external",
            ai_autoreply_enabled=False,
        )
    )
    session.add(
        OmniAISettings(
            id=uuid.uuid4(),
            scope="BUSINESS",
            scope_id=clinic.id,
            ai_mode="SUGGEST_ONLY",
        )
    )
    res_lcs = await session.execute(
        select(LoyaltyCampaignSettings).where(LoyaltyCampaignSettings.clinic_id == clinic.id)
    )
    if res_lcs.scalar_one_or_none() is None:
        session.add(
            LoyaltyCampaignSettings(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
            )
        )

    doctors: list[Doctor] = []
    for d in DOCTORS_TEMPLATE:
        doc = Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name=d["full_name"],
            specialization=d["specialization"],
            experience_years=d["experience_years"],
            specialist_role="doctor",
        )
        session.add(doc)
        doctors.append(doc)
    await session.flush()

    # 0=Пн … 6=Вс — включая воскресенье, иначе «сегодня» в выходной не попадёт в сетку расписания.
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

    # Связи врач–услуга (реалистично: не все ко всем)
    allow_map = {
        0: (0, 1, 2, 3, 7, 8),
        1: (3, 4, 5, 8),
        2: (6, 7, 8),
        3: (1, 7, 8, 9),
    }
    for di, doc in enumerate(doctors):
        idxs = allow_map.get(di, range(len(services)))
        seen_si: set[int] = set()
        for raw_si in idxs:
            si = int(raw_si) % len(services)
            if si in seen_si:
                continue
            seen_si.add(si)
            session.add(
                ServiceDoctor(
                    service_id=services[si].id,
                    doctor_id=doc.id,
                    is_active=True,
                )
            )
    await session.flush()

    patients: list[Patient] = []
    for i, pn in enumerate(PATIENT_NAMES):
        phone = f"{phone_prefix}{i:02d}"
        local = pn.lower().replace(" ", ".").replace("ё", "e") + "@mail.example"
        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            phone=phone,
            full_name=pn,
            email=local,
            birth_date=date(1975 + (i % 35), 1 + (i % 12), 1 + (i % 25)),
        )
        session.add(patient)
        patients.append(patient)
    await session.flush()

    # Скидки
    session.add(
        Discount(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            name="Скидка 10% на первый визит",
            discount_type="first_visit",
            percent_off=Decimal("10.00"),
            valid_from=date.today() - timedelta(days=60),
            valid_until=date.today() + timedelta(days=365),
        )
    )
    session.add(
        Discount(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            name="Весна 2026: гигиена −15%",
            discount_type="service",
            service_id=services[1].id,
            percent_off=Decimal("15.00"),
            valid_from=date.today() - timedelta(days=14),
            valid_until=date.today() + timedelta(days=90),
        )
    )

    # Пакеты абонементов
    pkg_visits = SubscriptionPackage(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        code=f"HYG2_{clinic_idx}",
        name="Два профессиональных гигиены",
        description="Два визита гигиены в течение 12 месяцев",
        kind="visits",
        services_included=[services[1].id],
        total_visits=2,
        total_amount=None,
        price=Decimal("12000.00"),
        validity_days=365,
    )
    pkg_mixed = SubscriptionPackage(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        code=f"FAM_{clinic_idx}",
        name="Семейный профилактический",
        description="Консультация + гигиена для двоих взрослых",
        kind="mixed",
        services_included=[services[0].id, services[1].id],
        total_visits=4,
        total_amount=None,
        price=Decimal("19900.00"),
        validity_days=180,
    )
    session.add_all([pkg_visits, pkg_mixed])
    await session.flush()

    # Подписки и кошельки: первые пять + Королёв (индекс 31) — для демо омниканала с абонементом
    for j in (0, 1, 2, 3, 4, 31):
        p = patients[j]
        session.add(
            CustomerSubscription(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                patient_id=p.id,
                subscription_package_id=pkg_visits.id,
                status="active",
                purchased_at=datetime.now(timezone.utc) - timedelta(days=60),
                activated_at=datetime.now(timezone.utc) - timedelta(days=60),
                expires_at=datetime.now(timezone.utc) + timedelta(days=120),
                remaining_visits=1,
                remaining_amount=None,
            )
        )
        session.add(
            Wallet(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                patient_id=p.id,
                balance=Decimal("2500.00"),
            )
        )
    await session.flush()

    # Семейные связи
    if len(patients) >= 4:
        session.add(
            FamilyLink(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                primary_patient_id=patients[0].id,
                related_patient_id=patients[1].id,
                relation_type="spouse",
                can_spend_from_owner_loyalty=True,
                can_view_owner_history=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True,
            )
        )
        session.add(
            FamilyLink(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                primary_patient_id=patients[2].id,
                related_patient_id=patients[3].id,
                relation_type="child",
                can_spend_from_owner_loyalty=False,
                can_view_owner_history=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True,
            )
        )

    # Промо-лента (published_at — naive UTC, колонка без tz)
    now_n = utc_now_naive()
    posts = [
        PromoPost(
            clinic_id=clinic.id,
            title="Бесплатная консультация при планировании имплантации",
            body="Запишитесь на план лечения — первичный осмотр и КТ в подарок при старте имплантации.",
            is_published=True,
            published_at=now_n - timedelta(days=3),
        ),
        PromoPost(
            clinic_id=clinic.id,
            title="Семейная профилактика: −10% на второго члена семьи",
            body="Акция действует до конца квартала на пакет «Семейный профилактический».",
            is_published=True,
            published_at=now_n - timedelta(days=10),
        ),
    ]
    session.add_all(posts)

    # Задачи
    task_specs: list[tuple[str, str, str, str, uuid.UUID]] = [
        (
            "Согласовать с лабораторией срок коронки",
            "Пациент Козлов, имплант 4.6 — ждём модель от техника до среды.",
            "in_progress",
            "high",
            admin.id,
        ),
        (
            "Перезвонить после гигиены",
            "Контроль чувствительности после Air Flow, пациентка Соколова.",
            "open",
            "medium",
            manager.id,
        ),
        (
            "Проверить страховой случай по полису ДМС",
            "Номер полиса в карте — запросить уточнение по лимитам.",
            "open",
            "urgent",
            admin.id,
        ),
        (
            "Подготовить ортодонтический план (фото + скан)",
            "Для пациента Ларина, первичка на ортодонта.",
            "open",
            "medium",
            manager.id,
        ),
    ]
    for title, desc, st, pr, assignee in task_specs:
        session.add(
            Task(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                title=title,
                description=desc,
                status=st,
                priority=pr,
                creator_id=admin.id,
                assignee_id=assignee,
                source="manual",
            )
        )

    return clinic.id, admin, doctors, patients, services


async def _seed_bookings(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    doctors: list[Doctor],
    patients: list[Patient],
    services: list[Service],
) -> None:
    ref = date.today()
    start, end = _month_bounds(ref)
    days = _iter_days(start, end)
    rng = random.Random(42)
    occupied: set[tuple[uuid.UUID, date, time]] = set()
    for d in doctors:
        for day in days:
            for slot in SLOT_STARTS:
                if rng.random() > 0.52:
                    continue
                key = (d.id, day, slot)
                if key in occupied:
                    continue
                occupied.add(key)
                pat = rng.choice(patients)
                svc = rng.choice(services)
                if day < ref:
                    st = "completed"
                elif day > ref + timedelta(days=14):
                    st = rng.choice(["confirmed", "pending"])
                else:
                    st = rng.choice(["confirmed", "completed", "pending", "pending"])
                b = Booking(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    patient_id=pat.id,
                    doctor_id=d.id,
                    service_id=svc.id,
                    appointment_date=day,
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
                        clinic_id=clinic_id,
                        booking_id=b.id,
                        provider="YOOKASSA",
                        provider_payment_id=f"demo-{b.id}",
                        amount=svc.price,
                        status="succeeded",
                    )
                    session.add(pay)
                    await session.flush()
                    b.payment_id = pay.id
                    b.prepayment_amount = svc.price


async def _ensure_anchor_bookings(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    doctors: list[Doctor],
    patients: list[Patient],
    services: list[Service],
) -> None:
    """Гарантирует записи на сегодня и завтра с выручкой по завершённым.

    Включая воскресенье, иначе «сегодня» в Sun — пустой дашборд при полном понедельнике.
    """
    today = date.today()
    anchor_days: list[date] = [today, today + timedelta(days=1)]
    res = await session.execute(
        select(Booking.doctor_id, Booking.appointment_date, Booking.appointment_time).where(
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
        )
    )
    occupied: set[tuple[uuid.UUID, date, time]] = {(r[0], r[1], r[2]) for r in res.all()}
    slot_times = [time(10, 0), time(11, 0), time(14, 0), time(15, 0), time(16, 0), time(17, 0)]

    for day in anchor_days:
        statuses = ["completed", "completed", "confirmed", "confirmed"]
        pi = 0
        for st in statuses:
            placed = False
            for slot in slot_times:
                for doc in doctors:
                    key = (doc.id, day, slot)
                    if key in occupied:
                        continue
                    occupied.add(key)
                    pat = patients[pi % len(patients)]
                    svc = services[pi % len(services)]
                    pi += 1
                    b = Booking(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        patient_id=pat.id,
                        doctor_id=doc.id,
                        service_id=svc.id,
                        appointment_date=day,
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
                            clinic_id=clinic_id,
                            booking_id=b.id,
                            provider="YOOKASSA",
                            provider_payment_id=f"anchor-{b.id}",
                            amount=svc.price,
                            status="succeeded",
                        )
                        session.add(pay)
                        await session.flush()
                        b.payment_id = pay.id
                        b.prepayment_amount = svc.price
                    placed = True
                    break
                if placed:
                    break
            if not placed:
                break


async def _seed_crm_sales(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    patients: list[Patient],
) -> None:
    pipeline = LeadPipeline(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Воронка продаж: стоматология",
        description="От первого обращения до согласования плана лечения",
        is_default=True,
    )
    session.add(pipeline)
    await session.flush()
    stage_specs: list[tuple[str, str, int, str, str, int]] = [
        ("lead_new", "Новый лид", 0, "start", "#94A3B8", 15),
        ("lead_consult", "Консультация назначена", 1, "scheduled", "#3B82F6", 45),
        ("lead_stale", "Долго не отвечает", 2, "stale", "#F59E0B", 25),
        ("lead_won", "План согласован", 3, "won", "#22C55E", 100),
        ("lead_lost", "Отказ", 4, "lost", "#EF4444", 0),
    ]
    stages: list[LeadStage] = []
    for code, name, order, _sem, color, prob in stage_specs:
        st = LeadStage(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=order,
            code=code,
            name=name,
            probability=prob,
            color=color,
        )
        session.add(st)
        stages.append(st)
    await session.flush()
    for i, spec in enumerate(stage_specs):
        sem = spec[3]
        session.add(
            LeadStageSemanticMap(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                pipeline_id=pipeline.id,
                semantic=sem,
                stage_id=stages[i].id,
            )
        )
    await session.flush()
    won = stages[3]
    cards: list[tuple[str, str, LeadStage, Patient, Decimal, str | None, str | None]] = [
        (
            "Имплантация — запрос с сайта",
            "website",
            stages[0],
            patients[0],
            Decimal("85000.00"),
            "google",
            "spring_implants",
        ),
        (
            "Ортодонтия — первичная консультация",
            "instagram",
            stages[1],
            patients[1],
            Decimal("45000.00"),
            "instagram",
            "aligners_2026",
        ),
        (
            "Гигиена + терапия (план согласован)",
            "referral",
            won,
            patients[2],
            Decimal("12000.00"),
            None,
            None,
        ),
    ]
    for title, src, stg, pat, est, utm_s, utm_c in cards:
        closed = stg.id == won.id
        session.add(
            LeadCard(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                pipeline_id=pipeline.id,
                stage_id=stg.id,
                omnichannel_contact_id=None,
                patient_id=pat.id,
                title=title,
                source=src,
                utm_source=utm_s,
                utm_medium="social" if src == "instagram" else ("cpc" if utm_s else None),
                utm_campaign=utm_c,
                estimated_value=est,
                status="success" if closed else "open",
                closed_at=datetime.now(timezone.utc) if closed else None,
                lost_reason=None,
            )
        )
    await session.flush()


async def _seed_finance_erp(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    doctors: list[Doctor],
) -> None:
    session.add_all(
        [
            Cashbox(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                name="Касса (наличные), ресепшн",
                type="cash",
                currency="RUB",
                is_default=True,
                is_active=True,
            ),
            Cashbox(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                name="Эквайринг (Тинькофф)",
                type="card",
                currency="RUB",
                is_default=False,
                is_active=True,
            ),
            Cashbox(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                name="Расчётный счёт (ООО)",
                type="bank_account",
                currency="RUB",
                is_default=False,
                is_active=True,
            ),
        ]
    )
    await session.flush()
    for doc in doctors:
        session.add(
            PayrollPolicy(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                doctor_id=doc.id,
                role=None,
                fixed_per_shift=Decimal("0.00"),
                percent_from_services=Decimal("0.3500"),
                percent_from_products=Decimal("0.1500"),
            )
        )
    await session.flush()


async def _seed_marketing_attribution(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    patients: list[Patient],
) -> None:
    ts_google = TrafficSource(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="google_ads",
        name="Google Ads",
        budget_planned=Decimal("120000.00"),
        is_active=True,
    )
    ts_vk = TrafficSource(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="vk_ads",
        name="VK Реклама",
        budget_planned=Decimal("45000.00"),
        is_active=True,
    )
    session.add_all([ts_google, ts_vk])
    await session.flush()
    camp = Campaign(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        traffic_source_id=ts_google.id,
        code="spring_hygiene_2026",
        name="Весна 2026 — гигиена",
        budget_planned=Decimal("80000.00"),
        is_active=True,
    )
    session.add(camp)
    await session.flush()
    session.add(
        VisitAttribution(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patients[3].id,
            lead_id=None,
            traffic_source_id=ts_google.id,
            campaign_id=camp.id,
            session_id="demo-session-1",
            landing_page="/services/hygiene",
            anchor="utm",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="spring_hygiene_2026",
        )
    )
    await session.flush()


async def _seed_telegram_admin_dialogue(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    """6 сообщений: клиент ↔ администратор (HUMAN_ADMIN) в одном Telegram-чате."""
    gateway = IntegrationGatewayService(session=session, business_account_id=clinic_id)
    omni = gateway.chat_service
    ext = "tg_demo_admin_thread"
    now = datetime.now(timezone.utc)
    script: list[tuple[str, str]] = [
        ("in", "Здравствуйте, хочу записаться на гигиену на субботу, есть окна?"),
        ("out", "Добрый день! На субботу есть 10:00 и 11:30 у гигиениста. Какой слот удобнее?"),
        ("in", "10:00 отлично, спасибо."),
        ("out", "Записала на 10:00. Подтвердите телефон для SMS-напоминания."),
        ("in", "+79991234567"),
        ("out", "Готово, запись в системе. Ждём вас в субботу!"),
    ]
    inbound_i = 0
    for kind, text in script:
        if kind == "in":
            await gateway.handle_inbound_normalized_message(
                NormalizedMessageDTO(
                    provider="TELEGRAM",
                    external_message_id=f"tg-{clinic_id}-adm-demo-{inbound_i}",
                    from_id=ext,
                    chat_external_id=ext,
                    text=text,
                    timestamp=now - timedelta(minutes=45 - inbound_i * 6),
                )
            )
            inbound_i += 1
            contact = await omni.contacts.find_by_external_id(
                clinic_id, "telegram_user_id", ext
            )
            if contact is not None and not contact.full_name:
                contact.full_name = "Пациент (Telegram, демо-диалог)"
        else:
            contact = await omni.contacts.find_by_external_id(
                clinic_id, "telegram_user_id", ext
            )
            if contact is None:
                continue
            chat = await omni.chats.find_open_by_contact(clinic_id, contact.id)
            if chat is None:
                continue
            await omni.append_outbound_message(chat, "HUMAN_ADMIN", text)
    await session.flush()


async def _seed_legacy_chats_for_attention(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    admin_id: uuid.UUID,
    patients: list[Patient],
) -> None:
    """Внутренние conversations/chat_messages для ленты внимания (follow-up + conflict)."""
    p_conflict = patients[10]
    p_follow = patients[11]
    conv_c = Conversation(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=p_conflict.id,
        assigned_admin_id=admin_id,
        last_message_at=utc_now_naive() - timedelta(hours=2),
        last_message_sender_type="patient",
    )
    conv_f = Conversation(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=p_follow.id,
        assigned_admin_id=admin_id,
        last_message_at=utc_now_naive() - timedelta(hours=5),
        last_message_sender_type="patient",
    )
    session.add_all([conv_c, conv_f])
    await session.flush()
    # conflict heuristic: negative keywords
    session.add(
        ChatMessage(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            conversation_id=conv_c.id,
            patient_id=p_conflict.id,
            sender_type="patient",
            message_type="text",
            body=(
                "Добрый день, недоволен сроками: коронку обещали к пятнице, "
                "по факту снова перенос. Прошу разобраться, иначе буду жаловаться в Роспотребнадзор."
            ),
        )
    )
    follow_up_at = utc_now_naive() - timedelta(hours=1)
    session.add(
        ChatMessage(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            conversation_id=conv_f.id,
            patient_id=p_follow.id,
            sender_type="patient",
            message_type="text",
            body="Напомните, пожалуйста, когда подъезжать к ортодонту — график сменился.",
            follow_up_at=follow_up_at,
            follow_up_closed=False,
        )
    )


async def _seed_omnichannel(
    session: AsyncSession,
    clinic_id: uuid.UUID,
) -> None:
    gateway = IntegrationGatewayService(session=session, business_account_id=clinic_id)
    now = datetime.now(timezone.utc)
    demos: list[tuple[NormalizedMessageDTO, str, str | None]] = [
        (
            NormalizedMessageDTO(
                provider="TELEGRAM",
                external_message_id=f"tg-{clinic_id}-1",
                from_id="tg_u1",
                chat_external_id="tg_u1",
                text=(
                    "Нужен перенос приёма с 17:00 на 18:30 — застрял в пробке на ТТК, "
                    "могу подтвердить звонком."
                ),
                timestamp=now - timedelta(hours=3),
            ),
            "telegram_user_id",
            "tg_u1",
        ),
        (
            NormalizedMessageDTO(
                provider="WHATSAPP",
                external_message_id=f"wa-{clinic_id}-1",
                from_id="+79161234501",
                chat_external_id="+79161234501",
                text=(
                    "Добрый день, уточните по стоимости снятия шва после имплантации — "
                    "в договоре не вижу отдельной строки."
                ),
                timestamp=now - timedelta(hours=2, minutes=20),
            ),
            "whatsapp_user_id",
            "+79161234501",
        ),
        (
            NormalizedMessageDTO(
                provider="VK",
                external_message_id=f"vk-{clinic_id}-1",
                from_id="vk_1002",
                chat_external_id="vk_1002",
                text="Запишите на профессиональную гигиену на субботу, желательно до обеда.",
                timestamp=now - timedelta(hours=1, minutes=40),
            ),
            "vk_user_id",
            "vk_1002",
        ),
        (
            NormalizedMessageDTO(
                provider="WEBCHAT",
                external_message_id=f"web-{clinic_id}-1",
                from_id="web_site_1",
                chat_external_id="web_site_1",
                text=(
                    "С сайта: нужна консультация по импланту Straumann, есть ли у вас в наличии компоненты?"
                ),
                timestamp=now - timedelta(hours=1),
            ),
            "webchat_user_id",
            "web_site_1",
        ),
    ]
    for dto, ext_key, ext_val in demos:
        await gateway.handle_inbound_normalized_message(dto)
        contact = await gateway.chat_service.contacts.find_by_external_id(
            business_account_id=clinic_id,
            external_key=ext_key,
            external_value=ext_val,
        )
        if contact is not None:
            if dto.provider.upper() == "WHATSAPP":
                contact.primary_phone = dto.from_id
            if dto.provider.upper() == "EMAIL":
                contact.emails = [dto.from_id]
            if "telegram" in ext_key:
                # tg_u1 — отдельный демо-пациент; Королёв только в _seed_unified_korolev_omnichannel
                contact.full_name = "Петров Сергей Иванович"
            elif "whatsapp" in ext_key:
                contact.full_name = "Лебедева Анна Викторовна"
            elif ext_key.startswith("vk"):
                contact.full_name = "Михайлов Денис Сергеевич"
            elif "webchat" in ext_key:
                contact.full_name = "Посетитель сайта"
    await session.flush()


async def _seed_unified_korolev_omnichannel(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    korolev_patient: Patient,
) -> None:
    """Один контакт и один чат: Telegram + Email; ответы HUMAN_ADMIN (без второго дубликата в списке).

    Лояльность в UI сопоставляет пациента по телефону — `primary_phone` = телефон карточки пациента.
    """
    omni = OmnichannelChatService(session)
    contact = OmniContact(
        id=uuid.uuid4(),
        business_account_id=clinic_id,
        full_name="Королёв Игорь Сергеевич",
        primary_phone=korolev_patient.phone,
        emails=["patient.korolev@mail.example"],
        external_ids={
            "telegram_user_id": "tg_u2",
            "email_user_id": "patient.korolev@mail.example",
        },
    )
    contact = await omni.contacts.create(contact)
    ch_tg = await omni.get_or_create_channel_for_provider(clinic_id, "TELEGRAM")
    ch_em = await omni.get_or_create_channel_for_provider(clinic_id, "EMAIL")
    chat = await omni.get_or_create_chat(clinic_id, contact, channel_id=ch_tg)
    await omni.create_inbound_message(
        chat,
        contact,
        "Повторите, пожалуйста, рекомендации после отбеливания — через сколько можно кофе?",
        channel_id=ch_tg,
        source_metadata={
            "provider": "TELEGRAM",
            "external_message_id": f"tg-{clinic_id}-k1",
        },
    )
    await omni.append_outbound_message(
        chat,
        "HUMAN_ADMIN",
        "Добрый день! Первые 48 часов без кофе, чая и красного вина; далее по самочувствию.",
        channel_id=ch_tg,
    )
    await omni.create_inbound_message(
        chat,
        contact,
        "Коллеги, пришлите, пожалуйста, заключение ортодонта в PDF для страховой компании.",
        channel_id=ch_em,
        source_metadata={
            "provider": "EMAIL",
            "external_message_id": f"em-{clinic_id}-k1",
        },
    )
    await omni.append_outbound_message(
        chat,
        "HUMAN_ADMIN",
        "Выслала PDF на patient.korolev@mail.example; если письма нет — проверьте «Спам».",
        channel_id=ch_em,
    )
    await omni.append_outbound_message(
        chat,
        "HUMAN_ADMIN",
        "Если нужна дополнительная подпись врача — напишите, подготовим к понедельнику.",
        channel_id=ch_tg,
    )
    await session.flush()


async def _clear_redis_schedule_cache() -> None:
    try:
        from src.infrastructure.database.redis_client import get_redis

        redis = await get_redis()
        keys: list[str] = []
        async for k in redis.scan_iter("schedule:*"):
            keys.append(k)
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass


async def seed_main() -> None:
    async with AsyncSessionLocal() as session:
        exists = await session.execute(
            select(AdminUser).where(
                AdminUser.deleted_at.is_(None),
                or_(
                    AdminUser.email == MARKER_ADMIN_EMAIL,
                    AdminUser.email == LEGACY_MARKER_ADMIN_EMAIL,
                ),
            )
        )
        if exists.scalar_one_or_none() is not None:
            print(
                "Presentation seed already applied (found admin@dentapro.demo or legacy filial1@...). "
                "To re-run, reset DB and run alembic upgrade head."
            )
            return

        await ensure_role_permissions(session)

        phone_prefix = "+700910"  # +70091000.. +70091031 (32 пациента)
        bundle = await _seed_clinic_bundle(session, CLINIC_SPEC, 0, phone_prefix)
        await session.flush()

        cid, adm, docs, pat, svc = bundle
        await _seed_bookings(session, cid, docs, pat, svc)
        await _ensure_anchor_bookings(session, cid, docs, pat, svc)
        await _seed_crm_sales(session, cid, pat)
        await _seed_finance_erp(session, cid, docs)
        await _seed_marketing_attribution(session, cid, pat)
        await _seed_legacy_chats_for_attention(session, cid, adm.id, pat)
        await _seed_omnichannel(session, cid)
        await _seed_unified_korolev_omnichannel(session, cid, pat[31])
        await _seed_telegram_admin_dialogue(session, cid)

        await session.commit()
        print("Presentation seed OK.")
        print(f"  Owner login: {MARKER_ADMIN_EMAIL}  password: {DEMO_PASSWORD}")
        print(f"  Manager login: {MANAGER_EMAIL}  password: {DEMO_PASSWORD}")
        print(f"  clinic_id: {cid}")
        print(f"  Patient UUID (Loyalty > Subscriptions search): {pat[0].id}")
        print(f"  Korolev (omnichannel + subscription demo) patient UUID: {pat[31].id}")

    await _clear_redis_schedule_cache()


def main() -> None:
    asyncio.run(seed_main())


if __name__ == "__main__":
    main()
