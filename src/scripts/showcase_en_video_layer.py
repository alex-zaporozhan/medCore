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

from sqlalchemy import or_, select
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
from src.domain.entities.platform_catalog_option import PlatformCatalogOption
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.service import Service
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_chat_message import StaffChatMessage
from src.domain.entities.staff_chat_room import StaffChatRoom
from src.domain.entities.staff_chat_room_member import StaffChatRoomMember
from src.domain.entities.staff_feed_comment import StaffFeedComment
from src.domain.entities.staff_feed_post import StaffFeedPost
from src.domain.entities.story import Story
from src.domain.entities.task import Task
from src.domain.entities.task_board import TaskBoard
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_stream import TaskStream
from src.scripts.showcase_en_catalog import (
    CATALOG_OPTION_EN,
    CATALOG_PLAN_EN,
    DOCTOR_NAME_RU_EN,
    DOCTOR_SPEC_RU_EN,
    DOCTORS_TEMPLATE,
    ORG_SPECS,
    PATIENT_NAMES,
    SERVICE_DESC_EN,
    SERVICE_NAME_RU_EN,
    SPEC_BY_OWNER_EMAIL,
    SPEC_BY_SLUG,
    WINDOW_CAL_PREFIX_LEGACY,
    WINDOW_TASK_PREFIX_LEGACY,
    patient_phone,
)

DEMO_STOCK_CODE = "SHOWCASE_DEMO_MAIN"
GENERAL_ROOM_KIND = "GENERAL"
GROUP_ROOM_KIND = "GROUP"
MEMBERSHIP_GROUP = "group"
STAFF_GROUP_TITLE_PREFIX = ""
STAFF_GROUP_TITLE_PREFIX_LEGACY = "Demo huddle: "
PROMO_TITLE_CANONICAL = "Complimentary implant consult"
PROMO_BODY_CANONICAL = (
    "Book this month — exam and CT plan are complimentary when you start treatment. "
    "New patients only."
)
PROMO_TITLE_PREFIX = "Demo vitrine:"  # legacy EN marker for idempotent lookup
SHOWCASE_STAFF_CAL_PREFIX = "Demo calendar:"  # legacy EN marker
SHOWCASE_TASK_PREFIX = "Demo Kanban:"  # legacy EN marker
STAFF_FEED_TITLE_PREFIX = "Demo CRM:"  # legacy EN marker
STAFF_FEED_TITLE_WEEK = "Week plan"
STAFF_FEED_TITLE_NPS = "NPS and reviews digest"
SHOWCASE_OMNI_META = "en_video_v1"
BOOKING_CALENDAR_NOTE = "showcase_calendar_v1"

TASK_PREFIX_LEGACY = "Демо Kanban:"
CAL_PREFIX_LEGACY = "Демо календарь:"
FEED_PREFIX_LEGACY = "Демо CRM:"
PROMO_PREFIX_LEGACY = "Демо витрина:"
STAFF_CHAT_DEMO_MARK = "[demo]"

TASK_TITLES_CANONICAL: tuple[str, ...] = (
    "Reconcile price list with the website",
    "Call yesterday’s no-shows",
    "Prepare the owner report",
    "Approve a membership discount",
    "Roll out the front-desk checklist",
    "Onboard the new administrator",
    "Waiting on the orthodontist",
    "Check the vitrine before the promo",
    "Sign off marketing creatives",
    "Close hygiene visits for the month",
    "Refresh the website FAQ",
    "Monthly cash-up",
    "Migrate legacy contract (cancelled)",
)

CAL_TITLES_CANONICAL: tuple[str, ...] = (
    "Branch huddle",
    "NPS and reviews",
    "Marketing sync",
    "Training: sterilization SOP",
    "Stock vs vitrine check",
    "Weekend promo prep",
    "Schedule load review",
    "Internal document audit",
    "Service quality meeting",
    "Front-desk software update",
    "Period finance close",
    "HR: time-off calendar",
    "Consumables purchase",
    "Weekly retro",
)

