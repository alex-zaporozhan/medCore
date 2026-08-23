"""SaaS-style demo layers for multi-tenant showcase clinics (не Alembic).

Заполняет данные для «живой» презентации: organization_id у админов, Commerce (точка + SKU + остатки),
календарь записей пациентов (3 месяца, ~65% слотов), **поток задач + Kanban-доска**, **календарь сотрудников**,
лента (два поста и комментарии), общий чат, витрина. Идемпотентно по маркерам: канонические EN titles,
legacy RU / ``Demo …`` префиксы (после ``showcase_en_video_layer``), ``notes``.

Для БД, где showcase уже накатан старой версией сида (без organization_id у admins):

    poetry run python -m src.scripts.backfill_showcase_saas_extras

Новые установки получают этот слой автоматически из ``seed_multi_tenant_showcase``."""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.task_dto import TASK_STATUSES
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.commerce_document import CommerceDocument
from src.domain.entities.commerce_document_line import CommerceDocumentLine
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.domain.entities.commerce_stock_balance import CommerceStockBalance
from src.domain.entities.commerce_stock_location import CommerceStockLocation
from src.domain.entities.patient import Patient
from src.domain.entities.payment import Payment  # noqa: F401 — metadata: FK bookings.payment_id → payments
from src.domain.entities.product import Product  # noqa: F401 — metadata: FK tasks.inventory_product_id → products
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.staff_chat_message import StaffChatMessage
from src.domain.entities.staff_chat_room import StaffChatRoom
from src.domain.entities.staff_chat_room_member import StaffChatRoomMember
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_event_invitation import StaffCalendarEventInvitation
from src.domain.entities.staff_calendar_event_participant import StaffCalendarEventParticipant
from src.domain.entities.staff_feed_comment import StaffFeedComment
from src.domain.entities.staff_feed_post import StaffFeedPost
from src.domain.entities.story import Story
from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_board import TaskBoard
from src.domain.entities.task_board_column import TaskBoardColumn
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_stream import TaskStream
from src.scripts.showcase_en_video_layer import (
    CAL_TITLES_CANONICAL,
    PROMO_BODY_CANONICAL,
    PROMO_TITLE_CANONICAL,
    PROMO_TITLE_PREFIX as PROMO_TITLE_PREFIX_EN,
    SHOWCASE_STAFF_CAL_PREFIX as SHOWCASE_STAFF_CAL_PREFIX_EN,
    SHOWCASE_TASK_PREFIX as SHOWCASE_TASK_PREFIX_EN,
    STAFF_FEED_TITLE_NPS,
    STAFF_FEED_TITLE_PREFIX as STAFF_FEED_TITLE_PREFIX_EN,
    STAFF_FEED_TITLE_WEEK,
    STAFF_GENERAL_OPENERS,
    TASK_TITLES_CANONICAL,
)

# Совпадает с seed_multi_tenant_showcase.SEED_MARKER — клиники из этого сида.
SHOWCASE_INTENT_NOTES = "seed:multi_tenant_showcase_v1"
DEMO_STOCK_CODE = "SHOWCASE_DEMO_MAIN"
GENERAL_ROOM_KIND = "GENERAL"
MEMBERSHIP_GENERAL = "general"
STAFF_FEED_TITLE_PREFIX = "Демо CRM:"
STAFF_FEED_COMMENT2_BODY = (
    "I’ll publish the front-desk checklist in the knowledge base by Friday and drop the link in team chat."
)
PROMO_TITLE_PREFIX = "Демо витрина:"
SHOWCASE_TASK_PREFIX = "Демо Kanban:"
SHOWCASE_STAFF_CAL_PREFIX = "Демо календарь:"
# Lookup: RU seed + legacy "Demo …" prefixes + canonical workplace titles.
STAFF_FEED_POST1_TITLES = (
    STAFF_FEED_TITLE_WEEK,
    f"{STAFF_FEED_TITLE_PREFIX} План на неделю",
    f"{STAFF_FEED_TITLE_PREFIX_EN} Week plan",
)
STAFF_FEED_POST2_TITLES = (
    STAFF_FEED_TITLE_NPS,
    f"{STAFF_FEED_TITLE_PREFIX} Сводка NPS и отзывы",
    f"{STAFF_FEED_TITLE_PREFIX_EN} NPS and reviews digest",
)
STAFF_FEED_COMMENT2_BODIES = (
    STAFF_FEED_COMMENT2_BODY,
    "Чеклист для стойки выложу в KB до пятницы, ссылку пришлю в общий чат.",
)
# Единый маркер строки в bookings.notes — слой календаря идемпотентен по факту наличия таких записей.
BOOKING_CALENDAR_NOTE = "showcase_calendar_v1"
# Доля занятых слотов 09:00–17:30 (шаг 30 мин) в пределах 60–70%.
SLOT_FILL_RATIO = 0.65
# Сетка как в seed_demo_bookings: последний старт 17:30.
SLOT_STARTS: tuple[time, ...] = (
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
)


