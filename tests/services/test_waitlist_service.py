"""WaitlistService integration tests."""

from datetime import date, time
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from src.application.dto.waitlist_dto import WaitlistEntryCreate, WaitlistEntryUpdate
from src.application.services.waitlist_service import (
    WaitlistService,
    WaitlistServiceError,
)
from src.domain.entities.queue_policy import QueuePolicy
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.entities.waitlist_status import WaitlistStatus


async def _ensure_sequential_queue_policy(db_session, clinic_id: UUID) -> None:
    """Session-scoped seed + TRUNCATE-once: only one QueuePolicy per clinic for the whole pytest session."""
    res = await db_session.execute(select(QueuePolicy).where(QueuePolicy.clinic_id == clinic_id))
    if res.scalar_one_or_none() is not None:
        return
    db_session.add(
        QueuePolicy(
            clinic_id=clinic_id,
            mode="sequential",
            broadcast_size=5,
            response_timeout_minutes=60,
        )
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_create_and_cancel_entry(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    admin_id = seed_data["admin_id"]

    svc = WaitlistService(db_session)
    body = WaitlistEntryCreate(
        clinic_id=clinic_id,
        patient_id=patient_id,
        preferred_date=date.today(),
        priority=1,
        source="admin",
    )
    entry = await svc.create_entry(clinic_id, body, actor_admin_id=admin_id)
    assert entry.status == WaitlistStatus.WAITING.value
    await db_session.commit()

    await svc.cancel_entry(clinic_id, entry.id, actor_admin_id=admin_id)
    await db_session.commit()

    active = await svc.list_entries(clinic_id, include_inactive=False)
    assert len(active) == 0


@pytest.mark.asyncio
async def test_cannot_set_booked_via_update(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    admin_id = seed_data["admin_id"]

    svc = WaitlistService(db_session)
    entry = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(
            clinic_id=clinic_id,
            patient_id=patient_id,
            preferred_date=date.today(),
        ),
        actor_admin_id=admin_id,
    )
    await db_session.commit()

    with pytest.raises(WaitlistServiceError, match="booked_status_only_via_booking"):
        await svc.update_entry(
            clinic_id,
            entry.id,
            WaitlistEntryUpdate(status=WaitlistStatus.BOOKED.value),
            actor_admin_id=admin_id,
        )


@pytest.mark.asyncio
async def test_notify_slot_freed_marks_notified(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    await _ensure_sequential_queue_policy(db_session, clinic_id)

    svc = WaitlistService(db_session)
    created = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            preferred_service_id=service_id,
            preferred_date=date.today(),
            # notify_slot_freed picks highest priority, then oldest id; other tests leave WAITING rows.
            priority=10_000,
        ),
        actor_admin_id=seed_data["admin_id"],
    )
    await db_session.commit()

    svc2 = WaitlistService(db_session)
    await svc2.notify_slot_freed(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        slot_date=date.today(),
        slot_time=time(10, 0),
        service_id=service_id,
    )
    await db_session.commit()

    # Other tests in this module (and the suite) leave more rows in waitlist_entry; assert only our row.
    refreshed = await db_session.get(WaitlistEntry, created.id)
    assert refreshed is not None
    assert refreshed.status == WaitlistStatus.NOTIFIED.value


@pytest.mark.asyncio
async def test_service_filter_skips_mismatched_service(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    seed_service_id = seed_data["service_id"]

    other_service_id = uuid4()
    db_session.add(
        Service(
            id=other_service_id,
            clinic_id=clinic_id,
            name="Other Svc",
            category="therapy",
            price=Decimal("500.00"),
            duration_minutes=20,
            is_active=True,
        )
    )
    db_session.add(
        ServiceDoctor(service_id=other_service_id, doctor_id=doctor_id, is_active=True)
    )
    await _ensure_sequential_queue_policy(db_session, clinic_id)
    await db_session.flush()

    svc = WaitlistService(db_session)
    created = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            preferred_service_id=other_service_id,
            preferred_date=date.today(),
        ),
        actor_admin_id=seed_data["admin_id"],
    )
    await db_session.commit()

    await WaitlistService(db_session).notify_slot_freed(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        slot_date=date.today(),
        slot_time=time(10, 0),
        service_id=seed_service_id,
    )
    await db_session.commit()

    e = await db_session.get(WaitlistEntry, created.id)
    assert e is not None
    assert e.status == WaitlistStatus.WAITING.value


@pytest.mark.asyncio
async def test_invalid_transition_raises(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    svc = WaitlistService(db_session)
    entry = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(clinic_id=clinic_id, patient_id=patient_id, preferred_date=date.today()),
        actor_admin_id=seed_data["admin_id"],
    )
    await svc.cancel_entry(clinic_id, entry.id, actor_admin_id=seed_data["admin_id"])
    await db_session.commit()

    with pytest.raises(WaitlistServiceError, match="entry_already_terminal"):
        await svc.cancel_entry(clinic_id, entry.id, actor_admin_id=seed_data["admin_id"])


@pytest.mark.asyncio
async def test_notified_to_waiting_allowed(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    svc = WaitlistService(db_session)
    entry = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(
            clinic_id=clinic_id,
            patient_id=patient_id,
            preferred_date=date.today(),
            status=WaitlistStatus.NOTIFIED.value,
        ),
        actor_admin_id=seed_data["admin_id"],
    )
    await db_session.commit()

    updated = await svc.update_entry(
        clinic_id,
        entry.id,
        WaitlistEntryUpdate(status=WaitlistStatus.WAITING.value),
        actor_admin_id=seed_data["admin_id"],
    )
    assert updated.status == WaitlistStatus.WAITING.value


@pytest.mark.asyncio
async def test_terminal_entry_not_mutable(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    svc = WaitlistService(db_session)
    entry = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(clinic_id=clinic_id, patient_id=patient_id, preferred_date=date.today()),
        actor_admin_id=seed_data["admin_id"],
    )
    await svc.cancel_entry(clinic_id, entry.id, actor_admin_id=seed_data["admin_id"])
    await db_session.commit()

    with pytest.raises(WaitlistServiceError, match="entry_terminal_immutable"):
        await svc.update_entry(
            clinic_id,
            entry.id,
            WaitlistEntryUpdate(priority=99),
            actor_admin_id=seed_data["admin_id"],
        )


@pytest.mark.asyncio
async def test_cannot_reopen_cancelled(db_session, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    svc = WaitlistService(db_session)
    entry = await svc.create_entry(
        clinic_id,
        WaitlistEntryCreate(clinic_id=clinic_id, patient_id=patient_id, preferred_date=date.today()),
        actor_admin_id=seed_data["admin_id"],
    )
    await svc.cancel_entry(clinic_id, entry.id, actor_admin_id=seed_data["admin_id"])
    await db_session.commit()

    # Terminal rows reject any update before transition rules (see waitlist_service.update_entry).
    with pytest.raises(WaitlistServiceError, match="entry_terminal_immutable"):
        await svc.update_entry(
            clinic_id,
            entry.id,
            WaitlistEntryUpdate(status=WaitlistStatus.WAITING.value),
            actor_admin_id=seed_data["admin_id"],
        )