TASK_TITLE_RU_EN: dict[str, str] = {
    f"{TASK_PREFIX_LEGACY} Сверка прайса с сайтом": TASK_TITLES_CANONICAL[0],
    f"{TASK_PREFIX_LEGACY} Позвонить по no-show за вчера": TASK_TITLES_CANONICAL[1],
    f"{TASK_PREFIX_LEGACY} Подготовить отчёт для руководителя": TASK_TITLES_CANONICAL[2],
    f"{TASK_PREFIX_LEGACY} Согласовать скидку по абонементу": TASK_TITLES_CANONICAL[3],
    f"{TASK_PREFIX_LEGACY} Внедрить чеклист на стойке": TASK_TITLES_CANONICAL[4],
    f"{TASK_PREFIX_LEGACY} Обучение нового администратора": TASK_TITLES_CANONICAL[5],
    f"{TASK_PREFIX_LEGACY} Ждём ответ стоматолога-ортодонта": TASK_TITLES_CANONICAL[6],
    f"{TASK_PREFIX_LEGACY} Проверка витрины перед акцией": TASK_TITLES_CANONICAL[7],
    f"{TASK_PREFIX_LEGACY} Согласование макетов с маркетингом": TASK_TITLES_CANONICAL[8],
    f"{TASK_PREFIX_LEGACY} Закрыть модуль гигиены за месяц": TASK_TITLES_CANONICAL[9],
    f"{TASK_PREFIX_LEGACY} Актуализировать FAQ на сайте": TASK_TITLES_CANONICAL[10],
    f"{TASK_PREFIX_LEGACY} Ежемесячная сверка кассы": TASK_TITLES_CANONICAL[11],
    f"{TASK_PREFIX_LEGACY} Перенос старого договора (отменено)": TASK_TITLES_CANONICAL[12],
    **{f"{SHOWCASE_TASK_PREFIX} {t}": t for t in TASK_TITLES_CANONICAL},
}

CAL_TITLE_RU_EN: dict[str, str] = {
    f"{CAL_PREFIX_LEGACY} Планёрка филиала": CAL_TITLES_CANONICAL[0],
    f"{CAL_PREFIX_LEGACY} Разбор NPS и отзывов": CAL_TITLES_CANONICAL[1],
    f"{CAL_PREFIX_LEGACY} Синк с маркетингом": CAL_TITLES_CANONICAL[2],
    f"{CAL_PREFIX_LEGACY} Обучение: новый регламент стерилизации": CAL_TITLES_CANONICAL[3],
    f"{CAL_PREFIX_LEGACY} Сверка склад/витрина": CAL_TITLES_CANONICAL[4],
    f"{CAL_PREFIX_LEGACY} Подготовка к акции выходного дня": CAL_TITLES_CANONICAL[5],
    f"{CAL_PREFIX_LEGACY} Разбор загрузки расписания": CAL_TITLES_CANONICAL[6],
    f"{CAL_PREFIX_LEGACY} Внутренний аудит документов": CAL_TITLES_CANONICAL[7],
    f"{CAL_PREFIX_LEGACY} Собрание по качеству сервиса": CAL_TITLES_CANONICAL[8],
    f"{CAL_PREFIX_LEGACY} IT: обновление ПО на стойке": CAL_TITLES_CANONICAL[9],
    f"{CAL_PREFIX_LEGACY} Финансовая сверка за период": CAL_TITLES_CANONICAL[10],
    f"{CAL_PREFIX_LEGACY} HR: график отпусков": CAL_TITLES_CANONICAL[11],
    f"{CAL_PREFIX_LEGACY} Закупка расходников": CAL_TITLES_CANONICAL[12],
    f"{CAL_PREFIX_LEGACY} Ретроспектива недели": CAL_TITLES_CANONICAL[13],
    **{f"{SHOWCASE_STAFF_CAL_PREFIX} {t}": t for t in CAL_TITLES_CANONICAL},
}

