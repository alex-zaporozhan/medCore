"""Celery: drain domain_outbox for crash recovery and multi-replica (ADR-009)."""

from __future__ import annotations

import asyncio
import logging

from src.application.services.domain_outbox_service import dispatch_domain_outbox_batch
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="domain_outbox.dispatch_pending")
def dispatch_pending_domain_outbox() -> int:
    """Publish unpublished outbox rows (idempotent consumers)."""
    try:
        return int(_run_async(dispatch_domain_outbox_batch()))
    except Exception:
        logger.exception("domain_outbox.dispatch_pending failed")
        raise
