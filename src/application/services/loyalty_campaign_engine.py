"""Loyalty campaign engine: rules-based Tasks for expiring packages, wallet gaps, reengagement."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.loyalty_campaign_dto import LoyaltyCampaignRunResult
from src.application.services.attention_feed_service import (
    LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT,
    LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT,
    LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT,
    LOYALTY_MIN_REMAINING_VISITS_DEFAULT,
    LOYALTY_WALLET_MIN_BALANCE_DEFAULT,
)
from src.application.services.task_service import TaskService
from src.core.datetime_utils import utc_now
from src.core.metrics import (
    loyalty_campaign_runs_total,
    loyalty_campaign_tasks_created_total,
)
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.booking import Booking
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.loyalty_campaign_settings import LoyaltyCampaignSettings
from src.domain.entities.loyalty_policy import LoyaltyPolicy
from src.domain.entities.notification import Notification
from src.domain.entities.patient import Patient
from src.domain.entities.task import Task
from src.domain.entities.wallet import Wallet
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl

logger = logging.getLogger(__name__)

LOYALTY_KIND_EXPIRING = "LOYALTY_EXPIRING_PACKAGE"
LOYALTY_KIND_HIGH_BALANCE = "LOYALTY_HIGH_BALANCE_LOW_ACTIVITY"
LOYALTY_KIND_REENGAGEMENT = "LOYALTY_REENGAGEMENT"

LOYALTY_KINDS = (
    LOYALTY_KIND_EXPIRING,
    LOYALTY_KIND_HIGH_BALANCE,
    LOYALTY_KIND_REENGAGEMENT,
)

# No recorded visit: require account at least this old (days) before reengagement.
REENGAGEMENT_MIN_ACCOUNT_AGE_DAYS = 30


@dataclass
class _Thresholds:
    expiry_days: int
    min_remaining_visits: int
    min_remaining_amount: Decimal
    wallet_min_balance: Decimal
    inactive_days_with_balance: int


def _patient_account_age_days(patient: Patient, today: date) -> int:
    ca = patient.created_at
    if ca.tzinfo is not None:
        d = ca.astimezone(timezone.utc).date()
    else:
        d = ca.date()
    return (today - d).days


async def get_or_create_loyalty_campaign_settings(
    session: AsyncSession, clinic_id: UUID
) -> LoyaltyCampaignSettings:
    """Load or insert settings; insert uses ON CONFLICT to avoid duplicate rows under concurrency."""
    stmt = (
        pg_insert(LoyaltyCampaignSettings)
        .values(id=uuid.uuid4(), clinic_id=clinic_id)
        .on_conflict_do_nothing(constraint="ux_loyalty_campaign_settings_clinic")
    )
    await session.execute(stmt)
    await session.flush()
    result = await session.execute(
        select(LoyaltyCampaignSettings).where(
            LoyaltyCampaignSettings.clinic_id == clinic_id
        )
    )
    return result.scalar_one()


async def _load_thresholds(session: AsyncSession, clinic_id: UUID) -> _Thresholds:
    result = await session.execute(
        select(LoyaltyPolicy).where(LoyaltyPolicy.clinic_id == clinic_id)
    )
    policy: LoyaltyPolicy | None = result.scalar_one_or_none()
    if not policy:
        return _Thresholds(
            expiry_days=LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT,
            min_remaining_visits=LOYALTY_MIN_REMAINING_VISITS_DEFAULT,
            min_remaining_amount=LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT,
            wallet_min_balance=LOYALTY_WALLET_MIN_BALANCE_DEFAULT,
            inactive_days_with_balance=LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT,
        )
    expiry_days = policy.points_expire_days or LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT
    wallet_min = policy.min_check_for_cashback or LOYALTY_WALLET_MIN_BALANCE_DEFAULT
    return _Thresholds(
        expiry_days=int(expiry_days),
        min_remaining_visits=LOYALTY_MIN_REMAINING_VISITS_DEFAULT,
        min_remaining_amount=LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT,
        wallet_min_balance=Decimal(wallet_min),
        inactive_days_with_balance=LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT,
    )


def _day_start_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    d = now.astimezone(timezone.utc).date()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)


def _month_start_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    d = now.astimezone(timezone.utc).date()
    first = date(d.year, d.month, 1)
    return datetime.combine(first, datetime.min.time(), tzinfo=timezone.utc)


def _patient_allowed_for_loyalty_campaign(patient: Patient, attention_kind: str) -> bool:
    """Patient-level opt-out: all channels, reminders, or marketing-only (reengagement)."""
    if patient.disable_all_notifications:
        return False
    if attention_kind in (LOYALTY_KIND_EXPIRING, LOYALTY_KIND_HIGH_BALANCE):
        if patient.disable_reminders:
            return False
    if attention_kind == LOYALTY_KIND_REENGAGEMENT and not patient.consent_mailing:
        return False
    return True


async def _count_loyalty_tasks_today_for_clinic(
    session: AsyncSession, clinic_id: UUID, day_start: datetime
) -> int:
    q = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.clinic_id == clinic_id,
            Task.created_at >= day_start,
            Task.attention_kind.in_(LOYALTY_KINDS),
            Task.source.in_(("system", "ai_auto", "ai_suggested")),
        )
    )
    return int(q.scalar_one() or 0)


async def _count_loyalty_tasks_today_for_patient(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    day_start: datetime,
) -> int:
    q = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.clinic_id == clinic_id,
            Task.patient_id == patient_id,
            Task.created_at >= day_start,
            Task.attention_kind.in_(LOYALTY_KINDS),
            Task.source.in_(("system", "ai_auto", "ai_suggested")),
        )
    )
    return int(q.scalar_one() or 0)


async def _count_loyalty_tasks_month_for_patient(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    month_start: datetime,
) -> int:
    q = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.clinic_id == clinic_id,
            Task.patient_id == patient_id,
            Task.created_at >= month_start,
            Task.attention_kind.in_(LOYALTY_KINDS),
            Task.source.in_(("system", "ai_auto", "ai_suggested")),
        )
    )
    return int(q.scalar_one() or 0)


async def _has_recent_loyalty_campaign_task(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    attention_kind: str,
    since: datetime,
) -> bool:
    q = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.clinic_id == clinic_id,
            Task.patient_id == patient_id,
            Task.attention_kind == attention_kind,
            Task.created_at >= since,
            Task.source.in_(("system", "ai_auto", "ai_suggested")),
        )
    )
    return int(q.scalar_one() or 0) > 0


async def _sms_expiring_touch_today(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    subscription_id: UUID,
    day_start: datetime,
) -> bool:
    """True if daily SMS job already created an expiring-package notification for this subscription."""
    q = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.clinic_id == clinic_id,
            Notification.patient_id == patient_id,
            Notification.template == "expiring_package",
            Notification.created_at >= day_start,
            Notification.status.in_(("sent", "pending")),
            Notification.payload.contains({"subscription_id": str(subscription_id)}),
        )
    )
    return int(q.scalar_one() or 0) > 0


async def _load_last_visit_map(
    session: AsyncSession, clinic_id: UUID, patient_ids: set[UUID]
) -> dict[UUID, date]:
    if not patient_ids:
        return {}
    today = utc_now().date()
    stmt = (
        select(Booking.patient_id, func.max(Booking.appointment_date))
        .where(
            Booking.clinic_id == clinic_id,
            Booking.patient_id.in_(patient_ids),
            Booking.status.in_(("confirmed", "completed")),
            Booking.appointment_date <= today,
        )
        .group_by(Booking.patient_id)
    )
    result = await session.execute(stmt)
    return {row[0]: row[1] for row in result.all() if row[0] is not None}


async def run_campaigns_for_clinic(
    session: AsyncSession,
    clinic_id: UUID,
    *,
    now: datetime | None = None,
    limit: int = 500,
) -> LoyaltyCampaignRunResult:
    """Select loyalty candidates and create Tasks with LOYALTY_* attention_kind.

    Does not commit the session — caller should commit.

    FamilyLink: tasks are created for the patient tied to the wallet/subscription row;
    redirecting to primary account holder is not implemented here (see LOY_FAMILY_013).
    """
    now = now or utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    result = LoyaltyCampaignRunResult(clinic_id=clinic_id)
    settings = await get_or_create_loyalty_campaign_settings(session, clinic_id)
    if not settings.channel_tasks_enabled:
        loyalty_campaign_runs_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), status="skipped_no_channel"
        ).inc()
        logger.info(
            "loyalty_campaigns_skip",
            extra={"clinic_id": str(clinic_id), "reason": "channel_tasks_disabled"},
        )
        return result

    thresholds = await _load_thresholds(session, clinic_id)
    day_start = _day_start_utc(now)
    month_start = _month_start_utc(now)

    repo = TaskRepositoryImpl(session)
    task_service = TaskService(repo)

    expiring_patients_reserved: set[UUID] = set()
    high_balance_patients_reserved: set[UUID] = set()

    async def can_create_more() -> bool:
        if await _count_loyalty_tasks_today_for_clinic(session, clinic_id, day_start) >= (
            settings.max_contacts_per_day_clinic
        ):
            return False
        return True

    async def can_touch_patient(patient_id: UUID) -> bool:
        if await _count_loyalty_tasks_today_for_patient(
            session, clinic_id, patient_id, day_start
        ) >= settings.max_contacts_per_day_patient:
            return False
        return True

    cooldown_cutoff = now - timedelta(days=settings.campaign_cooldown_days)

    async def try_create(
        *,
        patient: Patient | None,
        patient_id: UUID,
        attention_kind: str,
        title: str,
        description: str,
        priority: str,
        due_at: datetime | None,
        source_event_id: UUID | None,
    ) -> bool:
        if patient is None:
            result.skipped_opt_out += 1
            return False
        if not _patient_allowed_for_loyalty_campaign(patient, attention_kind):
            result.skipped_opt_out += 1
            return False
        if (
            await _count_loyalty_tasks_month_for_patient(
                session, clinic_id, patient_id, month_start
            )
            >= settings.max_campaign_touches_per_patient_month
        ):
            result.skipped_limits += 1
            return False
        if not await can_create_more():
            result.skipped_limits += 1
            return False
        if not await can_touch_patient(patient_id):
            result.skipped_limits += 1
            return False
        if await _has_recent_loyalty_campaign_task(
            session, clinic_id, patient_id, attention_kind, cooldown_cutoff
        ):
            result.skipped_cooldown += 1
            return False

        await task_service.create_task(
            clinic_id=clinic_id,
            title=title,
            description=description,
            priority=priority,
            creator_id=None,
            assignee_id=None,
            role_assignee="admin",
            due_at=due_at,
            booking_id=None,
            patient_id=patient_id,
            source="system",
            source_event_id=source_event_id,
            attention_kind=attention_kind,
        )
        if attention_kind == LOYALTY_KIND_EXPIRING:
            result.created_expiring += 1
            loyalty_campaign_tasks_created_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), campaign_type="expiring"
            ).inc()
        elif attention_kind == LOYALTY_KIND_HIGH_BALANCE:
            result.created_high_balance += 1
            loyalty_campaign_tasks_created_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), campaign_type="high_balance"
            ).inc()
        else:
            result.created_reengagement += 1
            loyalty_campaign_tasks_created_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), campaign_type="reengagement"
            ).inc()
        return True

    patients_stmt: Select[tuple[Patient]] = select(Patient).where(
        Patient.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
    )
    patients_result = await session.execute(patients_stmt)
    patients = {p.id: p for p in patients_result.scalars().all()}

    created_total = 0
    today = now.date()

    # 1) Expiring subscriptions
    if settings.expiring_packages_enabled:
        subs_stmt: Select[tuple[CustomerSubscription]] = select(
            CustomerSubscription
        ).where(
            CustomerSubscription.clinic_id == clinic_id,
            CustomerSubscription.status == "active",
        )
        subs_result = await session.execute(subs_stmt)
        subs = list(subs_result.scalars().all())

        for s in subs:
            if created_total >= limit:
                break
            has_visits = (
                s.remaining_visits is not None
                and s.remaining_visits >= thresholds.min_remaining_visits
            )
            has_amount = (
                s.remaining_amount is not None
                and s.remaining_amount >= thresholds.min_remaining_amount
            )
            if not has_visits and not has_amount:
                continue
            if s.expires_at is None:
                continue
            days_left = (s.expires_at.date() - today).days
            if days_left < 0 or days_left > thresholds.expiry_days:
                continue

            if settings.skip_expiring_task_if_sms_expiring_sent_today:
                if await _sms_expiring_touch_today(
                    session, clinic_id, s.patient_id, s.id, day_start
                ):
                    result.skipped_sms_duplicate += 1
                    continue

            expiring_patients_reserved.add(s.patient_id)

            patient = patients.get(s.patient_id)
            label = "patient"
            if patient:
                label = patient.full_name or patient.phone or "patient"
            title = f"Абонемент скоро сгорит: {label}"
            desc_parts = [f"Истекает {s.expires_at.date().isoformat()} (через {days_left} дн.)."]
            if has_visits:
                desc_parts.append(f"Остаток визитов: {s.remaining_visits}.")
            if has_amount:
                desc_parts.append(f"Остаток суммы: {s.remaining_amount} ₽.")
            description = " ".join(desc_parts)
            due_at = datetime.combine(s.expires_at.date(), datetime.min.time())
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)

            ok = await try_create(
                patient=patients.get(s.patient_id),
                patient_id=s.patient_id,
                attention_kind=LOYALTY_KIND_EXPIRING,
                title=title,
                description=description,
                priority="high",
                due_at=due_at,
                source_event_id=s.id,
            )
            if ok:
                created_total += 1

    # 2) High wallet balance + low activity
    if settings.high_balance_low_activity_enabled:
        wallet_stmt: Select[tuple[Wallet]] = select(Wallet).where(
            Wallet.clinic_id == clinic_id,
            Wallet.balance >= thresholds.wallet_min_balance,
        )
        wallet_result = await session.execute(wallet_stmt)
        wallets = list(wallet_result.scalars().all())
        w_pids = {w.patient_id for w in wallets}
        last_visit_map = await _load_last_visit_map(session, clinic_id, w_pids)

        for w in wallets:
            if created_total >= limit:
                break
            pid = w.patient_id
            if pid in expiring_patients_reserved:
                result.skipped_cross_campaign += 1
                continue
            patient = patients.get(pid)
            if not patient:
                continue

            last_d = last_visit_map.get(pid)
            if last_d is not None:
                inactive_days = (today - last_d).days
                if inactive_days < thresholds.inactive_days_with_balance:
                    continue

            high_balance_patients_reserved.add(pid)

            title = f"Баллы без активности: {patient.full_name or patient.phone or 'patient'}"
            description = (
                f"Баланс кошелька: {w.balance} {w.currency}. "
                f"Давно не было визита (порог {thresholds.inactive_days_with_balance} дн.). "
                "Предложите запись и списание."
            )
            ok = await try_create(
                patient=patient,
                patient_id=pid,
                attention_kind=LOYALTY_KIND_HIGH_BALANCE,
                title=title,
                description=description,
                priority="medium",
                due_at=now + timedelta(days=1),
                source_event_id=w.id,
            )
            if ok:
                created_total += 1

    # 3) Reengagement: long inactive + loyalty signal
    if settings.reengagement_enabled:
        subs_all = await session.execute(
            select(CustomerSubscription).where(
                CustomerSubscription.clinic_id == clinic_id,
                CustomerSubscription.status == "active",
            )
        )
        sub_ids: set[UUID] = set()
        for s in subs_all.scalars().all():
            has_visits = s.remaining_visits is not None and s.remaining_visits > 0
            has_amount = s.remaining_amount is not None and s.remaining_amount > 0
            if has_visits or has_amount:
                sub_ids.add(s.patient_id)

        wall_stmt = select(Wallet.patient_id).where(
            Wallet.clinic_id == clinic_id,
            Wallet.balance >= Decimal("0.01"),
        )
        wall_ids = {row[0] for row in (await session.execute(wall_stmt)).all()}
        candidate_ids = sub_ids | wall_ids
        candidate_ids -= expiring_patients_reserved
        candidate_ids -= high_balance_patients_reserved

        last_visit_map_r = await _load_last_visit_map(session, clinic_id, candidate_ids)
        re_days = settings.reengagement_inactive_days

        for pid in list(candidate_ids):
            if created_total >= limit:
                break
            patient = patients.get(pid)
            if not patient:
                continue

            last_d = last_visit_map_r.get(pid)
            if last_d is not None:
                if (today - last_d).days < re_days:
                    continue
            else:
                age = _patient_account_age_days(patient, today)
                if age < max(re_days, REENGAGEMENT_MIN_ACCOUNT_AGE_DAYS):
                    continue

            title = f"Реактивация: {patient.full_name or patient.phone or 'patient'}"
            description = (
                f"Нет визита ≥ {re_days} дн. при наличии лояльности/кошелька. "
                "Предложите визит или акцию."
            )
            ok = await try_create(
                patient=patient,
                patient_id=pid,
                attention_kind=LOYALTY_KIND_REENGAGEMENT,
                title=title,
                description=description,
                priority="low",
                due_at=now + timedelta(days=3),
                source_event_id=pid,
            )
            if ok:
                created_total += 1

    loyalty_campaign_runs_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id), status="success"
    ).inc()
    logger.info(
        "loyalty_campaigns_run",
        extra={
            "clinic_id": str(clinic_id),
            "created_expiring": result.created_expiring,
            "created_high_balance": result.created_high_balance,
            "created_reengagement": result.created_reengagement,
            "skipped_limits": result.skipped_limits,
            "skipped_cooldown": result.skipped_cooldown,
            "skipped_cross_campaign": result.skipped_cross_campaign,
            "skipped_sms_duplicate": result.skipped_sms_duplicate,
            "skipped_opt_out": result.skipped_opt_out,
        },
    )
    return result
