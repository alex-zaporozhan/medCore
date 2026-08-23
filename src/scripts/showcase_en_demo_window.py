"""English ±14-day demo window on multi-tenant showcase (not Alembic).

Schema stays in Alembic. This layer is progressive seed data after
``seed_multi_tenant_showcase`` + extras + ``showcase_en_video_layer``.

Covers a rolling two weeks back and two weeks forward: denser chair calendar,
Kanban due dates, staff meetings, patient Omni threads, a staff huddle, and a
doctor-role login per clinic.

Idempotent. Re-run via ``seed_multi_tenant_showcase`` or
``backfill_showcase_saas_extras``.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from passlib.hash import pbkdf2_sha256
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.domain.entities.patient import Patient
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_event_invitation import StaffCalendarEventInvitation
from src.domain.entities.staff_calendar_event_participant import StaffCalendarEventParticipant
from src.domain.entities.staff_chat_message import StaffChatMessage
from src.domain.entities.staff_chat_room import StaffChatRoom
from src.domain.entities.staff_chat_room_member import StaffChatRoomMember
from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.task_stream import TaskStream
from src.scripts.seed_rbac_baseline import ensure_user_role_by_code
from src.scripts.showcase_en_catalog import (
    HUDDLE_TITLE,
    HUDDLE_TITLE_LEGACY,
    ORG_SPECS,
    SHOWCASE_PASSWORD,
    WINDOW_CAL_PREFIX_LEGACY,
    WINDOW_TASK_PREFIX_LEGACY,
)
from src.scripts.showcase_en_video_layer import (
    GROUP_ROOM_KIND,
    MEMBERSHIP_GROUP,
    _decorate_channel,
    _find_omni_contact,
    _patient_by_name,
    _spec_for_clinic,
    _utc_naive_wall,
    omni_message_by_external_id,
)
from src.scripts.showcase_saas_extras import BOOKING_CALENDAR_NOTE, SLOT_STARTS

WINDOW_DAYS = 14
WINDOW_FILL_RATIO = 0.88
BOOKING_WINDOW_NOTE = "en_demo_window_v1"
TASK_PREFIX_LEGACY = WINDOW_TASK_PREFIX_LEGACY
CAL_PREFIX_LEGACY = WINDOW_CAL_PREFIX_LEGACY
SALES_STREAM_SLUG = "sales"
OMNI_META = "en_demo_window_v1"
WINDOW_HOUR_SLOTS = (12, 15, 17)
WINDOW_SLOT_MINUTES = {12: 30, 15: 15, 17: 15}

WINDOW_MEETINGS: tuple[str, ...] = (
    "Morning desk briefing",
    "Hygiene column load review",
    "No-show callbacks",
    "Implant consult prep",
    "Owner / finance 15-minute",
    "Marketing creatives sign-off",
    "Sterilization SOP recap",
    "Weekend promo staffing",
    "Ortho new-patient intake",
    "Weekly retro (ops)",
)

WINDOW_TASKS: tuple[tuple[str, str, str, str, int, bool, bool, int], ...] = (
    # suffix, status, priority, stream, due_offset_days, checklist, blocked, comment_index
    ("Call yesterday’s no-shows before 11:00", "open", "urgent", "general", -1, False, False, 0),
    ("Confirm tomorrow’s implant CT uploads", "open", "high", "general", 1, False, False, 1),
    ("Fill Friday hygiene holes from waitlist", "in_progress", "high", "sales", 2, False, False, 2),
    ("Owner report: two-week chair utilisation", "in_progress", "medium", "general", 3, False, False, -1),
    ("Membership discount — waiting on signed scan", "on_hold", "medium", "sales", 4, False, True, 3),
    ("Front-desk checklist live on tablets", "review", "medium", "general", 0, False, False, -1),
    ("Close last week’s hygiene module", "done", "medium", "general", -3, True, False, -1),
    ("Cash-up for the previous seven days", "done", "high", "general", -2, True, False, -1),
    ("Cancelled: migrate paper recall list", "cancelled", "low", "general", -10, False, False, -1),
    ("Approve weekend promo SMS copy", "review", "high", "sales", 5, False, False, 4),
)

WINDOW_TASK_TITLES: tuple[str, ...] = tuple(row[0] for row in WINDOW_TASKS)

TASK_COMMENTS: tuple[str, ...] = (
    "Two numbers bounced — I’ll try WhatsApp after lunch.",
    "Disk from the imaging centre is on the chart for 09:30.",
    "Waitlist SMS went out; three YES so far.",
    "Patient promised the scan by Thursday. Do not close without it.",
    "Legal-safe version is in the marketing huddle — waiting on owner OK.",
)

HUDDLE_BODIES: tuple[str, ...] = (
    "Two-week window is on the board: past no-shows are flagged, next 14 days denser on purpose.",
    "Practitioner logins are on the doctor-role accounts: tasks, medical chart, staff chat — not payroll, CRM, or Omni inbox.",
    "Omni: complaint + reschedule + confirm-tomorrow threads are real patients, not AI.",
    "Kanban Sales stream is membership and promo. General is ops.",
    "If a slot shows completed in the past, Finance can treat it as a finished visit.",
    "Today’s in-progress chairs should match who is actually in the room.",
    "Names on the board match the patient chart — don’t invent a second language column.",
    "Re-running the seed must not duplicate this huddle.",
)

OMNI_SCRIPTS: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "TELEGRAM",
        "Liam Brooks",
        "complaint",
        (
            ("in", "The wait after check-in was 40 minutes yesterday. That’s not OK."),
            ("out", "You’re right — that’s over our 15-minute chair-wait target. I’ve logged it on the visit."),
            ("in", "Will someone call me, or is this chat the follow-up?"),
            ("out", "This thread is the follow-up. The owner sees the NPS flag today."),
            ("in", "Fine. I’ll still come for the filling next week."),
            ("out", "We’ll hold that chair. Reply here if you want a later slot."),
        ),
    ),
    (
        "WHATSAPP",
        "Sophie Harper",
        "noshow",
        (
            ("in", "Sorry I missed Tuesday. Can we put me back this week?"),
            ("out", "We marked Tuesday as no-show so the chair could be offered. I can hold Thursday 16:30 hygiene."),
            ("in", "Thursday 16:30 works."),
            ("out", "Locked. A reminder goes out the day before. Please arrive 10 minutes early."),
        ),
    ),
    (
        "WEBCHAT",
        "Ethan Baker",
        "confirm",
        (
            ("in", "Just confirming I’m still on the book tomorrow morning."),
            ("out", "Yes — you are confirmed. Bring any new X-rays on a disk if you have them."),
            ("in", "Will do. Parking same as last time?"),
            ("out", "Clinic lot behind the building. See you tomorrow."),
        ),
    ),
)


def window_bounds(today: date | None = None) -> tuple[date, date]:
    day = today or date.today()
    return day - timedelta(days=WINDOW_DAYS), day + timedelta(days=WINDOW_DAYS)


def meeting_anchor_days(today: date, n: int = 10) -> list[date]:
    """Split staff meetings across the past and future halves of the window."""
    start, end = window_bounds(today)
    weekdays: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            weekdays.append(d)
        d += timedelta(days=1)
    past = [x for x in weekdays if x < today]
    future = [x for x in weekdays if x >= today]
    n_past = n // 2
    n_future = n - n_past
    return past[-n_past:] + future[:n_future]


def _stable_unit(raw: str) -> float:
    h = int(hashlib.sha256(raw.encode()).hexdigest(), 16)
    return (h % 10_000) / 10_000.0


def window_booking_status(day: date, today: date, clinic_id: uuid.UUID, doctor_id: uuid.UUID, slot_t: time) -> str:
    """Deterministic mix for the demo window (English product tour)."""
    key = f"wst:{clinic_id}:{doctor_id}:{day.isoformat()}:{slot_t.isoformat(timespec='minutes')}"
    roll = _stable_unit(key)
    if day < today:
        if roll < 0.08:
            return BookingStatus.NO_SHOW.value
        if roll < 0.13:
            return BookingStatus.CANCELED_BY_PATIENT.value
        return BookingStatus.COMPLETED.value
    if day == today:
        # One live chair per doctor (09:00) — not every morning slot in_progress.
        if slot_t == time(9, 0):
            return BookingStatus.IN_PROGRESS.value
        if roll < 0.25:
            return BookingStatus.REGISTERED.value
        return BookingStatus.CONFIRMED.value
    if roll < 0.45:
        return BookingStatus.PENDING.value
    return BookingStatus.CONFIRMED.value


def _utc_aware() -> datetime:
    return datetime.now(timezone.utc)


async def _calendar_slot_free(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(func.count()).select_from(StaffCalendarEvent).where(
        StaffCalendarEvent.clinic_id == clinic_id,
        StaffCalendarEvent.starts_at < ends_at,
        StaffCalendarEvent.ends_at > starts_at,
    )
    if exclude_id is not None:
        stmt = stmt.where(StaffCalendarEvent.id != exclude_id)
    cnt = await session.scalar(stmt)
    return int(cnt or 0) == 0


async def _ensure_doctor_logins(
    session: AsyncSession,
    clinic: Clinic,
) -> None:
    spec = await _spec_for_clinic(session, clinic)
    if spec is None or clinic.organization_id is None:
        return
    clinicians = spec.get("clinicians")
    if not isinstance(clinicians, list):
        return
    for email, full_name in clinicians:
        existing = (
            await session.execute(
                select(AdminUser).where(AdminUser.email == str(email).strip().lower())
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.clinic_id != clinic.id:
                continue
            existing.full_name = str(full_name)
            await ensure_user_role_by_code(
                session, admin_id=existing.id, clinic_id=clinic.id, role_code="doctor"
            )
            continue
        user = AdminUser(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            organization_id=clinic.organization_id,
            email=str(email).strip().lower(),
            password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
            full_name=str(full_name),
        )
        session.add(user)
        await session.flush()
        await ensure_user_role_by_code(
            session, admin_id=user.id, clinic_id=clinic.id, role_code="doctor"
        )


async def _ensure_sales_stream(session: AsyncSession, clinic_id: uuid.UUID) -> TaskStream:
    row = (
        await session.execute(
            select(TaskStream).where(
                TaskStream.clinic_id == clinic_id,
                TaskStream.slug == SALES_STREAM_SLUG,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        row.name = "Sales"
        row.is_archived = False
        if row.sort_order == 0:
            row.sort_order = 1
        return row
    row = TaskStream(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Sales",
        slug=SALES_STREAM_SLUG,
        sort_order=1,
        is_archived=False,
        theme={"page_tint": "subtle_amber", "mantine_color": "orange"},
    )
    session.add(row)
    await session.flush()
    return row


async def _remix_and_fill_bookings(session: AsyncSession, clinic_id: uuid.UUID, today: date) -> None:
    start, end = window_bounds(today)
    existing = (
        await session.scalars(
            select(Booking).where(
                Booking.clinic_id == clinic_id,
                Booking.deleted_at.is_(None),
                Booking.appointment_date >= start,
                Booking.appointment_date <= end,
            )
        )
    ).all()
    occupied: set[tuple[uuid.UUID, date, time]] = set()
    for b in existing:
        occupied.add((b.doctor_id, b.appointment_date, b.appointment_time))
        if b.notes in (BOOKING_CALENDAR_NOTE, BOOKING_WINDOW_NOTE):
            b.status = window_booking_status(
                b.appointment_date, today, clinic_id, b.doctor_id, b.appointment_time
            )
            b.erp_processed = b.appointment_date < today and b.status == BookingStatus.COMPLETED.value
    await session.flush()

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
    patient_ids = list(
        (
            await session.scalars(
                select(Patient.id).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
            )
        ).all()
    )
    if not patient_ids or not doctor_services:
        return

    added = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            for doc_id, svc_ids in doctor_services.items():
                if not svc_ids:
                    continue
                for slot_t in SLOT_STARTS:
                    if (doc_id, d, slot_t) in occupied:
                        continue
                    fill_key = f"windowfill:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}"
                    if _stable_unit(fill_key) >= WINDOW_FILL_RATIO:
                        continue
                    raw_p = f"wpatient:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}"
                    patient_id = patient_ids[int(hashlib.sha256(raw_p.encode()).hexdigest(), 16) % len(patient_ids)]
                    raw_s = f"wservice:{clinic_id}:{doc_id}:{d.isoformat()}:{slot_t.isoformat(timespec='minutes')}"
                    service_id = svc_ids[int(hashlib.sha256(raw_s.encode()).hexdigest(), 16) % len(svc_ids)]
                    st = window_booking_status(d, today, clinic_id, doc_id, slot_t)
                    booking = Booking(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        patient_id=patient_id,
                        doctor_id=doc_id,
                        service_id=service_id,
                        appointment_date=d,
                        appointment_time=slot_t,
                        status=st,
                        prepayment_amount=Decimal("0"),
                        erp_processed=d < today and st == BookingStatus.COMPLETED.value,
                        notes=BOOKING_WINDOW_NOTE,
                    )
                    try:
                        async with session.begin_nested():
                            session.add(booking)
                            await session.flush()
                    except IntegrityError:
                        continue
                    occupied.add((doc_id, d, slot_t))
                    added += 1
        d += timedelta(days=1)
    if added:
        await session.flush()


async def _ensure_window_kanban(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    owner_id: uuid.UUID,
    admin_ids: list[uuid.UUID],
    general_id: uuid.UUID,
    sales_id: uuid.UUID,
) -> uuid.UUID | None:
    window_task_filter = or_(
        Task.title.like(f"{TASK_PREFIX_LEGACY}%"),
        Task.title.in_(WINDOW_TASK_TITLES),
    )
    existing_tasks = list(
        (
            await session.scalars(
                select(Task)
                .where(Task.clinic_id == clinic_id, window_task_filter)
                .order_by(Task.created_at.asc())
            )
        ).all()
    )
    for task in existing_tasks:
        if task.title.startswith(TASK_PREFIX_LEGACY):
            rest = task.title[len(TASK_PREFIX_LEGACY) :].strip()
            if rest:
                task.title = rest
        task.description = "Two-week ops task. Linked to a real staff member."
    if existing_tasks:
        await session.flush()
        return existing_tasks[0].id

    if not admin_ids:
        admin_ids = [owner_id]
    patients = list(
        (
            await session.scalars(
                select(Patient.id).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)).limit(4)
            )
        ).all()
    )
    now = _utc_aware()
    today = date.today()
    first_id: uuid.UUID | None = None
    created: list[uuid.UUID] = []
    for rank, (suffix, status, priority, stream, due_off, chk, blocked, cidx) in enumerate(WINDOW_TASKS, start=1):
        tid = uuid.uuid4()
        if first_id is None:
            first_id = tid
        stream_id = sales_id if stream == "sales" else general_id
        aid = admin_ids[rank % len(admin_ids)]
        due_day = today + timedelta(days=due_off)
        due_at = datetime(due_day.year, due_day.month, due_day.day, 16, 0, tzinfo=timezone.utc)
        completed_at = (now - timedelta(days=abs(due_off) + 1)) if status == "done" else None
        session.add(
            Task(
                id=tid,
                clinic_id=clinic_id,
                stream_id=stream_id,
                title=suffix,
                description="Two-week ops task. Linked to a real staff member.",
                status=status,
                priority=priority,
                creator_id=owner_id,
                assignee_id=aid,
                due_at=due_at,
                completed_at=completed_at,
                patient_id=patients[rank % len(patients)] if patients and stream == "sales" else None,
                source="manual",
                rank=2000 + rank * 10,
                blocked=blocked,
                blocked_reason="Waiting on a signed membership scan from the patient." if blocked else None,
                checklist_done=chk,
                updated_by_admin_id=owner_id,
            )
        )
        session.add(TaskAssignee(task_id=tid, admin_id=aid))
        created.append(tid)
    await session.flush()
    for rank, spec in enumerate(WINDOW_TASKS):
        cidx = spec[7]
        if cidx < 0:
            continue
        session.add(
            TaskComment(
                id=uuid.uuid4(),
                task_id=created[rank],
                author_id=admin_ids[rank % len(admin_ids)],
                text=TASK_COMMENTS[cidx],
            )
        )
    await session.flush()
    return first_id


async def _ensure_window_meetings(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    owner_id: uuid.UUID,
    participant_ids: list[uuid.UUID],
    linked_task_id: uuid.UUID | None,
) -> None:
    existing_events = list(
        (
            await session.scalars(
                select(StaffCalendarEvent).where(
                    StaffCalendarEvent.clinic_id == clinic_id,
                    or_(
                        StaffCalendarEvent.title.like(f"{CAL_PREFIX_LEGACY}%"),
                        StaffCalendarEvent.title.in_(WINDOW_MEETINGS),
                    ),
                )
            )
        ).all()
    )
    for ev in existing_events:
        if ev.title.startswith(CAL_PREFIX_LEGACY):
            rest = ev.title[len(CAL_PREFIX_LEGACY) :].strip()
            if rest:
                ev.title = rest
        ev.description = "Staff meeting."
    have = {ev.title for ev in existing_events}
    needed = [title for title in WINDOW_MEETINGS if title not in have]
    today = date.today()
    parts = list(dict.fromkeys(pid for pid in participant_ids if pid))
    if owner_id not in parts:
        parts.insert(0, owner_id)
    ack = _utc_naive_wall()
    days = meeting_anchor_days(today, n=len(WINDOW_MEETINGS))

    if existing_events:
        ordered = sorted(existing_events, key=lambda e: e.title)
        for ev, day in zip(ordered, days):
            for h in WINDOW_HOUR_SLOTS:
                starts_at = datetime(
                    day.year, day.month, day.day, h, WINDOW_SLOT_MINUTES.get(h, 30), 0
                )
                ends_at = starts_at + timedelta(minutes=40)
                if not await _calendar_slot_free(
                    session, clinic_id, starts_at, ends_at, exclude_id=ev.id
                ):
                    continue
                ev.starts_at = starts_at
                ev.ends_at = ends_at
                break
        await session.flush()
    if not needed:
        return
    idx = 0
    for day in meeting_anchor_days(today, n=max(len(needed), len(WINDOW_MEETINGS))):
        if idx >= len(needed):
            break
        placed = False
        for h in WINDOW_HOUR_SLOTS:
            starts_at = datetime(
                day.year,
                day.month,
                day.day,
                h,
                WINDOW_SLOT_MINUTES.get(h, 30),
                0,
            )
            ends_at = starts_at + timedelta(minutes=40)
            if not await _calendar_slot_free(session, clinic_id, starts_at, ends_at):
                continue
            ev_id = uuid.uuid4()
            session.add(
                StaffCalendarEvent(
                    id=ev_id,
                    clinic_id=clinic_id,
                    title=needed[idx],
                    description="Staff meeting.",
                    starts_at=starts_at,
                    ends_at=ends_at,
                    all_day=False,
                    created_by_admin_id=owner_id,
                    task_id=linked_task_id if idx == 0 and not have else None,
                    reminder_minutes_before=15,
                )
            )
            await session.flush()
            for pid in parts:
                session.add(StaffCalendarEventParticipant(event_id=ev_id, admin_id=pid))
                session.add(
                    StaffCalendarEventInvitation(
                        id=uuid.uuid4(),
                        clinic_id=clinic_id,
                        event_id=ev_id,
                        invitee_admin_id=pid,
                        acknowledged_at=ack,
                    )
                )
            await session.flush()
            idx += 1
            placed = True
            break
        if not placed:
            continue


async def _ensure_window_huddle(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    room = (
        await session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.clinic_id == clinic_id,
                StaffChatRoom.kind == GROUP_ROOM_KIND,
                StaffChatRoom.title.in_((HUDDLE_TITLE, HUDDLE_TITLE_LEGACY)),
            )
        )
    ).scalar_one_or_none()
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
    ) or [owner_id]
    if room is None:
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=GROUP_ROOM_KIND,
            title=HUDDLE_TITLE,
            created_by_admin_id=owner_id,
        )
        session.add(room)
        await session.flush()
    else:
        room.title = HUDDLE_TITLE
    for aid in admin_ids:
        if await session.get(StaffChatRoomMember, (room.id, aid)) is None:
            session.add(
                StaffChatRoomMember(room_id=room.id, admin_id=aid, membership_kind=MEMBERSHIP_GROUP)
            )
    await session.flush()
    existing = list(
        (
            await session.scalars(
                select(StaffChatMessage)
                .where(StaffChatMessage.room_id == room.id)
                .order_by(StaffChatMessage.created_at.asc())
            )
        ).all()
    )
    now = _utc_naive_wall()
    for i, body in enumerate(HUDDLE_BODIES):
        if i < len(existing):
            existing[i].body = body
        else:
            session.add(
                StaffChatMessage(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    room_id=room.id,
                    author_admin_id=admin_ids[i % len(admin_ids)],
                    body=body,
                    created_at=now - timedelta(days=WINDOW_DAYS - i, hours=9, minutes=i * 11),
                )
            )
    for extra in existing[len(HUDDLE_BODIES) :]:
        await session.delete(extra)
    await session.flush()


async def _ensure_window_omni(session: AsyncSession, clinic: Clinic, owner_id: uuid.UUID) -> None:
    omni = OmnichannelChatService(session)
    key = (clinic.clinic_slug or "clinic").replace("showcase-", "")
    today = date.today()
    start, _end = window_bounds(today)
    for provider, patient_name, kind, turns in OMNI_SCRIPTS:
        patient = await _patient_by_name(session, clinic.id, patient_name)
        from_id = f"win_{kind}_{key}"
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
        ids = {provider_key: from_id, "showcase_window": OMNI_META}
        if patient is not None:
            ids["patient_id"] = str(patient.id)
        if contact is None:
            contact = OmniContact(
                business_account_id=clinic.id,
                full_name=patient_name,
                primary_phone=(patient.phone if patient is not None else None),
                external_ids=ids,
            )
            session.add(contact)
            await session.flush()
        else:
            merged = dict(contact.external_ids or {})
            merged.update(ids)
            contact.external_ids = merged
            contact.full_name = patient_name
            await session.flush()
        chat = await omni.get_or_create_chat(clinic.id, contact, channel_id=channel_id)
        chat.title = patient_name
        chat.ai_mode = "DISABLED"
        chat.assignee_admin_id = owner_id
        if chat.claimed_at is None:
            chat.claimed_at = _utc_naive_wall()
        await session.flush()
        for i, (direction, text) in enumerate(turns):
            ext_id = f"showcase-win-{key}-{kind}-{i}"
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
                        "showcase": OMNI_META,
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
                        "showcase": OMNI_META,
                        "external_message_id": ext_id,
                        "provider": provider,
                    },
                )
        msgs = (
            await session.scalars(
                select(OmniMessage).where(OmniMessage.chat_id == chat.id).order_by(OmniMessage.created_at.asc())
            )
        ).all()
        showcase_msgs = [m for m in msgs if str((m.source_metadata or {}).get("showcase") or "") == OMNI_META]
        if showcase_msgs:
            base_day = start + timedelta(days=2 if kind == "complaint" else 8 if kind == "noshow" else 13)
            base = datetime(base_day.year, base_day.month, base_day.day, 10, 0, 0)
            for i, msg in enumerate(showcase_msgs):
                msg.created_at = base + timedelta(minutes=i * 12)
            last = showcase_msgs[-1]
            chat.last_message_at = last.created_at
            chat.last_actor_type = last.actor_type
        await session.flush()


async def apply_showcase_en_demo_window(
    session: AsyncSession,
    *,
    clinic: Clinic,
    owner_admin_id: uuid.UUID,
) -> None:
    """English ±14 day tour layer for one showcase clinic."""
    await _ensure_doctor_logins(session, clinic)
    today = date.today()
    await _remix_and_fill_bookings(session, clinic.id, today)

    general = (
        await session.execute(
            select(TaskStream).where(
                TaskStream.clinic_id == clinic.id,
                TaskStream.slug == "general",
                TaskStream.is_archived.is_(False),
            )
        )
    ).scalar_one_or_none()
    admin_ids = list(
        (
            await session.scalars(
                select(AdminUser.id).where(
                    AdminUser.clinic_id == clinic.id,
                    AdminUser.deleted_at.is_(None),
                ).order_by(AdminUser.email.asc())
            )
        ).all()
    ) or [owner_admin_id]
    linked: uuid.UUID | None = None
    if general is not None:
        sales = await _ensure_sales_stream(session, clinic.id)
        linked = await _ensure_window_kanban(
            session,
            clinic.id,
            owner_id=owner_admin_id,
            admin_ids=admin_ids,
            general_id=general.id,
            sales_id=sales.id,
        )
        await _ensure_window_meetings(
            session,
            clinic.id,
            owner_id=owner_admin_id,
            participant_ids=admin_ids[:4],
            linked_task_id=linked,
        )
    await _ensure_window_huddle(session, clinic.id, owner_admin_id)
    await _ensure_window_omni(session, clinic, owner_admin_id)


def clinician_emails() -> list[tuple[str, str, str]]:
    """(city_key, email, full_name) for docs."""
    out: list[tuple[str, str, str]] = []
    for spec in ORG_SPECS:
        clinicians = spec.get("clinicians")
        if not isinstance(clinicians, list):
            continue
        for email, name in clinicians:
            out.append((str(spec["key"]), str(email), str(name)))
    return out
