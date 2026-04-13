"""Reconcile YooKassa payments stuck on ``local-pending:`` after provider create without DB commit (P1-4 ops backlog)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.payment_service import PaymentService
from src.core.config import settings
from src.core.metrics import payment_local_pending_reconcile_total
from src.domain.entities.payment import Payment
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment
from src.infrastructure.external_apis.yookassa_client import YooKassaClient, YooKassaClientError

logger = logging.getLogger(__name__)

PROVIDER_YOOKASSA = "yookassa"
_LOCAL_PREFIX = "local-pending:"


def _checkout_return_url() -> str:
    return (settings.platform_saas_checkout_return_url or settings.yookassa_return_url or "").strip()


async def reconcile_stale_patient_payment_local_pending(session: AsyncSession) -> int:
    """Replay ``PaymentService.create_payment`` for stale local-pending rows (YooKassa idempotency = booking_id)."""
    yk = YooKassaClient()
    if not yk.is_configured():
        return 0
    if not settings.payment_local_pending_reconcile_enabled:
        return 0

    cutoff = datetime.now(UTC) - timedelta(seconds=max(30, settings.payment_local_pending_reconcile_min_age_seconds))
    stmt = (
        select(Payment)
        .where(
            Payment.status == "pending",
            Payment.provider == PROVIDER_YOOKASSA,
            Payment.provider_payment_id.like(f"{_LOCAL_PREFIX}%"),
            Payment.created_at < cutoff,
        )
        .order_by(Payment.created_at.asc())
        .limit(max(1, settings.payment_local_pending_reconcile_batch_limit))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        return 0

    svc = PaymentService(session)
    fixed = 0
    for pay in rows:
        bid = pay.booking_id
        try:
            await svc.create_payment(bid)
            await session.flush()
            payment_local_pending_reconcile_total.labels(contour="patient", result="ok").inc()
            fixed += 1
        except (LookupError, ValueError) as exc:
            logger.warning(
                "payment_local_pending_reconcile_patient_skip",
                extra={"payment_id": str(pay.id), "booking_id": str(bid), "error": str(exc)},
            )
            payment_local_pending_reconcile_total.labels(contour="patient", result="skip").inc()
        except Exception:
            logger.exception(
                "payment_local_pending_reconcile_patient_failed",
                extra={"payment_id": str(pay.id), "booking_id": str(bid)},
            )
            payment_local_pending_reconcile_total.labels(contour="patient", result="error").inc()
    return fixed


async def reconcile_stale_platform_payment_local_pending(session: AsyncSession) -> int:
    """Call YooKassa create with same idempotence key as row id so provider returns existing payment if any."""
    yk = YooKassaClient()
    if not yk.is_configured():
        return 0
    if not settings.payment_local_pending_reconcile_enabled:
        return 0

    return_url = _checkout_return_url()
    if not return_url:
        logger.warning("platform payment reconcile skipped: no return URL configured")
        return 0

    cutoff_aware = datetime.now(UTC) - timedelta(seconds=max(30, settings.payment_local_pending_reconcile_min_age_seconds))
    # platform_subscription_payments.created_at is TIMESTAMP WITHOUT TIME ZONE in ORM.
    cutoff = cutoff_aware.replace(tzinfo=None)
    stmt = (
        select(PlatformSubscriptionPayment)
        .where(
            PlatformSubscriptionPayment.status == "pending",
            PlatformSubscriptionPayment.provider == PROVIDER_YOOKASSA,
            PlatformSubscriptionPayment.provider_payment_id.like(f"{_LOCAL_PREFIX}%"),
            PlatformSubscriptionPayment.created_at < cutoff,
        )
        .order_by(PlatformSubscriptionPayment.created_at.asc())
        .limit(max(1, settings.payment_local_pending_reconcile_batch_limit))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        return 0

    fixed = 0
    for pay in rows:
        intent = await session.get(PlatformSignupIntent, pay.signup_intent_id)
        if intent is None:
            payment_local_pending_reconcile_total.labels(contour="platform", result="skip").inc()
            continue
        snap = intent.tariff_snapshot if isinstance(intent.tariff_snapshot, dict) else {}
        plan_slug = str(snap.get("plan_slug") or "plan")
        bp = str(snap.get("billing_period") or "monthly")
        desc = f"SaaS {plan_slug} ({bp})"[:255]
        amount = pay.amount if pay.amount is not None else Decimal("0")
        if amount <= 0:
            payment_local_pending_reconcile_total.labels(contour="platform", result="skip").inc()
            continue
        try:
            pid, _url = await asyncio.to_thread(
                yk.create_platform_subscription_payment,
                amount,
                return_url,
                desc,
                intent.id,
                str(pay.id),
            )
            pay.provider_payment_id = str(pid)
            await session.flush()
            payment_local_pending_reconcile_total.labels(contour="platform", result="ok").inc()
            fixed += 1
        except YooKassaClientError as exc:
            logger.warning(
                "payment_local_pending_reconcile_platform_yk",
                extra={"payment_id": str(pay.id), "error": str(exc)},
            )
            payment_local_pending_reconcile_total.labels(contour="platform", result="skip").inc()
        except Exception:
            logger.exception(
                "payment_local_pending_reconcile_platform_failed",
                extra={"payment_id": str(pay.id)},
            )
            payment_local_pending_reconcile_total.labels(contour="platform", result="error").inc()
    return fixed


async def run_payment_local_pending_reconcile_pass() -> tuple[int, int]:
    """One Celery tick: patient + platform reconcile. Returns (patient_fixed, platform_fixed)."""
    from src.infrastructure.database.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return (0, 0)
    p_fixed = 0
    b_fixed = 0
    async with AsyncSessionLocal() as session:
        async with session.begin():
            p_fixed = await reconcile_stale_patient_payment_local_pending(session)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            b_fixed = await reconcile_stale_platform_payment_local_pending(session)
    return (p_fixed, b_fixed)
