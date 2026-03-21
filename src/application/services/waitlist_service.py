"""Waitlist facade: lifecycle, slot-freed notifications, booking conversion (BKG_WAITLIST_004)."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.datetime_utils import utc_now_naive
from src.core.metrics import (
    waitlist_booking_conversion_total,
    waitlist_entries_total,
    waitlist_slot_notify_total,
    waitlist_status_transitions_total,
)
from src.domain.entities.doctor import Doctor
from src.domain.entities.patient import Patient
from src.domain.entities.queue_policy import QueuePolicy
from src.domain.entities.service import Service
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.entities.waitlist_notification import WaitlistNotification
from src.domain.entities.waitlist_status import (
    LEGACY_CONVERTED_STATUS,
    WaitlistStatus,
    can_transition_waitlist,
    is_terminal_status,
    normalize_waitlist_status,
)
from src.application.dto.waitlist_dto import WaitlistEntryCreate, WaitlistEntryUpdate

logger = logging.getLogger(__name__)


class WaitlistServiceError(Exception):
    """Domain error for waitlist operations."""


class WaitlistInvalidTransition(WaitlistServiceError):
    """Status transition not allowed."""


class WaitlistService:
    """Single entry point for waitlist mutations and slot-freed handling."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _ensure_patient_in_clinic(self, clinic_id: UUID, patient_id: UUID) -> None:
        patient = await self.session.get(Patient, patient_id)
        if patient is None or patient.clinic_id != clinic_id:
            raise WaitlistServiceError("patient_clinic_mismatch")

    async def _ensure_doctor_in_clinic(self, clinic_id: UUID, doctor_id: UUID | None) -> None:
        if doctor_id is None:
            return
        doctor = await self.session.get(Doctor, doctor_id)
        if doctor is None or doctor.clinic_id != clinic_id:
            raise WaitlistServiceError("doctor_clinic_mismatch")

    async def _ensure_service_in_clinic(self, clinic_id: UUID, service_id: UUID | None) -> None:
        if service_id is None:
            return
        service = await self.session.get(Service, service_id)
        if service is None or service.clinic_id != clinic_id:
            raise WaitlistServiceError("service_clinic_mismatch")

    async def get_entry(self, clinic_id: UUID, entry_id: UUID) -> WaitlistEntry | None:
        entry = await self.session.get(WaitlistEntry, entry_id)
        if entry is None or entry.clinic_id != clinic_id:
            return None
        return entry

    async def lock_entry_for_admin_booking(
        self,
        clinic_id: UUID,
        entry_id: UUID,
    ) -> WaitlistEntry:
        """Load waitlist row with FOR UPDATE to serialize conversion (no double booking)."""
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.id == entry_id,
                WaitlistEntry.clinic_id == clinic_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            raise LookupError("Waitlist entry not found")
        old_s = normalize_waitlist_status(entry.status)
        if old_s not in (WaitlistStatus.WAITING.value, WaitlistStatus.NOTIFIED.value):
            raise ValueError("Waitlist entry is no longer available for conversion")
        return entry

    async def list_entries(
        self,
        clinic_id: UUID,
        *,
        include_inactive: bool = False,
        include_booked: bool = False,
    ) -> list[WaitlistEntry]:
        q = select(WaitlistEntry).where(WaitlistEntry.clinic_id == clinic_id)
        if not include_inactive:
            q = q.where(
                WaitlistEntry.status.notin_(
                    [WaitlistStatus.CANCELLED.value, WaitlistStatus.EXPIRED.value]
                )
            )
        if not include_booked:
            q = q.where(
                WaitlistEntry.status.notin_(
                    [WaitlistStatus.BOOKED.value, LEGACY_CONVERTED_STATUS]
                )
            )
        q = q.order_by(WaitlistEntry.priority.desc(), WaitlistEntry.created_at.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def create_entry(
        self,
        clinic_id: UUID,
        body: WaitlistEntryCreate,
        *,
        actor_admin_id: UUID | None = None,
    ) -> WaitlistEntry:
        await self._ensure_patient_in_clinic(clinic_id, body.patient_id)
        await self._ensure_doctor_in_clinic(clinic_id, body.doctor_id)
        await self._ensure_service_in_clinic(clinic_id, body.preferred_service_id)

        raw_status = normalize_waitlist_status(body.status or WaitlistStatus.WAITING.value)
        if raw_status not in (
            WaitlistStatus.WAITING.value,
            WaitlistStatus.NOTIFIED.value,
        ):
            raise WaitlistServiceError("invalid_initial_status")

        entry = WaitlistEntry(
            clinic_id=clinic_id,
            patient_id=body.patient_id,
            doctor_id=body.doctor_id,
            preferred_service_id=body.preferred_service_id,
            speciality=body.speciality,
            time_preferences_json=body.time_preferences_json,
            preferred_date=body.preferred_date,
            preferred_time=body.preferred_time,
            priority=body.priority,
            status=raw_status,
            source=body.source or "admin",
            notes=body.notes,
            created_by_id=actor_admin_id,
            updated_by_id=actor_admin_id,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        waitlist_entries_total.labels(clinic_id=str(clinic_id), op="create").inc()
        logger.info(
            "waitlist_entry_created",
            extra={
                "clinic_id": str(clinic_id),
                "patient_id": str(body.patient_id),
                "entry_id": str(entry.id),
                "status": entry.status,
                "source": entry.source,
                "preferred_service_id": str(body.preferred_service_id)
                if body.preferred_service_id
                else None,
            },
        )
        return entry

    async def update_entry(
        self,
        clinic_id: UUID,
        entry_id: UUID,
        body: WaitlistEntryUpdate,
        *,
        actor_admin_id: UUID | None = None,
    ) -> WaitlistEntry:
        entry = await self.get_entry(clinic_id, entry_id)
        if entry is None:
            raise LookupError("waitlist_entry_not_found")
        if is_terminal_status(normalize_waitlist_status(entry.status)):
            raise WaitlistServiceError("entry_terminal_immutable")

        data = body.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        if "patient_id" in data and data["patient_id"] is not None:
            await self._ensure_patient_in_clinic(clinic_id, data["patient_id"])
        if "doctor_id" in data:
            await self._ensure_doctor_in_clinic(clinic_id, data.get("doctor_id"))
        if "preferred_service_id" in data:
            await self._ensure_service_in_clinic(clinic_id, data.get("preferred_service_id"))

        for k, v in data.items():
            setattr(entry, k, v)

        if new_status is not None:
            new_s = normalize_waitlist_status(new_status)
            old_s = normalize_waitlist_status(entry.status)
            if new_s == WaitlistStatus.BOOKED.value:
                raise WaitlistServiceError("booked_status_only_via_booking")
            if not can_transition_waitlist(old_s, new_s):
                raise WaitlistInvalidTransition(f"{old_s} -> {new_s}")
            waitlist_status_transitions_total.labels(
                clinic_id=str(clinic_id),
                from_status=old_s,
                to_status=new_s,
            ).inc()
            entry.status = new_s

        entry.updated_by_id = actor_admin_id
        await self.session.flush()
        await self.session.refresh(entry)
        waitlist_entries_total.labels(clinic_id=str(clinic_id), op="update").inc()
        logger.info(
            "waitlist_entry_updated",
            extra={
                "clinic_id": str(clinic_id),
                "entry_id": str(entry_id),
                "status": entry.status,
            },
        )
        return entry

    async def cancel_entry(
        self,
        clinic_id: UUID,
        entry_id: UUID,
        *,
        actor_admin_id: UUID | None = None,
    ) -> WaitlistEntry:
        """Soft-cancel: status cancelled (row retained for audit)."""
        entry = await self.get_entry(clinic_id, entry_id)
        if entry is None:
            raise LookupError("waitlist_entry_not_found")
        old_s = normalize_waitlist_status(entry.status)
        if is_terminal_status(old_s):
            raise WaitlistServiceError("entry_already_terminal")
        if not can_transition_waitlist(old_s, WaitlistStatus.CANCELLED.value):
            raise WaitlistInvalidTransition(f"{old_s} -> cancelled")
        entry.status = WaitlistStatus.CANCELLED.value
        entry.updated_by_id = actor_admin_id
        await self.session.flush()
        await self.session.refresh(entry)
        waitlist_status_transitions_total.labels(
            clinic_id=str(clinic_id),
            from_status=old_s,
            to_status=WaitlistStatus.CANCELLED.value,
        ).inc()
        waitlist_entries_total.labels(clinic_id=str(clinic_id), op="cancel").inc()
        logger.info(
            "waitlist_entry_cancelled",
            extra={"clinic_id": str(clinic_id), "entry_id": str(entry_id)},
        )
        return entry

    async def mark_booked_after_booking_created(
        self,
        clinic_id: UUID,
        entry_id: UUID,
        booking_id: UUID,
        *,
        actor_admin_id: UUID | None = None,
    ) -> None:
        """After BookingService created a booking from a waitlist entry (locked row)."""
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.id == entry_id,
                WaitlistEntry.clinic_id == clinic_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            raise LookupError("waitlist_entry_not_found")
        old_s = normalize_waitlist_status(entry.status)
        if old_s not in (WaitlistStatus.WAITING.value, WaitlistStatus.NOTIFIED.value):
            raise WaitlistServiceError("entry_not_open_for_booking")
        if not can_transition_waitlist(old_s, WaitlistStatus.BOOKED.value):
            raise WaitlistInvalidTransition(f"{old_s} -> booked")
        entry.status = WaitlistStatus.BOOKED.value
        entry.booking_id = booking_id
        entry.updated_by_id = actor_admin_id
        await self.session.flush()
        waitlist_status_transitions_total.labels(
            clinic_id=str(clinic_id),
            from_status=old_s,
            to_status=WaitlistStatus.BOOKED.value,
        ).inc()
        waitlist_booking_conversion_total.labels(clinic_id=str(clinic_id), outcome="success").inc()
        logger.info(
            "waitlist_entry_booked",
            extra={
                "clinic_id": str(clinic_id),
                "entry_id": str(entry_id),
                "booking_id": str(booking_id),
            },
        )

    async def notify_slot_freed(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        slot_date: date,
        slot_time: time,
        *,
        service_id: UUID | None = None,
    ) -> None:
        """Match waiting entries, create WaitlistNotification rows, mark entries notified."""
        result = await self.session.execute(
            select(QueuePolicy).where(QueuePolicy.clinic_id == clinic_id)
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return

        limit_n = 1 if (policy.mode or "").lower() == "sequential" else int(policy.broadcast_size or 5)

        base_where = [
            WaitlistEntry.clinic_id == clinic_id,
            WaitlistEntry.status == WaitlistStatus.WAITING.value,
            (WaitlistEntry.doctor_id.is_(None)) | (WaitlistEntry.doctor_id == doctor_id),
        ]
        if service_id is not None:
            base_where.append(
                (WaitlistEntry.preferred_service_id.is_(None))
                | (WaitlistEntry.preferred_service_id == service_id)
            )

        stmt = (
            select(WaitlistEntry)
            .where(*base_where)
            .order_by(WaitlistEntry.priority.desc(), WaitlistEntry.id)
            .limit(limit_n)
            .with_for_update(skip_locked=True)
        )
        entries_result = await self.session.execute(stmt)
        entries = list(entries_result.scalars().all())
        if not entries:
            waitlist_slot_notify_total.labels(clinic_id=str(clinic_id), outcome="no_match").inc()
            return

        expires_at: datetime | None = None
        if policy.response_timeout_minutes:
            expires_at = utc_now_naive() + timedelta(minutes=policy.response_timeout_minutes)

        notified_count = 0
        for entry in entries:
            if policy.max_notifications_per_entry is not None:
                cnt_result = await self.session.execute(
                    select(func.count())
                    .select_from(WaitlistNotification)
                    .where(WaitlistNotification.waitlist_entry_id == entry.id)
                )
                prior = int(cnt_result.scalar() or 0)
                if prior >= policy.max_notifications_per_entry:
                    continue

            self.session.add(
                WaitlistNotification(
                    waitlist_entry_id=entry.id,
                    doctor_id=doctor_id,
                    slot_date=slot_date,
                    slot_time=slot_time,
                    channel="sms",
                    status="sent",
                    expires_at=expires_at,
                )
            )
            old_s = normalize_waitlist_status(entry.status)
            entry.status = WaitlistStatus.NOTIFIED.value
            notified_count += 1
            waitlist_status_transitions_total.labels(
                clinic_id=str(clinic_id),
                from_status=old_s,
                to_status=WaitlistStatus.NOTIFIED.value,
            ).inc()

        await self.session.flush()
        if notified_count == 0:
            waitlist_slot_notify_total.labels(clinic_id=str(clinic_id), outcome="no_match").inc()
            return
        waitlist_slot_notify_total.labels(clinic_id=str(clinic_id), outcome="notified").inc()
        logger.info(
            "waitlist_slot_freed_handled",
            extra={
                "clinic_id": str(clinic_id),
                "doctor_id": str(doctor_id),
                "service_id": str(service_id) if service_id else None,
                "count": notified_count,
            },
        )
