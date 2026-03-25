"""Celery: staff calendar reminders (fire_at due)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.datetime_utils import utc_now_naive
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_reminder_delivery import StaffCalendarReminderDelivery
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)

_ENGINE = None
_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


async def _build_session() -> AsyncSession:
    global _ENGINE, _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _ENGINE = create_async_engine(settings.database_url, echo=settings.debug)
        _SESSION_FACTORY = async_sessionmaker(
            _ENGINE,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _SESSION_FACTORY()


async def _run_calendar_reminders() -> None:
    session = await _build_session()
    try:
        # DB stores calendar timestamps as naive UTC (TIMESTAMP WITHOUT TIME ZONE).
        now = utc_now_naive()
        res = await session.execute(
            select(StaffCalendarReminderDelivery).where(
                StaffCalendarReminderDelivery.sent_at.is_(None),
                StaffCalendarReminderDelivery.fire_at <= now,
            ).limit(500)
        )
        rows = list(res.scalars().all())
        for row in rows:
            ev = await session.get(StaffCalendarEvent, row.event_id)
            title = ev.title if ev else "?"
            logger.info(
                "staff_calendar_reminder",
                extra={
                    "event_id": str(row.event_id),
                    "clinic_id": str(row.clinic_id),
                    "title": title,
                },
            )
            row.sent_at = now
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@celery_app.task(name="staff_collab_tasks.send_calendar_reminders")
def send_calendar_reminders() -> None:
    asyncio.run(_run_calendar_reminders())
