"""Batch job helpers for creating Tasks/Recall entries from loyalty gaps."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.datetime_utils import utc_now
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.wallet import Wallet
from src.domain.entities.patient import Patient
from src.domain.entities.loyalty_policy import LoyaltyPolicy
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.application.services.task_service import TaskService


LOYALTY_JOB_EXPIRY_DAYS_THRESHOLD_DEFAULT = 14
LOYALTY_JOB_MIN_REMAINING_VISITS_DEFAULT = 1
LOYALTY_JOB_MIN_REMAINING_AMOUNT_DEFAULT = Decimal("1.00")
LOYALTY_JOB_WALLET_MIN_BALANCE_DEFAULT = Decimal("1.00")


async def _load_job_thresholds(session: AsyncSession, clinic_id: UUID) -> dict[str, Decimal | int]:
    """Return thresholds for loyalty attention job based on LoyaltyPolicy or defaults.

    These thresholds only influence which Tasks мы создаём, не меняя финансовый учёт.
    """
    result = await session.execute(
        select(LoyaltyPolicy).where(LoyaltyPolicy.clinic_id == clinic_id)
    )
    policy: LoyaltyPolicy | None = result.scalar_one_or_none()
    if not policy:
        return {
            "expiry_days": LOYALTY_JOB_EXPIRY_DAYS_THRESHOLD_DEFAULT,
            "min_remaining_visits": LOYALTY_JOB_MIN_REMAINING_VISITS_DEFAULT,
            "min_remaining_amount": LOYALTY_JOB_MIN_REMAINING_AMOUNT_DEFAULT,
            "wallet_min_balance": LOYALTY_JOB_WALLET_MIN_BALANCE_DEFAULT,
        }
    expiry_days = policy.points_expire_days or LOYALTY_JOB_EXPIRY_DAYS_THRESHOLD_DEFAULT
    wallet_min_balance = policy.min_check_for_cashback or LOYALTY_JOB_WALLET_MIN_BALANCE_DEFAULT
    return {
        "expiry_days": expiry_days,
        "min_remaining_visits": LOYALTY_JOB_MIN_REMAINING_VISITS_DEFAULT,
        "min_remaining_amount": LOYALTY_JOB_MIN_REMAINING_AMOUNT_DEFAULT,
        "wallet_min_balance": wallet_min_balance,
    }


async def run_loyalty_attention_job(session: AsyncSession, clinic_id: UUID) -> int:
    """Scan loyalty data and create system Tasks for at-risk balances.

    Phase 1 implementation (with configurable thresholds via LoyaltyPolicy):
    - active subscriptions in clinic with non-zero remaining_visits/amount
      that expire within configured number of days;
    - wallets in clinic with balance >= configured minimal balance.

    Returns number of tasks created.
    """
    repo: TaskRepository = TaskRepositoryImpl(session)
    task_service = TaskService(repo)

    today = utc_now().date()
    created = 0

    thresholds = await _load_job_thresholds(session, clinic_id)
    expiry_days = int(thresholds["expiry_days"])
    min_remaining_visits = int(thresholds["min_remaining_visits"])
    min_remaining_amount = Decimal(thresholds["min_remaining_amount"])
    wallet_min_balance = Decimal(thresholds["wallet_min_balance"])

    # Load patients for title enrichment
    patients_stmt: Select[tuple[Patient]] = select(Patient).where(
        Patient.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
    )
    patients_result = await session.execute(patients_stmt)
    patients = {p.id: p for p in patients_result.scalars().all()}

    subs_stmt: Select[tuple[CustomerSubscription]] = (
        select(CustomerSubscription)
        .where(
            CustomerSubscription.clinic_id == clinic_id,
            CustomerSubscription.status == "active",
        )
    )
    subs_result = await session.execute(subs_stmt)
    subs = list(subs_result.scalars().all())

    for s in subs:
        has_visits = (
            s.remaining_visits is not None
            and s.remaining_visits >= min_remaining_visits
        )
        has_amount = (
            s.remaining_amount is not None
            and s.remaining_amount >= min_remaining_amount
        )
        if not has_visits and not has_amount:
            continue
        if s.expires_at is None:
            continue
        days_left = (s.expires_at.date() - today).days
        if days_left < 0 or days_left > expiry_days:
            continue

        patient = patients.get(s.patient_id)
        patient_name = patient.full_name if patient else None
        patient_phone = patient.phone if patient else ""
        title = f"Абонемент скоро сгорит: {patient_name or patient_phone or 'Пациент'}"
        description_parts: list[str] = [
            f"Истекает {s.expires_at.date().isoformat()} (через {days_left} дн.)."
        ]
        if has_visits:
            description_parts.append(f"Остаток визитов: {s.remaining_visits}.")
        if has_amount:
            description_parts.append(f"Остаток суммы: {s.remaining_amount} ₽.")
        description = " ".join(description_parts)

        due_at = datetime.combine(s.expires_at.date(), datetime.min.time())
        await task_service.create_task(
            clinic_id=clinic_id,
            title=title,
            description=description,
            priority="high",
            creator_id=None,
            assignee_id=None,
            role_assignee="admin",
            due_at=due_at,
            booking_id=None,
            patient_id=s.patient_id,
            source="system",
            source_event_id=s.id,
        )
        created += 1

    wallet_stmt: Select[tuple[Wallet]] = (
        select(Wallet)
        .where(
            Wallet.clinic_id == clinic_id,
            Wallet.balance >= wallet_min_balance,
        )
    )
    wallet_result = await session.execute(wallet_stmt)
    wallets = list(wallet_result.scalars().all())

    for w in wallets:
        patient = patients.get(w.patient_id)
        if not patient:
            continue
        title = f"Напомнить про баллы: {patient.full_name or patient.phone}"
        description = (
            f"Баланс кошелька: {w.balance} {w.currency}. "
            "Предложите пациенту записаться и использовать баллы."
        )
        due_at = utc_now() + timedelta(days=1)
        await task_service.create_task(
            clinic_id=clinic_id,
            title=title,
            description=description,
            priority="medium",
            creator_id=None,
            assignee_id=None,
            role_assignee="admin",
            due_at=due_at,
            booking_id=None,
            patient_id=w.patient_id,
            source="system",
            source_event_id=w.id,
        )
        created += 1

    return created

