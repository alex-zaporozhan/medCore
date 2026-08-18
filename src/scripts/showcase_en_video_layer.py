"""English video layer on top of multi-tenant showcase (not Alembic).

Progressive data (after schema + RBAC + ``seed_multi_tenant_showcase``):
  1. Relabel orgs / clinics / staff / doctors / services / patients to EN (stable emails/slugs).
  2. Relabel Kanban / feed / staff calendar / promo / commerce / team chat already in DB.
  3. Seed multi-turn omnichannel dialogues (patient + admin) and a richer staff chat.
     Omni contacts carry ``patient_id``; copy is built from a real upcoming booking when one exists.

Idempotent. Safe on a DB that already has ``seed:multi_tenant_showcase_v1``.

    poetry run python -m src.scripts.backfill_showcase_saas_extras
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.clinic import Clinic
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.domain.entities.commerce_stock_location import CommerceStockLocation
from src.domain.entities.doctor import Doctor
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.domain.entities.organization import Organization
from src.domain.entities.patient import Patient
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.service import Service
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_chat_message import StaffChatMessage
from src.domain.entities.staff_chat_room import StaffChatRoom
from src.domain.entities.staff_feed_comment import StaffFeedComment
from src.domain.entities.staff_feed_post import StaffFeedPost
from src.domain.entities.story import Story
from src.domain.entities.task import Task
from src.domain.entities.task_board import TaskBoard
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_stream import TaskStream
from src.scripts.showcase_en_catalog import (
    DOCTOR_NAME_RU_EN,
    DOCTOR_SPEC_RU_EN,
    DOCTORS_TEMPLATE,
    ORG_SPECS,
    PATIENT_NAMES,
    SERVICE_DESC_EN,
    SERVICE_NAME_RU_EN,
    SPEC_BY_OWNER_EMAIL,
    SPEC_BY_SLUG,
)

DEMO_STOCK_CODE = "SHOWCASE_DEMO_MAIN"
GENERAL_ROOM_KIND = "GENERAL"
PROMO_TITLE_PREFIX = "Demo vitrine:"
SHOWCASE_STAFF_CAL_PREFIX = "Demo calendar:"
SHOWCASE_TASK_PREFIX = "Demo Kanban:"
STAFF_FEED_TITLE_PREFIX = "Demo CRM:"
SHOWCASE_OMNI_META = "en_video_v1"
BOOKING_CALENDAR_NOTE = "showcase_calendar_v1"

TASK_PREFIX_LEGACY = "Демо Kanban:"
CAL_PREFIX_LEGACY = "Демо календарь:"
FEED_PREFIX_LEGACY = "Демо CRM:"
PROMO_PREFIX_LEGACY = "Демо витрина:"
STAFF_CHAT_DEMO_MARK = "[demo]"

TASK_TITLE_RU_EN: dict[str, str] = {
    f"{TASK_PREFIX_LEGACY} Сверка прайса с сайтом": f"{SHOWCASE_TASK_PREFIX} Reconcile price list with the website",
    f"{TASK_PREFIX_LEGACY} Позвонить по no-show за вчера": f"{SHOWCASE_TASK_PREFIX} Call yesterday’s no-shows",
    f"{TASK_PREFIX_LEGACY} Подготовить отчёт для руководителя": f"{SHOWCASE_TASK_PREFIX} Prepare the owner report",
    f"{TASK_PREFIX_LEGACY} Согласовать скидку по абонементу": f"{SHOWCASE_TASK_PREFIX} Approve a membership discount",
    f"{TASK_PREFIX_LEGACY} Внедрить чеклист на стойке": f"{SHOWCASE_TASK_PREFIX} Roll out the front-desk checklist",
    f"{TASK_PREFIX_LEGACY} Обучение нового администратора": f"{SHOWCASE_TASK_PREFIX} Onboard the new administrator",
    f"{TASK_PREFIX_LEGACY} Ждём ответ стоматолога-ортодонта": f"{SHOWCASE_TASK_PREFIX} Waiting on the orthodontist",
    f"{TASK_PREFIX_LEGACY} Проверка витрины перед акцией": f"{SHOWCASE_TASK_PREFIX} Check the vitrine before the promo",
    f"{TASK_PREFIX_LEGACY} Согласование макетов с маркетингом": f"{SHOWCASE_TASK_PREFIX} Sign off marketing creatives",
    f"{TASK_PREFIX_LEGACY} Закрыть модуль гигиены за месяц": f"{SHOWCASE_TASK_PREFIX} Close hygiene visits for the month",
    f"{TASK_PREFIX_LEGACY} Актуализировать FAQ на сайте": f"{SHOWCASE_TASK_PREFIX} Refresh the website FAQ",
    f"{TASK_PREFIX_LEGACY} Ежемесячная сверка кассы": f"{SHOWCASE_TASK_PREFIX} Monthly cash-up",
    f"{TASK_PREFIX_LEGACY} Перенос старого договора (отменено)": f"{SHOWCASE_TASK_PREFIX} Migrate legacy contract (cancelled)",
}

CAL_TITLE_RU_EN: dict[str, str] = {
    f"{CAL_PREFIX_LEGACY} Планёрка филиала": f"{SHOWCASE_STAFF_CAL_PREFIX} Branch huddle",
    f"{CAL_PREFIX_LEGACY} Разбор NPS и отзывов": f"{SHOWCASE_STAFF_CAL_PREFIX} NPS and reviews",
    f"{CAL_PREFIX_LEGACY} Синк с маркетингом": f"{SHOWCASE_STAFF_CAL_PREFIX} Marketing sync",
    f"{CAL_PREFIX_LEGACY} Обучение: новый регламент стерилизации": f"{SHOWCASE_STAFF_CAL_PREFIX} Training: sterilization SOP",
    f"{CAL_PREFIX_LEGACY} Сверка склад/витрина": f"{SHOWCASE_STAFF_CAL_PREFIX} Stock vs vitrine check",
    f"{CAL_PREFIX_LEGACY} Подготовка к акции выходного дня": f"{SHOWCASE_STAFF_CAL_PREFIX} Weekend promo prep",
    f"{CAL_PREFIX_LEGACY} Разбор загрузки расписания": f"{SHOWCASE_STAFF_CAL_PREFIX} Schedule load review",
    f"{CAL_PREFIX_LEGACY} Внутренний аудит документов": f"{SHOWCASE_STAFF_CAL_PREFIX} Internal document audit",
    f"{CAL_PREFIX_LEGACY} Собрание по качеству сервиса": f"{SHOWCASE_STAFF_CAL_PREFIX} Service quality meeting",
    f"{CAL_PREFIX_LEGACY} IT: обновление ПО на стойке": f"{SHOWCASE_STAFF_CAL_PREFIX} Front-desk software update",
    f"{CAL_PREFIX_LEGACY} Финансовая сверка за период": f"{SHOWCASE_STAFF_CAL_PREFIX} Period finance close",
    f"{CAL_PREFIX_LEGACY} HR: график отпусков": f"{SHOWCASE_STAFF_CAL_PREFIX} HR: time-off calendar",
    f"{CAL_PREFIX_LEGACY} Закупка расходников": f"{SHOWCASE_STAFF_CAL_PREFIX} Consumables purchase",
    f"{CAL_PREFIX_LEGACY} Ретроспектива недели": f"{SHOWCASE_STAFF_CAL_PREFIX} Weekly retro",
}

FEED_TITLE_RU_EN: dict[str, str] = {
    f"{FEED_PREFIX_LEGACY} План на неделю": f"{STAFF_FEED_TITLE_PREFIX} Week plan",
    f"{FEED_PREFIX_LEGACY} Сводка NPS и отзывы": f"{STAFF_FEED_TITLE_PREFIX} NPS and reviews digest",
}

COMMERCE_SKU_EN: dict[str, str] = {
    "WH-001": "Branded clinic notebook",
    "WH-002": "Preventive mouthwash, 250 ml",
    "SRV-001": "Hygiene gift voucher",
}

CHANNEL_DISPLAY: dict[str, str] = {
    "TELEGRAM": "Telegram",
    "WHATSAPP": "WhatsApp Business",
    "WEBCHAT": "Web widget",
}

STAFF_CHAT_EXTRA_BODIES: tuple[str, ...] = (
    "Hygiene column is full tomorrow 10–13. Offer Friday PM first.",
    "Noted. I’ll text waitlist patients after lunch.",
    "Implant consults: confirm CT is on file before we book chair time.",
    "Two Telegram threads still waiting — I’ll take both.",
    "Great. Log outcomes on the booking so Finance sees completed visits.",
    "Will do. See you at the 16:00 huddle.",
)

_OPEN_BOOKING = (
    BookingStatus.PENDING.value,
    BookingStatus.CONFIRMED.value,
    BookingStatus.SCHEDULED.value,
    BookingStatus.REGISTERED.value,
)


def _utc_naive_wall() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def strip_staff_demo_mark(body: str) -> str:
    text = (body or "").strip()
    if text.startswith(STAFF_CHAT_DEMO_MARK):
        return text[len(STAFF_CHAT_DEMO_MARK) :].lstrip(" -:").strip()
    return text


def english_prefix_fallback(title: str, legacy_prefix: str, en_prefix: str, exact: dict[str, str]) -> str:
    if title in exact:
        return exact[title]
    if title.startswith(legacy_prefix):
        rest = title[len(legacy_prefix) :].strip()
        return f"{en_prefix} {rest}" if rest else en_prefix.rstrip(":")
    return title


def doctor_short_label(full_name: str) -> str:
    core = (full_name or "").split(",")[0].strip()
    parts = [p for p in core.replace(".", " ").split() if p]
    if not parts:
        return "the dentist"
    return f"Dr. {parts[-1]}"


def is_showcase_omni_message(msg: OmniMessage) -> bool:
    meta = msg.source_metadata or {}
    return str(meta.get("showcase") or "") == SHOWCASE_OMNI_META


async def _spec_for_clinic(session: AsyncSession, clinic: Clinic) -> dict[str, object] | None:
    slug = (clinic.clinic_slug or "").strip()
    if slug in SPEC_BY_SLUG:
        return SPEC_BY_SLUG[slug]
    for spec in ORG_SPECS:
        if str(spec["clinic_name"]) == clinic.name or str(spec["org_name"]) == clinic.name:
            return spec
    owner_email = (
        await session.execute(
            select(AdminUser.email).where(
                AdminUser.clinic_id == clinic.id,
                AdminUser.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    for email in owner_email:
        spec = SPEC_BY_OWNER_EMAIL.get((email or "").strip().lower())
        if spec is not None:
            return spec
    return None


async def _relabel_directory(session: AsyncSession, clinic: Clinic) -> None:
    spec = await _spec_for_clinic(session, clinic)
    if spec is None:
        return
    if clinic.organization_id:
        org = await session.get(Organization, clinic.organization_id)
        if org is not None:
            org.name = str(spec["org_name"])
    clinic.name = str(spec["clinic_name"])
    clinic.address = str(spec.get("address") or clinic.address)
    await session.flush()

    email_names: dict[str, str] = {str(spec["owner_email"]).lower(): str(spec["owner_name"])}
    for email, name in list(spec["admins"]) + list(spec["marketers"]):  # type: ignore[arg-type]
        email_names[str(email).lower()] = str(name)
    admins = (
        await session.scalars(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic.id,
                AdminUser.deleted_at.is_(None),
            )
        )
    ).all()
    for admin in admins:
        mapped = email_names.get((admin.email or "").strip().lower())
        if mapped:
            admin.full_name = mapped
    await session.flush()

    template_by_en = {str(t["full_name"]): t for t in DOCTORS_TEMPLATE}
    doctors = (
        await session.scalars(
            select(Doctor)
            .where(Doctor.clinic_id == clinic.id, Doctor.deleted_at.is_(None))
            .order_by(Doctor.experience_years.desc(), Doctor.id.asc())
        )
    ).all()
    for i, doc in enumerate(doctors):
        if doc.full_name in DOCTOR_NAME_RU_EN:
            en_name = DOCTOR_NAME_RU_EN[doc.full_name]
            doc.full_name = en_name
            tpl = template_by_en.get(en_name)
            if tpl:
                doc.specialization = str(tpl["specialization"])
        elif doc.full_name in template_by_en:
            doc.specialization = str(template_by_en[doc.full_name]["specialization"])
        elif doc.specialization in DOCTOR_SPEC_RU_EN:
            doc.specialization = DOCTOR_SPEC_RU_EN[doc.specialization]
        elif i < len(DOCTORS_TEMPLATE):
            tpl = DOCTORS_TEMPLATE[i]
            doc.full_name = str(tpl["full_name"])
            doc.specialization = str(tpl["specialization"])
    await session.flush()

    services = (
        await session.scalars(select(Service).where(Service.clinic_id == clinic.id, Service.deleted_at.is_(None)))
    ).all()
    for svc in services:
        en_name = SERVICE_NAME_RU_EN.get(svc.name)
        if en_name:
            svc.name = en_name
            svc.description = SERVICE_DESC_EN.get(en_name, svc.description)
    await session.flush()

    patients = (
        await session.scalars(
            select(Patient)
            .where(Patient.clinic_id == clinic.id, Patient.deleted_at.is_(None))
            .order_by(Patient.email.asc())
        )
    ).all()
    for i, patient in enumerate(patients):
        if i < len(PATIENT_NAMES):
            patient.full_name = PATIENT_NAMES[i]
    await session.flush()


async def _relabel_ops_surfaces(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    streams = (
        await session.scalars(
            select(TaskStream).where(TaskStream.clinic_id == clinic_id, TaskStream.slug == "general")
        )
    ).all()
    for stream in streams:
        if stream.name in ("Общее", "General"):
            stream.name = "General"
    boards = (
        await session.scalars(
            select(TaskBoard).where(TaskBoard.clinic_id == clinic_id, TaskBoard.kind == "clinic_wide")
        )
    ).all()
    for board in boards:
        if board.name in ("Основная", "Main"):
            board.name = "Main"
    await session.flush()

    tasks = (
        await session.scalars(
            select(Task).where(
                Task.clinic_id == clinic_id,
                or_(Task.title.like(f"{TASK_PREFIX_LEGACY}%"), Task.title.like(f"{SHOWCASE_TASK_PREFIX}%")),
            )
        )
    ).all()
    for task in tasks:
        task.title = english_prefix_fallback(
            task.title, TASK_PREFIX_LEGACY, SHOWCASE_TASK_PREFIX, TASK_TITLE_RU_EN
        )
        task.description = "Showcase task linked to a real staff member (and a patient when relevant)."
    comments: list[TaskComment] = []
    if tasks:
        comments = list(
            (
                await session.scalars(
                    select(TaskComment).where(TaskComment.task_id.in_([t.id for t in tasks]))
                )
            ).all()
        )
    ru_comments = {
        "Забрала в работу, до конца дня пришлю статус.": "Picked this up — status by end of day.",
        "Список no-show приложу в комментарии к отчёту.": "I’ll attach the no-show list to the report.",
        "Нужен скан договёна с пациентом — без него не закрываю.": "Need the signed scan from the patient before I can close this.",
        "Нужен скан договора с пациентом — без него не закрываю.": "Need the signed scan from the patient before I can close this.",
        "Маркетинг прислал макеты v2, жду финального ОК.": "Marketing sent v2 creatives — waiting on final OK.",
    }
    for c in comments:
        if c.text in ru_comments:
            c.text = ru_comments[c.text]
    await session.flush()

    events = (
        await session.scalars(
            select(StaffCalendarEvent).where(
                StaffCalendarEvent.clinic_id == clinic_id,
                or_(
                    StaffCalendarEvent.title.like(f"{CAL_PREFIX_LEGACY}%"),
                    StaffCalendarEvent.title.like(f"{SHOWCASE_STAFF_CAL_PREFIX}%"),
                ),
            )
        )
    ).all()
    for ev in events:
        ev.title = english_prefix_fallback(
            ev.title, CAL_PREFIX_LEGACY, SHOWCASE_STAFF_CAL_PREFIX, CAL_TITLE_RU_EN
        )
        ev.description = "Showcase staff meeting."
    await session.flush()

    posts = (
        await session.scalars(
            select(StaffFeedPost).where(
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
    ).all()
    feed_bodies = {
        f"{STAFF_FEED_TITLE_PREFIX} Week plan": (
            "Reminder: membership discounts go through the CRM card only — no verbal deals at the desk."
        ),
        f"{STAFF_FEED_TITLE_PREFIX} NPS and reviews digest": (
            "NPS held last week; complaints are mostly chair wait time. Please log actual chair time in CRM."
        ),
    }
    comment_ru_en = {
        "Зафиксировали на собрании. Маркетинг подготовит короткий гайд для стойки регистрации.": (
            "Logged in the huddle. Marketing will ship a one-pager for the front desk."
        ),
        "Чеклист для стойки выложу в KB до пятницы, ссылку пришлю в общий чат.": (
            "I’ll publish the front-desk checklist in the knowledge base by Friday and drop the link in team chat."
        ),
        "Супер, в пятницу выложу сводку в KB и отметлю в общем чате.": (
            "Great — I’ll post the digest in the knowledge base on Friday and ping team chat."
        ),
        "Супер, в пятницу выложу сводку в KB и отмечу в общем чате.": (
            "Great — I’ll post the digest in the knowledge base on Friday and ping team chat."
        ),
    }
    for post in posts:
        if post.title in FEED_TITLE_RU_EN:
            post.title = FEED_TITLE_RU_EN[post.title]
        if post.title in feed_bodies:
            post.body = feed_bodies[post.title]
        for c in (
            await session.scalars(select(StaffFeedComment).where(StaffFeedComment.post_id == post.id))
        ).all():
            if c.body in comment_ru_en:
                c.body = comment_ru_en[c.body]
    await session.flush()

    loc = (
        await session.execute(
            select(CommerceStockLocation).where(
                CommerceStockLocation.clinic_id == clinic_id,
                CommerceStockLocation.code == DEMO_STOCK_CODE,
            )
        )
    ).scalar_one_or_none()
    if loc is not None:
        loc.name = "Main sales point (demo)"
    items = (
        await session.scalars(
            select(CommerceNomenclatureItem).where(CommerceNomenclatureItem.clinic_id == clinic_id)
        )
    ).all()
    for it in items:
        if it.sku in COMMERCE_SKU_EN:
            it.name = COMMERCE_SKU_EN[it.sku]
    await session.flush()

    promos = (
        await session.scalars(select(PromoPost).where(PromoPost.clinic_id == clinic_id))
    ).all()
    for promo in promos:
        if promo.title.startswith(PROMO_PREFIX_LEGACY) or "Бесплатная консультация" in (promo.title or ""):
            promo.title = f"{PROMO_TITLE_PREFIX} Complimentary implant consult"
            promo.body = (
                "Book this month — exam and CT plan are complimentary when you start treatment. "
                "New patients only."
            )
    stories = (await session.scalars(select(Story).where(Story.clinic_id == clinic_id))).all()
    for story in stories:
        if story.caption and ("зона отдыха" in story.caption or "ремонт" in story.caption):
            story.caption = "New lounge for patients — peek at the renovation before we open."
    await session.flush()


async def _ensure_staff_chat_dialogues(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    owner_id: uuid.UUID,
    second_id: uuid.UUID,
) -> None:
    room = (
        await session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.clinic_id == clinic_id,
                StaffChatRoom.kind == GENERAL_ROOM_KIND,
            )
        )
    ).scalar_one_or_none()
    if room is None:
        return
    room.title = "Team chat"
    await session.flush()

    existing = (
        await session.scalars(
            select(StaffChatMessage)
            .where(StaffChatMessage.room_id == room.id)
            .order_by(StaffChatMessage.created_at.asc())
        )
    ).all()
    ru_to_en = {
        "Коллеги, доброе утро! Сегодня держим фокус на NPS после приёма — короткий опрос у администратора.": (
            "Morning — today’s focus is post-visit NPS. Keep the desk survey short."
        ),
        "Принято. На стойке уже стоят планшеты с формой, вечером снимем сводку в отчётах.": (
            "Done. Tablets are on the desk; I’ll pull the report tonight."
        ),
    }
    for msg in existing:
        if msg.body in ru_to_en:
            msg.body = ru_to_en[msg.body]
        elif msg.body.startswith(STAFF_CHAT_DEMO_MARK):
            msg.body = strip_staff_demo_mark(msg.body)
    await session.flush()

    have = {strip_staff_demo_mark(m.body) for m in existing}
    if all(body in have for body in STAFF_CHAT_EXTRA_BODIES):
        return

    now = _utc_naive_wall()
    speakers = (owner_id, second_id)
    offsets = (36, 30, 24, 18, 12, 6)
    for i, body in enumerate(STAFF_CHAT_EXTRA_BODIES):
        if body in have:
            continue
        session.add(
            StaffChatMessage(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                room_id=room.id,
                author_admin_id=speakers[i % 2],
                body=body,
                created_at=now - timedelta(minutes=offsets[i]),
            )
        )
    await session.flush()


async def _patient_by_name(session: AsyncSession, clinic_id: uuid.UUID, full_name: str) -> Patient | None:
    return (
        await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.full_name == full_name,
                Patient.deleted_at.is_(None),
            ).limit(1)
        )
    ).scalar_one_or_none()


async def _upcoming_booking_line(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> tuple[str, str] | None:
    today = date.today()
    row = (
        await session.execute(
            select(Booking, Doctor, Service)
            .join(Doctor, Doctor.id == Booking.doctor_id)
            .join(Service, Service.id == Booking.service_id)
            .where(
                Booking.clinic_id == clinic_id,
                Booking.patient_id == patient_id,
                Booking.deleted_at.is_(None),
                Booking.appointment_date >= today,
                Booking.status.in_(_OPEN_BOOKING),
            )
            .order_by(Booking.appointment_date.asc(), Booking.appointment_time.asc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    booking, doctor, service = row
    when = f"{booking.appointment_date.strftime('%A')} {booking.appointment_time.strftime('%H:%M')}"
    line = f"{when} — {service.name}, {doctor_short_label(doctor.full_name)}"
    return line, service.name


def _turns_for_script(kind: str, patient_name: str, booking_line: str | None) -> list[tuple[str, str]]:
    first = patient_name.split()[0]
    if kind == "TELEGRAM":
        if booking_line:
            return [
                ("in", f"Hi — can I confirm my next visit? I think it’s {booking_line}."),
                ("out", f"Hi {first} — yes, that’s the slot we have: {booking_line}. Want to keep it?"),
                ("in", "Yes, please. Same doctor is perfect."),
                ("out", f"Kept as booked. Reminder goes out the day before. See you — {booking_line}."),
            ]
        return [
            ("in", "Hi — can I move my hygiene visit to Friday after 16:00? School pickup ran late."),
            ("out", f"Hi {first} — I’ll check the hygiene column and hold a Friday afternoon chair if one is free."),
            ("in", "Thank you. Same doctor if possible."),
            ("out", "Noted. I’ll confirm in this thread once the slot is locked in the calendar."),
        ]
    if kind == "WHATSAPP":
        if booking_line:
            return [
                ("in", f"Hello, I have {booking_line}. Do I still need a CT scan?"),
                ("out", f"Yes — please arrive 15 minutes early so we can upload imaging before {booking_line}."),
                ("in", "Got it, I’ll bring the disk from the imaging center."),
                ("out", "Perfect. Front desk will check you in as soon as you arrive."),
            ]
        return [
            ("in", "Hello, the implant consult is coming up. Do I still need a CT scan?"),
            ("out", "Yes — please arrive 15 minutes early so we can upload the CT before you see the surgeon."),
            ("in", "Got it, I’ll bring the disk from the imaging center."),
            ("out", "Perfect. Front desk will check you in as soon as you arrive."),
        ]
    if booking_line:
        return [
            ("in", "Do you take new ortho patients this month? Teen, 14."),
            ("out", f"We do. We already have {first} on the book: {booking_line}."),
            ("in", "That’s us — how long is that visit?"),
            ("out", "About 30 minutes — exam and a written plan. See you then."),
        ]
    return [
        ("in", "Do you take new ortho patients this month? Teen, 14."),
        ("out", "We do. Dr. Larina has new-patient exams this week — I can hold Tuesday morning or Thursday afternoon."),
        ("in", "Tuesday morning works. How long is the first visit?"),
        ("out", f"About 30 minutes — exam and a written plan. I’ll book {patient_name} as soon as you confirm a slot."),
    ]


async def _find_omni_contact(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    provider_key: str,
    from_id: str,
    patient_id: uuid.UUID | None,
) -> OmniContact | None:
    rows = (
        await session.scalars(select(OmniContact).where(OmniContact.business_account_id == clinic_id))
    ).all()
    for row in rows:
        ids = row.external_ids or {}
        if str(ids.get(provider_key) or "") == from_id:
            return row
        if patient_id is not None and str(ids.get("patient_id") or "") == str(patient_id):
            if provider_key not in ids or str(ids.get(provider_key) or "") in ("", from_id):
                return row
    return None


async def _decorate_channel(session: AsyncSession, channel_id: uuid.UUID | None, provider: str) -> None:
    if channel_id is None:
        return
    channel = await session.get(Channel, channel_id)
    if channel is None:
        return
    pretty = CHANNEL_DISPLAY.get(provider)
    if pretty:
        channel.display_name = pretty
    if not channel.settings_ref:
        channel.settings_ref = "showcase_en_video_v1"
    await session.flush()


async def _outbound_exists(session: AsyncSession, chat_id: uuid.UUID, ext_id: str, text: str) -> bool:
    by_ext = await session.scalar(
        select(func.count())
        .select_from(OmniMessage)
        .where(
            OmniMessage.chat_id == chat_id,
            OmniMessage.direction == "OUTBOUND",
            OmniMessage.source_metadata.isnot(None),
            OmniMessage.source_metadata["external_message_id"].as_string() == ext_id,
        )
    )
    if int(by_ext or 0) > 0:
        return True
    by_text = await session.scalar(
        select(func.count())
        .select_from(OmniMessage)
        .where(
            OmniMessage.chat_id == chat_id,
            OmniMessage.direction == "OUTBOUND",
            OmniMessage.content == text,
        )
    )
    return int(by_text or 0) > 0


async def _ensure_omni_dialogues(
    session: AsyncSession,
    clinic: Clinic,
    owner_id: uuid.UUID,
) -> None:
    """Patient ↔ admin threads for Omni Chat (no AI orchestrator, no live send)."""
    omni = OmnichannelChatService(session)
    key = (clinic.clinic_slug or "clinic").replace("showcase-", "")
    now = datetime.now(timezone.utc)

    scripts: list[dict[str, object]] = [
        {
            "provider": "TELEGRAM",
            "from_id": f"tg_video_{key}_anna",
            "name": "Anna Smirnova",
            "kind": "TELEGRAM",
        },
        {
            "provider": "WHATSAPP",
            "from_id": f"+7999{clinic.id.int % 10_000_000:07d}",
            "name": "Ivan Kozlov",
            "kind": "WHATSAPP",
        },
        {
            "provider": "WEBCHAT",
            "from_id": f"web_video_{key}_maria",
            "name": "Maria Sokolova",
            "kind": "WEBCHAT",
        },
    ]

    for script in scripts:
        provider = str(script["provider"])
        name = str(script["name"])
        patient = await _patient_by_name(session, clinic.id, name)
        synthetic_from = str(script["from_id"])
        from_id = synthetic_from
        if provider == "WHATSAPP" and patient is not None and (patient.phone or "").strip():
            from_id = patient.phone.strip()
        channel_id = await omni.get_or_create_channel_for_provider(clinic.id, provider)
        await _decorate_channel(session, channel_id, provider)
        provider_key = provider.lower() + "_user_id"

        contact = await _find_omni_contact(
            session,
            clinic.id,
            provider_key=provider_key,
            from_id=from_id,
            patient_id=patient.id if patient is not None else None,
        )
        if contact is None and from_id != synthetic_from:
            contact = await _find_omni_contact(
                session,
                clinic.id,
                provider_key=provider_key,
                from_id=synthetic_from,
                patient_id=patient.id if patient is not None else None,
            )
        ids: dict[str, str] = {provider_key: from_id}
        if patient is not None:
            ids["patient_id"] = str(patient.id)
        if contact is None:
            contact = OmniContact(
                business_account_id=clinic.id,
                full_name=name,
                primary_phone=from_id if provider == "WHATSAPP" else (patient.phone if patient else None),
                external_ids=ids,
            )
            session.add(contact)
            await session.flush()
        else:
            contact.full_name = name
            merged = dict(contact.external_ids or {})
            merged.update(ids)
            contact.external_ids = merged
            if provider == "WHATSAPP":
                contact.primary_phone = from_id
            await session.flush()

        chat = await omni.get_or_create_chat(clinic.id, contact, channel_id=channel_id)
        chat.title = name
        chat.ai_mode = "DISABLED"
        chat.assignee_admin_id = owner_id
        if chat.claimed_at is None:
            chat.claimed_at = _utc_naive_wall()
        await session.flush()

        booking_line = None
        if patient is not None:
            found = await _upcoming_booking_line(session, clinic.id, patient.id)
            if found:
                booking_line = found[0]
        turns = _turns_for_script(str(script["kind"]), name, booking_line)

        for i, (direction, text) in enumerate(turns):
            ext_id = f"showcase-en-{key}-{provider.lower()}-{i}"
            if direction == "in":
                if await omni.exists_inbound_by_external_id(chat.id, provider, ext_id):
                    continue
                await omni.create_inbound_message(
                    chat=chat,
                    contact=contact,
                    content=text,
                    channel_id=channel_id,
                    source_metadata={
                        "provider": provider,
                        "external_message_id": ext_id,
                        "from_id": from_id,
                        "chat_external_id": from_id,
                        "showcase": SHOWCASE_OMNI_META,
                    },
                )
            else:
                if await _outbound_exists(session, chat.id, ext_id, text):
                    continue
                await omni.append_outbound_message(
                    chat,
                    "HUMAN_ADMIN",
                    text,
                    channel_id=channel_id,
                    sender_admin_id=owner_id,
                    source_metadata={
                        "showcase": SHOWCASE_OMNI_META,
                        "external_message_id": ext_id,
                        "provider": provider,
                    },
                )

        msgs = (
            await session.scalars(
                select(OmniMessage).where(OmniMessage.chat_id == chat.id).order_by(OmniMessage.created_at.asc())
            )
        ).all()
        showcase_msgs = [m for m in msgs if is_showcase_omni_message(m)]
        if showcase_msgs:
            base = now - timedelta(hours=3)
            for i, msg in enumerate(showcase_msgs):
                stamp = (base + timedelta(minutes=i * 7)).replace(tzinfo=None)
                msg.created_at = stamp
            last = showcase_msgs[-1]
            chat.last_message_at = last.created_at
            chat.last_actor_type = last.actor_type
        await session.flush()

    legacy = (
        await session.scalars(
            select(OmniMessage).where(
                OmniMessage.content.like("%имплантации%"),
            )
        )
    ).all()
    for msg in legacy:
        if msg.chat_id is None:
            continue
        contact = await session.get(OmniContact, msg.contact_id) if msg.contact_id else None
        if contact is None or contact.business_account_id != clinic.id:
            continue
        msg.content = "Hi — I’d like to confirm the interval between visits after implant surgery."
    await session.flush()


async def apply_showcase_en_video_layer(
    session: AsyncSession,
    *,
    clinic: Clinic,
    owner_admin_id: uuid.UUID,
) -> None:
    other = (
        await session.execute(
            select(AdminUser.id).where(
                AdminUser.clinic_id == clinic.id,
                AdminUser.id != owner_admin_id,
                AdminUser.deleted_at.is_(None),
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            ).limit(1)
        )
    ).scalar_one_or_none() or owner_admin_id
    await _relabel_directory(session, clinic)
    await _relabel_ops_surfaces(session, clinic.id)
    await _ensure_staff_chat_dialogues(session, clinic.id, owner_admin_id, other)
    await _ensure_omni_dialogues(session, clinic, owner_admin_id)
