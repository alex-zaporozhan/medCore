"""Celery tasks for loyalty: expiring packages reminders (B6.3) and campaign engine."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.application.services.notification_service import send_with_fallback
from src.application.services.loyalty_campaign_engine import run_campaigns_for_clinic
from src.core.metrics import loyalty_campaign_batch_errors_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.clinic import Clinic
from src.infrastructure.database.base import AsyncSessionLocal
from src.core.datetime_utils import utc_now
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.notification import Notification
from src.domain.entities.patient import Patient
from src.domain.entities.subscription_package import SubscriptionPackage
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)

# Days before expiry to notify (configurable; can be moved to clinic settings)
EXPIRING_DAYS = 14


def _format_expiring_message(
    package_name: str,
    remaining_visits: int | None,
    remaining_amount: str | None,
    days_left: int,
) -> str:
    """Template: «У вас сгорят 2 массажа через 2 недели! Давайте найдём окно?»"""
    parts = []
    if remaining_visits and remaining_visits > 0:
        parts.append(f"{remaining_visits} визит(ов)" if remaining_visits != 1 else "1 визит")
    if remaining_amount and float(remaining_amount) > 0:
        if parts:
            parts.append(f" и {remaining_amount} ₽")
        else:
            parts.append(f"{remaining_amount} ₽")
    what = " ".join(parts) or package_name
    if days_left == 1:
        when = "завтра"
    elif days_left < 7:
        when = f"через {days_left} дн."
    else:
        weeks = days_left // 7
        when = "через 2 недели" if weeks >= 2 else "через 1 неделю"
    return f"У вас сгорят {what} по абонементу «{package_name}» {when}! Давайте найдём окно?"


async def _check_expiring_packages_async() -> None:
    """Select active subscriptions expiring in EXPIRING_DAYS, enqueue notification per patient."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=EXPIRING_DAYS)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(CustomerSubscription, SubscriptionPackage)
            .join(
                SubscriptionPackage,
                SubscriptionPackage.id == CustomerSubscription.subscription_package_id,
            )
            .where(
                CustomerSubscription.status == "active",
                CustomerSubscription.expires_at.isnot(None),
                CustomerSubscription.expires_at >= now,
                CustomerSubscription.expires_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        rows = result.all()
        for sub, pkg in rows:
            try:
                days_left = (sub.expires_at.date() - now.date()).days if sub.expires_at else 0
                remaining_visits = sub.remaining_visits
                remaining_amount = str(sub.remaining_amount) if sub.remaining_amount is not None else None
                if (remaining_visits or 0) <= 0 and (sub.remaining_amount or 0) <= 0:
                    continue
                message = _format_expiring_message(
                    package_name=pkg.name,
                    remaining_visits=remaining_visits,
                    remaining_amount=remaining_amount,
                    days_left=days_left,
                )
                patient_result = await session.execute(
                    select(Patient).where(Patient.id == sub.patient_id)
                )
                patient = patient_result.scalar_one_or_none()
                channel = (patient.preferred_channel if patient else None) or "sms"
                chat_id = patient.telegram_chat_id if patient else None
                phone = patient.phone if patient else None
                email = patient.email if patient else None

                notification = Notification(
                    clinic_id=sub.clinic_id,
                    patient_id=sub.patient_id,
                    admin_id=None,
                    booking_id=None,
                    channel=channel,
                    template="expiring_package",
                    payload={
                        "message": message,
                        "subscription_id": str(sub.id),
                        "package_name": pkg.name,
                        "days_left": days_left,
                    },
                    status="pending",
                    error=None,
                    sent_at=None,
                )
                session.add(notification)
                await session.flush()

                try:
                    success, error_msg, delivery = await send_with_fallback(
                        chat_id=chat_id,
                        phone=phone,
                        email=email,
                        message=message,
                        template="expiring_package",
                        meta={"subscription_id": str(sub.id), "package_name": pkg.name},
                        preferred_channel=channel,
                    )
                    sent_at = utc_now()
                    if success and delivery == "channel":
                        notification.status = "sent"
                        notification.sent_at = sent_at
                    elif success and delivery == "log_only":
                        notification.status = "skipped_no_channel"
                        notification.error = None
                        notification.sent_at = sent_at
                    else:
                        notification.status = "failed"
                        notification.error = error_msg
                        notification.sent_at = sent_at
                    await session.flush()
                    log_evt = "check_expiring_packages: send failed"
                    if success and delivery == "channel":
                        log_evt = "check_expiring_packages: sent"
                    elif success and delivery == "log_only":
                        log_evt = "check_expiring_packages: skipped_no_channel"
                    logger.info(
                        log_evt,
                        extra={
                            "clinic_id": str(sub.clinic_id),
                            "patient_id": str(sub.patient_id),
                            "subscription_id": str(sub.id),
                            "sent": success,
                            "delivery": delivery,
                            "error": error_msg,
                        },
                    )
                except Exception as send_err:
                    logger.warning(
                        "check_expiring_packages: send exception (task continues)",
                        extra={
                            "subscription_id": str(sub.id),
                            "patient_id": str(sub.patient_id),
                            "error": str(send_err),
                        },
                    )
                    notification.status = "failed"
                    notification.error = str(send_err)
                    notification.sent_at = utc_now()
                    await session.flush()
            except Exception as e:
                logger.warning(
                    "check_expiring_packages: skip subscription",
                    extra={"subscription_id": str(sub.id), "error": str(e)},
                )
        await session.commit()


@celery_app.task(name="loyalty_tasks.check_expiring_packages")
def check_expiring_packages() -> None:
    """B6.3: Notify patients whose packages expire in N days. Run daily via beat."""
    import asyncio
    asyncio.run(_check_expiring_packages_async())


async def _run_loyalty_campaign_engine_all_clinics_async() -> None:
    """Create Tasks from loyalty campaign rules for every clinic (LOY_AI_014)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Clinic.id))
        clinic_ids = [row[0] for row in result.all()]
    for cid in clinic_ids:
        try:
            async with AsyncSessionLocal() as s:
                async with s.begin():
                    await run_campaigns_for_clinic(s, cid)
        except Exception:
            loyalty_campaign_batch_errors_total.labels(clinic_bucket=clinic_bucket_label(cid)).inc()
            logger.exception(
                "run_loyalty_campaign_engine_all_clinics: clinic failed",
                extra={"clinic_id": str(cid)},
            )


@celery_app.task(name="loyalty_tasks.run_loyalty_campaign_engine_all_clinics")
def run_loyalty_campaign_engine_all_clinics() -> None:
    """Daily: run :func:`run_campaigns_for_clinic` for all clinics."""
    import asyncio
    asyncio.run(_run_loyalty_campaign_engine_all_clinics_async())