def _prev_month_first(today: date) -> date:
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def _next_month_last(today: date) -> date:
    if today.month == 12:
        nm_first = date(today.year + 1, 1, 1)
    else:
        nm_first = date(today.year, today.month + 1, 1)
    if nm_first.month == 12:
        return date(nm_first.year + 1, 1, 1) - timedelta(days=1)
    return date(nm_first.year, nm_first.month + 1, 1) - timedelta(days=1)


def _stable_slot_fill(
    clinic_id: uuid.UUID,
    doctor_id: uuid.UUID,
    day: date,
    slot_t: time,
    *,
    ratio: float = SLOT_FILL_RATIO,
) -> bool:
    raw = f"fill:{clinic_id}:{doctor_id}:{day.isoformat()}:{slot_t.isoformat(timespec='minutes')}".encode()
    h = int(hashlib.sha256(raw).hexdigest(), 16)
    return (h % 10_000) / 10_000.0 < ratio


async def backfill_admin_organization_ids(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    """admins.organization_id из клиники (исправляет баннер «Нет организации» в Commerce)."""
    clinic = await session.get(Clinic, clinic_id)
    if clinic is None or clinic.organization_id is None:
        return
    await session.execute(
        update(AdminUser)
        .where(
            AdminUser.clinic_id == clinic_id,
            AdminUser.organization_id.is_(None),
            AdminUser.deleted_at.is_(None),
        )
        .values(organization_id=clinic.organization_id)
    )


async def _ensure_commerce_demo(session: AsyncSession, org_id: uuid.UUID, clinic_id: uuid.UUID) -> None:
    res = await session.execute(
        select(CommerceStockLocation.id).where(
            CommerceStockLocation.clinic_id == clinic_id,
            CommerceStockLocation.code == DEMO_STOCK_CODE,
        )
    )
    if res.scalar_one_or_none() is not None:
        return

    loc = CommerceStockLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        clinic_id=clinic_id,
        name="Основная точка продаж (демо)",
        code=DEMO_STOCK_CODE,
        is_default=True,
    )
    session.add(loc)
    await session.flush()

    items_spec = [
        ("WH-001", "Блокнот с логотипом клиники", Decimal("120")),
        ("WH-002", "Ополаскиватель профилактический, 250 мл", Decimal("45")),
        ("SRV-001", "Подарочный сертификат на гигиену", Decimal("1")),
    ]
    items: list[CommerceNomenclatureItem] = []
    for sku, name, qty in items_spec:
        it = CommerceNomenclatureItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            clinic_id=clinic_id,
            sku=sku,
            name=name,
            unit="pcs",
            is_active=True,
        )
        session.add(it)
        items.append(it)
    await session.flush()

    for it, (_, _, qty) in zip(items, items_spec, strict=True):
        session.add(
            CommerceStockBalance(
                id=uuid.uuid4(),
                organization_id=org_id,
                clinic_id=clinic_id,
                stock_location_id=loc.id,
                nomenclature_item_id=it.id,
                quantity=qty,
            )
        )
    await session.flush()

    doc = CommerceDocument(
        id=uuid.uuid4(),
        organization_id=org_id,
        clinic_id=clinic_id,
        stock_location_id=loc.id,
        to_stock_location_id=None,
        doc_kind="goods_in",
        remark="Начальные остатки для демо-презентации Commerce",
    )
    session.add(doc)
    await session.flush()
    for it, (_, _, qty) in zip(items, items_spec, strict=True):
        session.add(
            CommerceDocumentLine(
                id=uuid.uuid4(),
                organization_id=org_id,
                clinic_id=clinic_id,
                document_id=doc.id,
                nomenclature_item_id=it.id,
                quantity=qty,
            )
        )