FEED_TITLE_RU_EN: dict[str, str] = {
    f"{FEED_PREFIX_LEGACY} План на неделю": STAFF_FEED_TITLE_WEEK,
    f"{FEED_PREFIX_LEGACY} Сводка NPS и отзывы": STAFF_FEED_TITLE_NPS,
    f"{STAFF_FEED_TITLE_PREFIX} Week plan": STAFF_FEED_TITLE_WEEK,
    f"{STAFF_FEED_TITLE_PREFIX} NPS and reviews digest": STAFF_FEED_TITLE_NPS,
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

STAFF_GENERAL_OPENERS: tuple[str, str] = (
    "Morning — today’s focus is post-visit NPS. Keep the desk survey short.",
    "Done. Tablets are on the desk; I’ll pull the report tonight.",
)

# Old seed lines → current workplace copy (in-place rewrite, no duplicate inserts).
STAFF_CHAT_LINE_REWRITES: dict[str, str] = {
    "Коллеги, доброе утро! Сегодня держим фокус на NPS после приёма — короткий опрос у администратора.": (
        STAFF_GENERAL_OPENERS[0]
    ),
    "Принято. На стойке уже стоят планшеты с формой, вечером снимем сводку в отчётах.": STAFF_GENERAL_OPENERS[1],
    "Morning — keep the post-visit NPS prompt short at the desk.": STAFF_GENERAL_OPENERS[0],
    "Got it. Tablets are on the counter; I’ll pull the digest tonight.": STAFF_GENERAL_OPENERS[1],
    "Ivan has the disk. Anna said she will bring it.": "Noah has the disk. Mary said she will bring it.",
    "If Anna arrives without imaging, hold the surgeon and do exam only.": (
        "If Mary arrives without imaging, hold the surgeon and do exam only."
    ),
    "Keep the landing in English for the GitHub demo path.": "Keep the public landing in English.",
    "Demo path may still be a RU SMS provider — that’s expected.": (
        "If a reminder failed, log it on the booking and retry from Omni."
    ),
    "The SMS adapter in this environment may still point at a regional provider — that’s expected.": (
        "If a reminder failed, log it on the booking and retry from Omni."
    ),
    "Do not publish until legal placeholder pages stay RU-only.": (
        "Do not publish until legal has signed off the landing."
    ),
    "Stories caption was relabelled. Check the vitrine.": (
        "Stories on the vitrine are current — check before the weekend promo."
    ),
    "One review says SMS reminder never arrived. Check Twilio/SMS adapter.": (
        "One review says SMS reminder never arrived. Check the SMS channel."
    ),
    "Don’t promise a channel we haven’t configured in .env.": (
        "Don’t promise a channel that isn’t connected in clinic settings."
    ),
}

# Five staff GROUP rooms × 10 English messages (idempotent by room title).
STAFF_GROUP_THREADS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Front desk vs hygiene column",
        (
            "Hygiene is full 10–13 tomorrow. Who takes waitlist SMS?",
            "I’ll take waitlist. Offer Friday after 16:00 first.",
            "Flag no-shows from yesterday on the CRM card, not in chat.",
            "Done. Two names still have no phone — I’ll ping marketing.",
            "If a patient asks for a same-day fill, check the surgeon column first.",
            "Surgeon has a hole at 14:30 if we move the polish.",
            "Don’t move polish without asking the hygienist.",
            "Agreed. I’ll ask before I touch the grid.",
            "Owner wants a 16:00 huddle on chair utilisation.",
            "I’ll bring the occupancy screenshot. See you then.",
        ),
    ),
    (
        "Implant consults and CT",
        (
            "Two implant consults tomorrow — CT on file for both?",
            "Noah has the disk. Mary said she will bring it.",
            "If Mary arrives without imaging, hold the surgeon and do exam only.",
            "Front desk: arrive 15 minutes early is in the WhatsApp thread.",
            "I claimed the Telegram thread so we don’t double-answer.",
            "Log the outcome on the booking so Finance sees a completed visit.",
            "Membership discount stays on the CRM card — no verbal deals.",
            "Copy. I’ll add a checklist line on the consult template.",
            "Need a signed scan before we close the related Kanban card.",
            "I’ll attach it when the patient leaves.",
        ),
    ),
    (
        "Marketing creatives v2",
        (
            "v2 creatives are in the shared folder. Need owner OK today.",
            "Weekend promo copy still mentions complimentary consult.",
            "Keep the public landing in English.",
            "FAQ on the site is stale — hygiene prices moved last week.",
            "I’ll open a Kanban card for the FAQ refresh.",
            "Do not publish until legal has signed off the landing.",
            "Understood. Promo post body is already English.",
            "Stories on the vitrine are current — check before the weekend promo.",
            "Owner: ship the one-pager for the desk by Friday.",
            "Link goes in team chat, not in patient WhatsApp.",
        ),
    ),
    (
        "NPS and reviews digest",
        (
            "NPS held. Complaints are mostly chair wait time.",
            "Please log actual chair time in CRM, not in a spreadsheet.",
            "Desk survey must stay short — three questions max.",
            "Tablets are on the desk; I’ll pull the report tonight.",
            "Two Google reviews mention the lounge renovation — good.",
            "One review says SMS reminder never arrived. Check the SMS channel.",
            "If a reminder failed, log it on the booking and retry from Omni.",
            "Don’t promise a channel that isn’t connected in clinic settings.",
            "I’ll add a feed comment with the Friday digest plan.",
            "Marketing will publish the desk one-pager after the huddle.",
        ),
    ),
    (
        "Week close and payroll notes",
        (
            "Cash-up is tomorrow morning. Don’t leave open invoices.",
            "Hygiene gift voucher SKU is on the vitrine — confirm stock.",
            "Payroll: flag overtime from Saturday implant block.",
            "I’ll attach the occupancy export to the owner report task.",
            "Cancelled contract migration stays cancelled — don’t reopen.",
            "On-hold Kanban card is waiting on the orthodontist.",
            "If the orthodontist replies, drop it in this room.",
            "Front desk software update is on the staff calendar.",
            "Consumables purchase is approved — don’t double-order.",
            "Weekly retro is Friday 16:00. Bring one improvement, not a list.",
        ),
    ),
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


