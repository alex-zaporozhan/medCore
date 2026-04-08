"""Celery: retry platform SaaS provisioning (contour B) after transient failures."""

from __future__ import annotations

import asyncio
import logging

from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app
from src.application.services.platform_billing_service import (
    expire_stale_platform_signup_intents,
    run_due_platform_provisions,
)

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="platform_billing.expire_stale_signup_intents")
def expire_stale_signup_intents_task() -> int:
    """Privacy TTL: pending_payment intents past expires_at without active YooKassa capture."""

    async def _do() -> int:
        if AsyncSessionLocal is None:
            return 0
        async with AsyncSessionLocal() as session:
            n = await expire_stale_platform_signup_intents(session, limit=500)
            if n:
                await session.commit()
            return n

    try:
        return int(_run_async(_do()))
    except Exception:
        logger.exception("platform_billing.expire_stale_signup_intents failed")
        raise


@celery_app.task(name="platform_billing.retry_due_provisions")
def retry_due_platform_provisions_task() -> int:
    """Pick intents in paid/provision_failed due for retry; bounded batch."""

    async def _do() -> int:
        if AsyncSessionLocal is None:
            return 0
        async with AsyncSessionLocal() as session:
            return await run_due_platform_provisions(session, limit=20)

    try:
        n = _run_async(_do())
        return int(n)
    except Exception:
        logger.exception("platform_billing.retry_due_provisions failed")
        raise