async def _ensure_showcase_calendar_bookings(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    """Календарь: прошлый + текущий + следующий месяц, будни, ~65% слотов; только связки service_doctors."""
    marker_count = await session.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.clinic_id == clinic_id,
            Booking.notes == BOOKING_CALENDAR_NOTE,
            Booking.deleted_at.is_(None),
        )
    )
    if marker_count and int(marker_count) > 0:
        return

    occ_rows = await session.execute(
        select(Booking.doctor_id, Booking.appointment_date, Booking.appointment_time).where(
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
        )
    )
    # Любая существующая запись на слот (в т.ч. completed) — не пересекаем: так нет конфликта с индексом и старым сидом.
    occupied_slot: set[tuple[uuid.UUID, date, time]] = {(did, ad, at) for did, ad, at in occ_rows}

    sd_rows = await session.execute(
        select(ServiceDoctor.doctor_id, ServiceDoctor.service_id)
        .join(Doctor, Doctor.id == ServiceDoctor.doctor_id)
        .join(Service, Service.id == ServiceDoctor.service_id)
        .where(
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
            Service.clinic_id == clinic_id,
            Service.deleted_at.is_(None),
            ServiceDoctor.is_active.is_(True),
        )
    )
    doctor_services: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for did, sid in sd_rows:
        doctor_services[did].append(sid)

    patient_rows = await session.scalars(
        select(Patient.id).where(
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    patient_ids = list(patient_rows.all())
    if not patient_ids or not doctor_services:
        return

    today = date.today()
    range_start = _prev_month_first(today)
    range_end = _next_month_last(today)

    added = 0
    d = range_start
    while d <= range_end:
        if d.weekday() < 5:
            for doc_id, svc_ids in doctor_services.items():
                if not svc_ids:
                    continue
                for slot_t in SLOT_STARTS:
                    if (doc_id, d, slot_t) in occupied_slot:
                        continue
                    if not _stable_slot_fill(clinic_id, doc_id, d, slot_t):
                        continue
                    raw_p = f"patient:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}".encode()
                    patient_id = patient_ids[int(hashlib.sha256(raw_p).hexdigest(), 16) % len(patient_ids)]
                    raw_s = f"service:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}".encode()
                    service_id = svc_ids[int(hashlib.sha256(raw_s).hexdigest(), 16) % len(svc_ids)]

                    if d < today:
                        st = BookingStatus.COMPLETED.value
                        erp_ok = True
                    elif d == today:
                        st = BookingStatus.CONFIRMED.value
                        erp_ok = False
                    else:
                        raw_st = f"st:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}".encode()
                        st = (
                            BookingStatus.PENDING.value
                            if (int(hashlib.sha256(raw_st).hexdigest(), 16) % 2) == 0
                            else BookingStatus.CONFIRMED.value
                        )
                        erp_ok = False

                    b = Booking(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        patient_id=patient_id,
                        doctor_id=doc_id,
                        service_id=service_id,
                        appointment_date=d,
                        appointment_time=slot_t,
                        status=st,
                        prepayment_amount=Decimal("0"),
                        erp_processed=erp_ok,
                        erp_error_code=None,
                        notes=BOOKING_CALENDAR_NOTE,
                    )
                    session.add(b)
                    occupied_slot.add((doc_id, d, slot_t))
                    added += 1
                    if added % 150 == 0:
                        await session.flush()
        d += timedelta(days=1)

    if added:
        await session.flush()


def _utc_aware() -> datetime:
    return datetime.now(timezone.utc)


def _utc_naive_wall() -> datetime:
    """UTC instant as naive datetime for columns typed TIMESTAMP WITHOUT TIME ZONE (asyncpg)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _ensure_task_stream_general(session: AsyncSession, clinic_id: uuid.UUID) -> TaskStream:
    res = await session.execute(
        select(TaskStream).where(
            TaskStream.clinic_id == clinic_id,
            TaskStream.slug == "general",
            TaskStream.is_archived.is_(False),
        )
    )
    ts = res.scalar_one_or_none()
    if ts is not None:
        return ts
    ts = TaskStream(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Общее",
        slug="general",
        sort_order=0,
        is_archived=False,
        theme={},
    )
    session.add(ts)
    await session.flush()
    return ts


async def _ensure_clinic_wide_task_board(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    res = await session.execute(
        select(TaskBoard.id).where(
            TaskBoard.clinic_id == clinic_id,
            TaskBoard.kind == "clinic_wide",
            TaskBoard.owner_admin_id.is_(None),
        )
    )
    if res.scalar_one_or_none() is not None:
        return
    board = TaskBoard(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Основная",
        kind="clinic_wide",
        owner_admin_id=None,
    )
    session.add(board)
    await session.flush()
    for i, st in enumerate(TASK_STATUSES, start=1):
        session.add(
            TaskBoardColumn(
                id=uuid.uuid4(),
                board_id=board.id,
                sort_order=i,
                mapped_status=st,
                label=None,
            )
        )
    await session.flush()


async def _ensure_showcase_kanban_tasks(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    stream_id: uuid.UUID,
    admin_ids: list[uuid.UUID],
    owner_admin_id: uuid.UUID,
) -> uuid.UUID | None:
    """Задачи по колонкам Kanban + комментарии; первая задача — для связи с календарём сотрудника."""
    task_prefix_filter = or_(
        Task.title.like(f"{SHOWCASE_TASK_PREFIX}%"),
        Task.title.like(f"{SHOWCASE_TASK_PREFIX_EN}%"),
        Task.title.in_(TASK_TITLES_CANONICAL),
    )
    marker = await session.scalar(
        select(func.count()).select_from(Task).where(Task.clinic_id == clinic_id, task_prefix_filter)
    )
    if marker and int(marker) > 0:
        first = await session.scalar(
            select(Task.id)
            .where(Task.clinic_id == clinic_id, task_prefix_filter)
            .order_by(Task.created_at.asc())
            .limit(1)
        )
        return first

    if not admin_ids:
        admin_ids = [owner_admin_id]

    booking_id = await session.scalar(
        select(Booking.id).where(
            Booking.clinic_id == clinic_id,
            Booking.notes == BOOKING_CALENDAR_NOTE,
            Booking.deleted_at.is_(None),
        ).limit(1)
    )
    patient_ids = (
        await session.scalars(
            select(Patient.id).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)).limit(5)
        )
    ).all()
    pid = patient_ids[0] if patient_ids else None

    now = _utc_aware()

    defs: list[tuple[str, str, str, int, uuid.UUID | None, bool, datetime | None]] = [
        (TASK_TITLES_CANONICAL[0], "open", "high", 0, None, False, None),
        (TASK_TITLES_CANONICAL[1], "open", "urgent", 1, None, False, now + timedelta(days=1)),
        (TASK_TITLES_CANONICAL[2], "open", "medium", 2, None, False, now + timedelta(days=3)),
        (TASK_TITLES_CANONICAL[3], "in_progress", "high", 0, pid, False, now + timedelta(days=2)),
        (TASK_TITLES_CANONICAL[4], "in_progress", "medium", 1, None, False, None),
        (TASK_TITLES_CANONICAL[5], "in_progress", "low", 2, None, False, now + timedelta(days=5)),
        (TASK_TITLES_CANONICAL[6], "on_hold", "medium", 0, None, False, None),
        (TASK_TITLES_CANONICAL[7], "review", "high", 1, None, False, now + timedelta(days=1)),
        (TASK_TITLES_CANONICAL[8], "review", "medium", 2, None, False, None),
        (TASK_TITLES_CANONICAL[9], "done", "medium", 0, pid, True, None),
        (TASK_TITLES_CANONICAL[10], "done", "low", 1, None, True, None),
        (TASK_TITLES_CANONICAL[11], "done", "high", 2, None, True, None),
        (TASK_TITLES_CANONICAL[12], "cancelled", "low", 0, None, False, None),
    ]

    first_id: uuid.UUID | None = None
    created_ids: list[uuid.UUID] = []
    for rank, (title, status, priority, aidx, patient_id, done_chk, due) in enumerate(defs, start=1):
        aid = admin_ids[aidx % len(admin_ids)]
        completed_at = (now - timedelta(days=rank % 4 + 1)) if status == "done" else None
        tid = uuid.uuid4()
        if first_id is None:
            first_id = tid
        t = Task(
            id=tid,
            clinic_id=clinic_id,
            stream_id=stream_id,
            title=title,
            description="Linked to a real staff member (and a patient when relevant).",
            status=status,
            priority=priority,
            creator_id=owner_admin_id,
            assignee_id=aid,
            role_assignee=None,
            due_at=due,
            completed_at=completed_at,
            booking_id=booking_id if rank == 1 and booking_id else None,
            patient_id=patient_id,
            lead_id=None,
            source="manual",
            rank=1000 + rank * 10,
            blocked=False,
            checklist_done=done_chk,
            updated_by_admin_id=owner_admin_id,
        )
        session.add(t)
        session.add(TaskAssignee(task_id=tid, admin_id=aid))
        created_ids.append(tid)
    await session.flush()

    comment_pairs = [
        (created_ids[0], admin_ids[1 % len(admin_ids)], "Picked this up — status by end of day."),
        (created_ids[1], owner_admin_id, "I’ll attach the no-show list to the report."),
        (created_ids[3], admin_ids[2 % len(admin_ids)], "Need the signed scan from the patient before I can close this."),
        (created_ids[7], owner_admin_id, "Marketing sent v2 creatives — waiting on final OK."),
    ]
    for task_id, author_id, text in comment_pairs:
        session.add(TaskComment(id=uuid.uuid4(), task_id=task_id, author_id=author_id, text=text))
    await session.flush()
    return first_id


async def _calendar_slot_free(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
) -> bool:
    cnt = await session.scalar(
        select(func.count())
        .select_from(StaffCalendarEvent)
        .where(
            StaffCalendarEvent.clinic_id == clinic_id,
            StaffCalendarEvent.starts_at < ends_at,
            StaffCalendarEvent.ends_at > starts_at,
        )
    )
    return int(cnt or 0) == 0


async def _ensure_showcase_staff_calendar_events(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    owner_admin_id: uuid.UUID,
    participant_admin_ids: list[uuid.UUID],
    linked_task_id: uuid.UUID | None,
) -> None:
    """Совещания в календаре сотрудника: без пересечений (правило домена), участники + ack приглашений."""
    existing = await session.scalar(
        select(func.count())
        .select_from(StaffCalendarEvent)
        .where(
            StaffCalendarEvent.clinic_id == clinic_id,
            or_(
                StaffCalendarEvent.title.like(f"{SHOWCASE_STAFF_CAL_PREFIX}%"),
                StaffCalendarEvent.title.like(f"{SHOWCASE_STAFF_CAL_PREFIX_EN}%"),
                StaffCalendarEvent.title.in_(CAL_TITLES_CANONICAL),
            ),
        )
    )
    if existing and int(existing) > 0:
        return

    parts = list(dict.fromkeys(pid for pid in participant_admin_ids if pid))
    if owner_admin_id not in parts:
        parts.insert(0, owner_admin_id)
    if not parts:
        parts = [owner_admin_id]

    today = date.today()
    range_start = _prev_month_first(today)
    range_end = _next_month_last(today)
    weekdays: list[date] = []
    d = range_start
    while d <= range_end:
        if d.weekday() < 5:
            weekdays.append(d)
        d += timedelta(days=1)

    titles = list(CAL_TITLES_CANONICAL)

    ack_now = _utc_naive_wall()
    hour_slots = [9, 11, 14, 16]
    idx = 0
    for day in weekdays:
        if idx >= len(titles):
            break
        placed = False
        for h in hour_slots:
            # Columns are TIMESTAMP WITHOUT TIME ZONE; asyncpg rejects tz-aware binds.
            starts_at = datetime(day.year, day.month, day.day, h, 0, 0)
            ends_at = starts_at + timedelta(minutes=50)
            if not await _calendar_slot_free(session, clinic_id, starts_at, ends_at):
                continue
            ev_id = uuid.uuid4()
            task_link = linked_task_id if idx == 0 else None
            ev = StaffCalendarEvent(
                id=ev_id,
                clinic_id=clinic_id,
                title=titles[idx],
                description="Staff meeting.",
                starts_at=starts_at,
                ends_at=ends_at,
                all_day=False,
                created_by_admin_id=owner_admin_id,
                task_id=task_link,
                reminder_minutes_before=None,
            )
            session.add(ev)
            await session.flush()
            for pid in parts:
                session.add(StaffCalendarEventParticipant(event_id=ev_id, admin_id=pid))
                session.add(
                    StaffCalendarEventInvitation(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        event_id=ev_id,
                        invitee_admin_id=pid,
                        acknowledged_at=ack_now,
                    )
                )
            await session.flush()
            idx += 1
            placed = True
            break
        if not placed:
            continue


async def _ensure_staff_general_chat(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    owner_id: uuid.UUID,
    second_speaker_id: uuid.UUID,
) -> None:
    res = await session.execute(
        select(StaffChatRoom).where(
            StaffChatRoom.clinic_id == clinic_id,
            StaffChatRoom.kind == GENERAL_ROOM_KIND,
        )
    )
    room = res.scalar_one_or_none()
    if room is None:
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=GENERAL_ROOM_KIND,
            title="Team chat",
            created_by_admin_id=owner_id,
        )
        session.add(room)
        await session.flush()

    admin_ids = (
        await session.scalars(
            select(AdminUser.id).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            )
        )
    ).all()
    for aid in admin_ids:
        existing = await session.get(StaffChatRoomMember, (room.id, aid))
        if existing is None:
            session.add(
                StaffChatRoomMember(
                    room_id=room.id,
                    admin_id=aid,
                    membership_kind=MEMBERSHIP_GENERAL,
                )
            )
    await session.flush()

    cnt = await session.scalar(
        select(func.count()).select_from(StaffChatMessage).where(StaffChatMessage.room_id == room.id)
    )
    if int(cnt or 0) >= 2:
        return

    now = _utc_naive_wall()
    lines = [
        (owner_id, STAFF_GENERAL_OPENERS[0]),
        (second_speaker_id, STAFF_GENERAL_OPENERS[1]),
    ]
    for i, (author, body) in enumerate(lines):
        session.add(
            StaffChatMessage(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                room_id=room.id,
                author_admin_id=author,
                body=body,
                created_at=now - timedelta(minutes=40 - i * 12),
            )
        )


async def _ensure_staff_feed(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    owner_id: uuid.UUID,
    comment_author_id: uuid.UUID,
) -> None:
    post1_title = STAFF_FEED_POST1_TITLES[0]
    p1 = (
        await session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.title.in_(STAFF_FEED_POST1_TITLES),
                StaffFeedPost.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if p1 is None:
        p1 = StaffFeedPost(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            author_admin_id=owner_id,
            title=post1_title,
            body=(
                "Reminder: membership discounts go through the CRM card only — no verbal deals at the desk."
            ),
            is_announcement=False,
            priority_level="normal",
            requires_ack=False,
            audience_roles=["owner", "admin", "manager"],
            audience_admin_ids=[],
        )
        session.add(p1)
        await session.flush()
        session.add(
            StaffFeedComment(
                id=uuid.uuid4(),
                post_id=p1.id,
                parent_comment_id=None,
                author_admin_id=comment_author_id,
                body="Logged in the huddle. Marketing will ship a one-pager for the front desk.",
            )
        )
        await session.flush()

    c2_exists = await session.scalar(
        select(func.count())
        .select_from(StaffFeedComment)
        .where(StaffFeedComment.post_id == p1.id, StaffFeedComment.body.in_(STAFF_FEED_COMMENT2_BODIES))
    )
    if not c2_exists:
        session.add(
            StaffFeedComment(
                id=uuid.uuid4(),
                post_id=p1.id,
                parent_comment_id=None,
                author_admin_id=owner_id,
                body=STAFF_FEED_COMMENT2_BODY,
            )
        )
        await session.flush()

    p2 = (
        await session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.title.in_(STAFF_FEED_POST2_TITLES),
                StaffFeedPost.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if p2 is None:
        p2 = StaffFeedPost(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            author_admin_id=comment_author_id,
            title=STAFF_FEED_POST2_TITLES[0],
            body=(
                "NPS held last week; complaints are mostly chair wait time. Please log actual chair time in CRM."
            ),
            is_announcement=False,
            priority_level="normal",
            requires_ack=False,
            audience_roles=["owner", "admin", "manager"],
            audience_admin_ids=[],
        )
        session.add(p2)
        await session.flush()
        session.add(
            StaffFeedComment(
                id=uuid.uuid4(),
                post_id=p2.id,
                parent_comment_id=None,
                author_admin_id=owner_id,
                body="Great — I’ll post the digest in the knowledge base on Friday and ping team chat.",
            )
        )
        await session.flush()


async def _ensure_promo_and_story(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    res = await session.execute(
        select(PromoPost.id)
        .where(
            PromoPost.clinic_id == clinic_id,
            or_(
                PromoPost.title.like(f"{PROMO_TITLE_PREFIX}%"),
                PromoPost.title.like(f"{PROMO_TITLE_PREFIX_EN}%"),
                PromoPost.title == PROMO_TITLE_CANONICAL,
            ),
        )
        .limit(1)
    )
    if res.scalar_one_or_none() is None:
        now = _utc_naive_wall()
        session.add(
            PromoPost(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                title=PROMO_TITLE_CANONICAL,
                body=PROMO_BODY_CANONICAL,
                is_published=True,
                published_at=now - timedelta(days=2),
            )
        )

    st = await session.scalar(select(func.count()).select_from(Story).where(Story.clinic_id == clinic_id))
    if int(st or 0) == 0:
        session.add(
            Story(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                media_type="image",
                media_url="https://placehold.co/360x640/e2e8f0/1e293b?text=Smile",
                caption="New lounge for patients — peek at the renovation before we open.",
                order_index=0,
                expires_at=_utc_naive_wall() + timedelta(days=14),
            )
        )


async def apply_showcase_saas_extras(
    session: AsyncSession,
    *,
    clinic: Clinic,
    owner_admin_id: uuid.UUID,
) -> None:
    """Идемпотентно добавить демо-слой для одной клиники showcase."""
    if clinic.organization_id is None:
        return
    org_id = clinic.organization_id
    await backfill_admin_organization_ids(session, clinic.id)

    res = await session.execute(
        select(AdminUser.id)
        .where(
            AdminUser.clinic_id == clinic.id,
            AdminUser.id != owner_admin_id,
            AdminUser.deleted_at.is_(None),
        )
        .limit(1)
    )
    other_id = res.scalar_one_or_none() or owner_admin_id

    admin_ids_ordered = list(
        (
            await session.scalars(
                select(AdminUser.id).where(
                    AdminUser.clinic_id == clinic.id,
                    AdminUser.deleted_at.is_(None),
                ).order_by(AdminUser.email.asc())
            )
        ).all()
    )
    if not admin_ids_ordered:
        admin_ids_ordered = [owner_admin_id]

    await _ensure_commerce_demo(session, org_id, clinic.id)
    await _ensure_showcase_calendar_bookings(session, clinic.id)

    stream = await _ensure_task_stream_general(session, clinic.id)
    await _ensure_clinic_wide_task_board(session, clinic.id)
    linked_task_id = await _ensure_showcase_kanban_tasks(
        session,
        clinic.id,
        stream_id=stream.id,
        admin_ids=admin_ids_ordered,
        owner_admin_id=owner_admin_id,
    )
    await _ensure_showcase_staff_calendar_events(
        session,
        clinic.id,
        owner_admin_id=owner_admin_id,
        participant_admin_ids=[owner_admin_id, other_id],
        linked_task_id=linked_task_id,
    )

    await _ensure_staff_general_chat(session, clinic.id, owner_admin_id, other_id)
    await _ensure_staff_feed(session, clinic.id, owner_admin_id, other_id)
    await _ensure_promo_and_story(session, clinic.id)


async def clear_schedule_cache_best_effort() -> None:
    """Сброс Redis-кэша расписания после массовых вставок записей (если Redis доступен)."""
    try:
        from src.infrastructure.database.redis_client import get_redis

        redis = await get_redis()
        keys: list[bytes | str] = []
        async for k in redis.scan_iter("schedule:*"):
            keys.append(k)
        if keys:
            await redis.delete(*keys)
    except Exception:
        return


async def list_showcase_clinic_ids(session: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]]:
    """(organization_id, clinic_id, owner_admin_id provisioned) для клиник showcase."""
    rows = (
        await session.execute(
            select(Clinic.organization_id, Clinic.id, PlatformSignupIntent.provisioned_admin_id)
            .join(PlatformSignupIntent, PlatformSignupIntent.organization_id == Clinic.organization_id)
            .where(
                PlatformSignupIntent.notes == SHOWCASE_INTENT_NOTES,
                Clinic.organization_id.isnot(None),
                Clinic.deleted_at.is_(None),
            )
        )
    ).all()
    out: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []
    for org_id, clinic_id, prov_admin in rows:
        if org_id is None or clinic_id is None or prov_admin is None:
            continue
        out.append((org_id, clinic_id, prov_admin))
    return out