async def relabel_platform_catalog_en(session: AsyncSession) -> None:
    """English overlay for platform catalog rows (Alembic inserts stay historical)."""
    plans = (await session.scalars(select(PlatformCatalogPlan))).all()
    for plan in plans:
        mapped = CATALOG_PLAN_EN.get(plan.slug)
        if mapped is None:
            continue
        name, description = mapped
        plan.display_name = name
        plan.description = description
    options = (await session.scalars(select(PlatformCatalogOption))).all()
    for option in options:
        mapped_opt = CATALOG_OPTION_EN.get(option.entitlement_key)
        if mapped_opt is None:
            continue
        name, description = mapped_opt
        option.display_name = name
        if description is not None:
            option.description = description
    await session.flush()


def english_prefix_fallback(title: str, legacy_prefix: str, en_prefix: str, exact: dict[str, str]) -> str:
    if title in exact:
        return exact[title]
    for prefix in (legacy_prefix, en_prefix):
        if prefix and title.startswith(prefix):
            rest = title[len(prefix) :].strip()
            return rest if rest else title
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
    staff_pairs = list(spec["admins"]) + list(spec["marketers"])  # type: ignore[arg-type]
    if spec.get("clinicians"):
        staff_pairs = staff_pairs + list(spec["clinicians"])  # type: ignore[arg-type]
    for email, name in staff_pairs:
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
            key = str(spec.get("key") or "")
            if key:
                patient.phone = patient_phone(key, i)
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
                or_(
                    Task.title.like(f"{TASK_PREFIX_LEGACY}%"),
                    Task.title.like(f"{SHOWCASE_TASK_PREFIX}%"),
                    Task.title.like(f"{WINDOW_TASK_PREFIX_LEGACY}%"),
                    Task.title.in_(TASK_TITLES_CANONICAL),
                ),
            )
        )
    ).all()
    for task in tasks:
        raw = task.title or ""
        if raw.startswith(WINDOW_TASK_PREFIX_LEGACY):
            rest = raw[len(WINDOW_TASK_PREFIX_LEGACY) :].strip()
            task.title = rest or raw
        else:
            task.title = english_prefix_fallback(
                task.title, TASK_PREFIX_LEGACY, SHOWCASE_TASK_PREFIX, TASK_TITLE_RU_EN
            )
        if task.title in TASK_TITLES_CANONICAL:
            task.description = "Linked to a real staff member (and a patient when relevant)."
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
                    StaffCalendarEvent.title.like(f"{WINDOW_CAL_PREFIX_LEGACY}%"),
                    StaffCalendarEvent.title.in_(CAL_TITLES_CANONICAL),
                ),
            )
        )
    ).all()
    for ev in events:
        raw = ev.title or ""
        if raw.startswith(WINDOW_CAL_PREFIX_LEGACY):
            rest = raw[len(WINDOW_CAL_PREFIX_LEGACY) :].strip()
            ev.title = rest or raw
        else:
            ev.title = english_prefix_fallback(
                ev.title, CAL_PREFIX_LEGACY, SHOWCASE_STAFF_CAL_PREFIX, CAL_TITLE_RU_EN
            )
        ev.description = "Staff meeting."
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
        STAFF_FEED_TITLE_WEEK: (
            "Reminder: membership discounts go through the CRM card only — no verbal deals at the desk."
        ),
        STAFF_FEED_TITLE_NPS: (
            "NPS held last week; complaints are mostly chair wait time. Please log actual chair time in CRM."
        ),
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
        loc.name = "Main sales point"
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
        if (
            promo.title.startswith(PROMO_PREFIX_LEGACY)
            or promo.title.startswith(PROMO_TITLE_PREFIX)
            or promo.title == PROMO_TITLE_CANONICAL
            or "Бесплатная консультация" in (promo.title or "")
        ):
            promo.title = PROMO_TITLE_CANONICAL
            promo.body = PROMO_BODY_CANONICAL
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
            STAFF_GENERAL_OPENERS[0]
        ),
        "Принято. На стойке уже стоят планшеты с формой, вечером снимем сводку в отчётах.": STAFF_GENERAL_OPENERS[1],
    }
    for msg in existing:
        if msg.body in STAFF_CHAT_LINE_REWRITES:
            msg.body = STAFF_CHAT_LINE_REWRITES[msg.body]
        elif msg.body in ru_to_en:
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


