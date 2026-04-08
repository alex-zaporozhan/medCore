"""Enqueue and dispatch domain events via transactional outbox (ADR-009)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events.domain_event import DomainEvent
from src.application.events.event_bus import get_event_bus
from src.core.config import settings
from src.core.metrics import (
    domain_outbox_blocked_by_attempt_cap_rows,
    domain_outbox_dispatch_total,
    domain_outbox_gauge_refresh_failures_total,
    domain_outbox_oldest_pending_age_seconds,
    domain_outbox_pending_gauge,
)
from src.domain.entities.domain_outbox import DomainOutbox
from src.domain.entities.payment import Payment

logger = logging.getLogger(__name__)

PAYMENT_SUCCESS_DEDUP_PREFIX = "payment_success"
PLATFORM_SIGNUP_PROVISION_EVENT_TYPE = "PlatformSignupProvision"
PLATFORM_SIGNUP_PROVISION_DEDUP_PREFIX = "platform_signup_provision"


def _serialize_event(event: DomainEvent) -> dict:
    return {
        "name": event.name,
        "payload": dict(event.payload),
        "event_id": str(event.event_id),
    }


def _event_from_payload(payload: dict) -> DomainEvent:
    try:
        return DomainEvent(
            name=payload["name"],
            payload=payload["payload"],
            event_id=UUID(str(payload["event_id"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"corrupt_outbox_payload: {exc}") from exc


_gauge_refresh_ok_at_monotonic: float = 0.0


async def enqueue_payment_success_event(session: AsyncSession, payment: Payment) -> None:
    """Insert outbox row idempotently (same transaction as payment/booking updates)."""
    event = _payment_success_event_from_payment(payment)
    dedup = f"{PAYMENT_SUCCESS_DEDUP_PREFIX}:{payment.id}"
    stmt = (
        insert(DomainOutbox)
        .values(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type=event.name,
            payload=_serialize_event(event),
            dedup_key=dedup,
        )
        .on_conflict_do_nothing(index_elements=["dedup_key"])
    )
    await session.execute(stmt)


def _payment_success_event_from_payment(payment: Payment) -> DomainEvent:
    from src.application.events.standard_events import make_payment_success_event

    return make_payment_success_event(payment)


async def enqueue_platform_signup_provision(session: AsyncSession, intent_id: UUID) -> None:
    """Insert outbox row for contour B provisioning (same transaction as intent → paid)."""
    dedup = f"{PLATFORM_SIGNUP_PROVISION_DEDUP_PREFIX}:{intent_id}"
    stmt = (
        insert(DomainOutbox)
        .values(
            aggregate_type="platform_signup_intent",
            aggregate_id=intent_id,
            event_type=PLATFORM_SIGNUP_PROVISION_EVENT_TYPE,
            payload={"intent_id": str(intent_id)},
            dedup_key=dedup,
        )
        .on_conflict_do_nothing(index_elements=["dedup_key"])
    )
    await session.execute(stmt)


async def enqueue_domain_event(session: AsyncSession, event: DomainEvent) -> None:
    """Generic enqueue for serialized DomainEvent rows (e.g. booking lifecycle)."""
    dedup_val = event.payload.get("dedup_id")
    if dedup_val:
        dedup_key = str(dedup_val)[:255]
    else:
        raw_bid = event.payload.get("booking_id")
        if raw_bid:
            dedup_key = f"{event.name}:{raw_bid}"[:255]
        else:
            dedup_key = f"{event.name}:{event.event_id}"[:255]
    raw_bid = event.payload.get("booking_id")
    aggregate_id = UUID(str(raw_bid)) if raw_bid else event.event_id
    stmt = (
        insert(DomainOutbox)
        .values(
            aggregate_type="booking",
            aggregate_id=aggregate_id,
            event_type=event.name,
            payload=_serialize_event(event),
            dedup_key=dedup_key,
        )
        .on_conflict_do_nothing(index_elements=["dedup_key"])
    )
    await session.execute(stmt)


async def emit_booking_domain_event(session: AsyncSession, event: DomainEvent) -> None:
    """Booking lifecycle: transactional outbox when enabled, else in-process EventBus."""
    if settings.domain_outbox_booking_events_enabled:
        await enqueue_domain_event(session, event)
        return
    bus = get_event_bus()
    await bus.publish(event)


async def _dispatch_platform_signup_provision_row(
    session: AsyncSession, row: DomainOutbox, now: datetime
) -> bool:
    """Run execute_platform_provision under savepoint; mark outbox published. Returns True if provision succeeded."""
    from src.application.services.platform_billing_service import (
        execute_platform_provision,
        record_platform_provision_failure,
    )
    from src.domain.entities.platform_signup_intent import PlatformSignupIntent

    try:
        intent_id = UUID(str(row.payload["intent_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"corrupt_outbox_payload: {exc}") from exc

    intent = await session.get(PlatformSignupIntent, intent_id)
    if intent is None:
        await session.execute(
            update(DomainOutbox)
            .where(DomainOutbox.id == row.id)
            .values(published_at=now, last_error="intent_not_found")
        )
        return True

    try:
        async with session.begin_nested():
            await execute_platform_provision(session, intent)
    except Exception as exc:
        try:
            await record_platform_provision_failure(session, intent_id, exc)
        except Exception as rec_exc:
            rerr = str(rec_exc)[:2000]
            await session.execute(
                update(DomainOutbox)
                .where(DomainOutbox.id == row.id)
                .values(attempts=row.attempts + 1, last_error=f"record_failure:{rerr}"[:2000])
            )
            logger.exception(
                "platform outbox: record_platform_provision_failure failed outbox_id=%s",
                row.id,
            )
            return False
        await session.execute(
            update(DomainOutbox)
            .where(DomainOutbox.id == row.id)
            .values(published_at=now, last_error=str(exc)[:2000])
        )
        return False

    await session.execute(
        update(DomainOutbox)
        .where(DomainOutbox.id == row.id)
        .values(published_at=now, last_error=None)
    )
    return True


async def refresh_domain_outbox_gauges(*, force: bool = False) -> None:
    """Update pending count + oldest-unpublished age (for Prometheus scrape)."""
    global _gauge_refresh_ok_at_monotonic
    from src.infrastructure.database.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return

    interval = settings.domain_outbox_metrics_db_refresh_min_interval_seconds
    now_mono = time.monotonic()
    if (
        not force
        and interval > 0
        and _gauge_refresh_ok_at_monotonic > 0
        and (now_mono - _gauge_refresh_ok_at_monotonic) < interval
    ):
        return

    try:
        async with AsyncSessionLocal() as session:
            q = await session.execute(
                select(func.count()).select_from(DomainOutbox).where(DomainOutbox.published_at.is_(None))
            )
            n = int(q.scalar_one() or 0)
            domain_outbox_pending_gauge.set(float(n))
            qm = await session.execute(
                select(func.min(DomainOutbox.created_at)).where(DomainOutbox.published_at.is_(None))
            )
            oldest = qm.scalar_one_or_none()
            if oldest is None:
                domain_outbox_oldest_pending_age_seconds.set(0.0)
            else:
                now = datetime.now(timezone.utc)
                ts = oldest
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                domain_outbox_oldest_pending_age_seconds.set(max(0.0, (now - ts).total_seconds()))

            cap = settings.domain_outbox_max_dispatch_attempts
            if cap > 0:
                stuck = await session.scalar(
                    select(func.count()).where(
                        DomainOutbox.published_at.is_(None),
                        DomainOutbox.attempts >= cap,
                    )
                )
                domain_outbox_blocked_by_attempt_cap_rows.set(float(stuck or 0))
            else:
                domain_outbox_blocked_by_attempt_cap_rows.set(0.0)

        _gauge_refresh_ok_at_monotonic = time.monotonic()
    except Exception:
        domain_outbox_gauge_refresh_failures_total.inc()
        logger.warning("refresh_domain_outbox_gauges failed", exc_info=True)


async def dispatch_domain_outbox_batch(*, limit: int | None = None) -> int:
    """
    Claim unpublished rows, dispatch to EventBus or inline handlers (e.g. platform provision).
    Uses a fresh session; safe after HTTP commit or from Celery.
    Returns how many rows were processed in this batch (marked published or advanced); not all imply bus success.
    """
    batch = limit if limit is not None else settings.domain_outbox_dispatch_batch_limit
    from src.infrastructure.database.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return 0

    published = 0
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(DomainOutbox).where(DomainOutbox.published_at.is_(None))
            cap = settings.domain_outbox_max_dispatch_attempts
            if cap > 0:
                stmt = stmt.where(DomainOutbox.attempts < cap)
            stmt = stmt.order_by(DomainOutbox.created_at).limit(batch).with_for_update(skip_locked=True)
            result = await session.execute(stmt)
            rows: list[DomainOutbox] = list(result.scalars().all())
            bus = get_event_bus()
            now = datetime.now(timezone.utc)
            for row in rows:
                try:
                    if row.event_type == PLATFORM_SIGNUP_PROVISION_EVENT_TYPE:
                        prov_ok = await _dispatch_platform_signup_provision_row(session, row, now)
                        published += 1
                        domain_outbox_dispatch_total.labels(
                            result="ok" if prov_ok else "error",
                            event_type=row.event_type,
                        ).inc()
                        continue
                    event = _event_from_payload(row.payload)
                    await bus.publish(event)
                    await session.execute(
                        update(DomainOutbox)
                        .where(DomainOutbox.id == row.id)
                        .values(published_at=now, last_error=None)
                    )
                    published += 1
                    domain_outbox_dispatch_total.labels(result="ok", event_type=row.event_type).inc()
                except Exception as exc:
                    err = str(exc)[:2000]
                    await session.execute(
                        update(DomainOutbox)
                        .where(DomainOutbox.id == row.id)
                        .values(attempts=row.attempts + 1, last_error=err)
                    )
                    domain_outbox_dispatch_total.labels(result="error", event_type=row.event_type).inc()
                    logger.exception(
                        "domain_outbox dispatch failed outbox_id=%s event_type=%s",
                        row.id,
                        row.event_type,
                    )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    await refresh_domain_outbox_gauges(force=True)

    return published
