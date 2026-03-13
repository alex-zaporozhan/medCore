"""Waitlist service: notify on slot freed."""

import logging
from datetime import date, datetime, time, timedelta

from src.core.datetime_utils import utc_now_naive
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.queue_policy import QueuePolicy
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.entities.waitlist_notification import WaitlistNotification

logger = logging.getLogger(__name__)


class WaitlistService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def notify_slot_freed(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        slot_date: date,
        slot_time: time,
    ) -> None:
        """Create waitlist notifications for matching entries (backend logic; actual send in Phase 3)."""
        result = await self.session.execute(
            select(QueuePolicy).where(QueuePolicy.clinic_id == clinic_id)
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return
        entries_result = await self.session.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.clinic_id == clinic_id,
                WaitlistEntry.status == "waiting",
                (WaitlistEntry.doctor_id.is_(None)) | (WaitlistEntry.doctor_id == doctor_id),
            ).order_by(WaitlistEntry.priority.desc()).limit(policy.broadcast_size)
        )
        entries = list(entries_result.scalars().all())
        if not entries:
            return
        expires_at = None
        if policy.response_timeout_minutes:
            expires_at = utc_now_naive() + timedelta(minutes=policy.response_timeout_minutes)
        for entry in entries:
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
        logger.info(
            "Waitlist notifications created for slot freed",
            extra={"clinic_id": str(clinic_id), "doctor_id": str(doctor_id), "count": len(entries)},
        )