async def _ensure_staff_group_threads(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    admin_ids = list(
        (
            await session.scalars(
                select(AdminUser.id).where(
                    AdminUser.clinic_id == clinic_id,
                    AdminUser.deleted_at.is_(None),
                    AdminUser.employment_status == EMPLOYMENT_ACTIVE,
                )
            )
        ).all()
    )
    if not admin_ids:
        admin_ids = [owner_id]
    now = _utc_naive_wall()
    for topic_index, (suffix, bodies) in enumerate(STAFF_GROUP_THREADS):
        title = suffix
        room = (
            await session.execute(
                select(StaffChatRoom).where(
                    StaffChatRoom.clinic_id == clinic_id,
                    StaffChatRoom.kind == GROUP_ROOM_KIND,
                    StaffChatRoom.title.in_((title, f"{STAFF_GROUP_TITLE_PREFIX_LEGACY}{suffix}")),
                )
            )
        ).scalar_one_or_none()
        if room is None:
            room = StaffChatRoom(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                kind=GROUP_ROOM_KIND,
                title=title,
                created_by_admin_id=owner_id,
            )
            session.add(room)
            await session.flush()
        else:
            room.title = title
        for aid in admin_ids:
            existing_member = await session.get(StaffChatRoomMember, (room.id, aid))
            if existing_member is None:
                session.add(
                    StaffChatRoomMember(
                        room_id=room.id,
                        admin_id=aid,
                        membership_kind=MEMBERSHIP_GROUP,
                    )
                )
        await session.flush()
        existing_msgs = list(
            (
                await session.scalars(
                    select(StaffChatMessage)
                    .where(StaffChatMessage.room_id == room.id)
                    .order_by(StaffChatMessage.created_at.asc())
                )
            ).all()
        )
        for msg in existing_msgs:
            if msg.body in STAFF_CHAT_LINE_REWRITES:
                msg.body = STAFF_CHAT_LINE_REWRITES[msg.body]
            else:
                msg.body = strip_staff_demo_mark(msg.body)
        await session.flush()
        for i, body in enumerate(bodies):
            if i < len(existing_msgs):
                existing_msgs[i].body = body
            else:
                session.add(
                    StaffChatMessage(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        room_id=room.id,
                        author_admin_id=admin_ids[i % len(admin_ids)],
                        body=body,
                        created_at=now - timedelta(hours=topic_index + 1, minutes=90 - i * 7),
                    )
                )
        for extra in existing_msgs[len(bodies) :]:
            await session.delete(extra)
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
                ("in", "Can I add a hygiene visit the same week if a chair opens?"),
                ("out", "If the hygienist column has a hole after the exam, yes. I’ll check and reply here."),
                ("in", "Also, do you still send SMS reminders?"),
                ("out", "Yes — the day before, to this number."),
                ("in", "Perfect. Thank you."),
                ("out", "You’re welcome. Front desk has you flagged."),
            ]
        return [
            ("in", "Hi — can I move my hygiene visit to Friday after 16:00? School pickup ran late."),
            ("out", f"Hi {first} — I’ll check the hygiene column and hold a Friday afternoon chair if one is free."),
            ("in", "Thank you. Same doctor if possible."),
            ("out", "Noted. I’ll confirm in this thread once the slot is locked in the calendar."),
            ("in", "If Friday is full, Saturday morning also works."),
            ("out", "Saturday AM is usually implant block — I’ll only offer it if a hygiene chair is actually free."),
            ("in", "Understood. I’ll wait for your confirm."),
            ("out", "I’ll write back as soon as the grid is updated."),
            ("in", "Do I need to pay anything extra to move?"),
            ("out", "No fee to reschedule this visit. See you once the new slot is locked."),
        ]
    if kind == "WHATSAPP":
        if booking_line:
            return [
                ("in", f"Hello, I have {booking_line}. Do I still need a CT scan?"),
                ("out", f"Yes — please arrive 15 minutes early so we can upload imaging before {booking_line}."),
                ("in", "Got it, I’ll bring the disk from the imaging center."),
                ("out", "Perfect. Front desk will check you in as soon as you arrive."),
                ("in", "Is the visitor lot still behind the building?"),
                ("out", "Yes — use the clinic lot; street spots fill up by 09:00."),
                ("in", "Should I skip breakfast?"),
                ("out", "A light breakfast is fine. Avoid coffee right before imaging if they still need a retake."),
                ("in", "Thanks — see you then."),
                ("out", "See you. Reply here if the disk doesn’t open."),
            ]
        return [
            ("in", "Hello, the implant consult is coming up. Do I still need a CT scan?"),
            ("out", "Yes — please arrive 15 minutes early so we can upload the CT before you see the surgeon."),
            ("in", "Got it, I’ll bring the disk from the imaging center."),
            ("out", "Perfect. Front desk will check you in as soon as you arrive."),
            ("in", "If the disk is unreadable, can we retake in-house?"),
            ("out", "We can refer you the same morning. The surgeon slot then becomes exam-only."),
            ("in", "OK. I’ll come 20 minutes early just in case."),
            ("out", "That’s helpful. We’ll flag the chart."),
            ("in", "Do you take the membership discount on the consult?"),
            ("out", "Membership discounts go on the CRM card — the desk will apply it if you qualify."),
        ]
    if booking_line:
        return [
            ("in", "Do you take new ortho patients this month? Teen, 14."),
            ("out", f"We do. We already have {first} on the book: {booking_line}."),
            ("in", "That’s us — how long is that visit?"),
            ("out", "About 30 minutes — exam and a written plan. See you then."),
            ("in", "Should they wear the current retainer in?"),
            ("out", "Yes — bring whatever they’re wearing now."),
            ("in", "Any forms to fill before we arrive?"),
            ("out", "Medical history on the patient PWA saves time at the desk."),
            ("in", "We’ll do that tonight. Thanks."),
            ("out", "Great. See you at the booked time."),
        ]
    return [
        ("in", "Do you take new ortho patients this month? Teen, 14."),
        ("out", "We do. Dr. Carter has new-patient exams this week — I can hold Tuesday morning or Thursday afternoon."),
        ("in", "Tuesday morning works. How long is the first visit?"),
        ("out", f"About 30 minutes — exam and a written plan. I’ll book {patient_name} as soon as you confirm a slot."),
        ("in", "Please hold Tuesday. We’ll confirm by SMS."),
        ("out", "Holding Tuesday morning. Reply YES and I’ll lock the calendar."),
        ("in", "YES — lock it."),
        ("out", "Locked. Reminder goes out the day before."),
        ("in", "Can a parent sit in?"),
        ("out", "Yes. One adult in the room is fine."),
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


def video_omni_from_id(provider: str, key: str, clinic_id: uuid.UUID) -> str:
    """Stable Omni from_id (not patient phone) so re-seed does not split threads."""
    if provider == "TELEGRAM":
        return f"tg_video_{key}_anna"
    if provider == "WEBCHAT":
        return f"web_video_{key}_maria"
    return f"+7999{clinic_id.int % 10_000_000:07d}"


async def omni_message_by_external_id(
    session: AsyncSession,
    chat_id: uuid.UUID,
    ext_id: str,
) -> OmniMessage | None:
    return (
        await session.execute(
            select(OmniMessage)
            .where(
                OmniMessage.chat_id == chat_id,
                OmniMessage.source_metadata["external_message_id"].as_string() == ext_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()


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
            "name": "Mary Collins",
            "kind": "TELEGRAM",
        },
        {
            "provider": "WHATSAPP",
            "from_id": f"+7999{clinic.id.int % 10_000_000:07d}",
            "name": "Noah Bennett",
            "kind": "WHATSAPP",
        },
        {
            "provider": "WEBCHAT",
            "from_id": f"web_video_{key}_maria",
            "name": "Olivia Chen",
            "kind": "WEBCHAT",
        },
    ]

    for script in scripts:
        provider = str(script["provider"])
        name = str(script["name"])
        patient = await _patient_by_name(session, clinic.id, name)
        from_id = video_omni_from_id(provider, key, clinic.id)
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
        ids: dict[str, str] = {provider_key: from_id}
        if patient is not None:
            ids["patient_id"] = str(patient.id)
        display_phone = (patient.phone.strip() if patient is not None and (patient.phone or "").strip() else None)
        if provider == "WHATSAPP" and display_phone is None:
            display_phone = from_id
        if contact is None:
            contact = OmniContact(
                business_account_id=clinic.id,
                full_name=name,
                primary_phone=display_phone,
                external_ids=ids,
            )
            session.add(contact)
            await session.flush()
        else:
            contact.full_name = name
            merged = dict(contact.external_ids or {})
            merged.update(ids)
            contact.external_ids = merged
            if display_phone:
                contact.primary_phone = display_phone
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
            existing_msg = await omni_message_by_external_id(session, chat.id, ext_id)
            if existing_msg is not None:
                existing_msg.content = text
                continue
            if direction == "in":
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
    """Relabel clinic-scoped demo data and seed EN huddles/omni.

    Platform catalog overlay is **not** applied here (it is global). Callers run
    ``relabel_platform_catalog_en`` once per seed/backfill, not per clinic.
    """
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
    await _ensure_staff_group_threads(session, clinic.id, owner_admin_id)
    await _ensure_omni_dialogues(session, clinic, owner_admin_id)
