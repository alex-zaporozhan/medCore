"""Celery: reconcile YooKassa ``local-pending`` payment rows (P1-4 ops backlog)."""

from __future__ import annotations

import asyncio
import logging

from src.infrastructure.messaging.celery_app import celery_app
from src.application.services.payment_local_pending_reconcile_service import (
    run_payment_local_pending_reconcile_pass,
)

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="payment_reconciliation.reconcile_local_pending")
def reconcile_local_pending_payments() -> dict[str, int]:
    """Replay idempotent YooKassa creates for stale local-pending rows (contours A + B)."""

    async def _do() -> tuple[int, int]:
        return await run_payment_local_pending_reconcile_pass()

    try:
        p, b = _run_async(_do())
        return {"patient_rows_touched": p, "platform_rows_touched": b}
    except Exception:
        logger.exception("reconcile_local_pending_payments failed")
        return {"patient_rows_touched": 0, "platform_rows_touched": 0}
