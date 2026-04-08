"""Service that builds the owner's attention feed."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.metrics import (  # no-op fallback when prometheus_client is absent
    business_chain_tasks_attention_duration_seconds,
    business_chain_tasks_attention_errors_total,
    business_chain_tasks_attention_total,
)
from src.core.prometheus_labels import clinic_bucket_label

from src.application.dto.attention_feed_dto import AttentionFeedRead, AttentionItemRead
from src.core.datetime_utils import utc_now, utc_now_naive
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.conversation import Conversation
from src.domain.entities.patient import Patient
from src.domain.entities.task import Task
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.wallet import Wallet
from src.domain.entities.loyalty_policy import LoyaltyPolicy


RETENTION_DEFAULT_MONTHS = 6
FOLLOW_UP_MAX_ITEMS = 200
RETENTION_MAX_ITEMS = 50
CONFLICT_MAX_ITEMS = 50

# Loyalty-specific thresholds (can be tuned per clinic via LoyaltyPolicy).
# Defaults are kept conservative; per-clinic overrides are resolved dynamically.
LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT = 14
LOYALTY_MIN_REMAINING_VISITS_DEFAULT = 1
LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT = Decimal("1.00")
LOYALTY_WALLET_MIN_BALANCE_DEFAULT = Decimal("1.00")
LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT = 90


class AttentionFeedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_feed(self, clinic_id: UUID) -> AttentionFeedRead:
        started_at = utc_now()
        business_chain_tasks_attention_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            status="attempt",
        ).inc()

        try:
            follow_up_items = await self._build_follow_up_items(clinic_id)
            retention_items = await self._build_retention_gap_items(clinic_id)
            loyalty_items = await self._build_loyalty_loyalty_gap_items(clinic_id)
            conflict_items = await self._build_conflict_items(clinic_id)
            # Enrich all items with task linkage and computed attention status
            all_items = (
                follow_up_items + retention_items + loyalty_items + conflict_items
            )
            if all_items:
                await self._enrich_with_tasks_and_status(clinic_id, all_items)
                # Split back per kind preserving original ordering
                follow_up_items = [i for i in all_items if i.kind == "follow_up"]
                retention_items = [i for i in all_items if i.kind == "retention_gap"]
                conflict_items = [i for i in all_items if i.kind == "conflict"]
        except Exception:
            business_chain_tasks_attention_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                error_type="build_feed_error",
            ).inc()
            business_chain_tasks_attention_duration_seconds.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
            ).observe((utc_now() - started_at).total_seconds())
            raise

        business_chain_tasks_attention_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
        ).observe((utc_now() - started_at).total_seconds())
        business_chain_tasks_attention_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            status="success",
        ).inc()
        return AttentionFeedRead(
            follow_up=follow_up_items,
            retention_gap=retention_items + loyalty_items,
            conflicts=conflict_items,
        )

    async def _build_follow_up_items(self, clinic_id: UUID) -> list[AttentionItemRead]:
        """Items based on explicit follow-up flags on chat messages + ERP issues."""
        # Используем naive UTC, чтобы тип параметра совпадал с колонкой в БД.
        now = utc_now_naive()
        stmt: Select[tuple[ChatMessage]] = (
            select(ChatMessage)
            .where(
                ChatMessage.clinic_id == clinic_id,
                ChatMessage.follow_up_at.is_not(None),
                ChatMessage.follow_up_closed.is_(False),
                ChatMessage.follow_up_at <= now,
            )
            .order_by(ChatMessage.follow_up_at.asc())
            .limit(FOLLOW_UP_MAX_ITEMS)
        )
        result = await self.session.execute(stmt)
        messages: list[ChatMessage] = list(result.scalars().all())

        # ERP-проблемы по бронированиям (например, нет кассы/политики/склада/остатков).
        erp_stmt: Select[tuple[Booking]] = (
            select(Booking)
            .where(
                Booking.clinic_id == clinic_id,
                Booking.erp_error_code.is_not(None),
            )
            .order_by(Booking.appointment_date.desc())
            .limit(FOLLOW_UP_MAX_ITEMS)
        )
        erp_result = await self.session.execute(erp_stmt)
        erp_bookings: list[Booking] = list(erp_result.scalars().all())

        if not messages and not erp_bookings:
            return []

        patient_ids = {
            m.patient_id for m in messages if m.patient_id is not None
        } | {b.patient_id for b in erp_bookings if b.patient_id is not None}
        conversation_ids = {m.conversation_id for m in messages}

        patients_map = await self._load_patients(patient_ids)
        conversations_map = await self._load_conversations(conversation_ids)
        admin_map = await self._load_admins(
            {c.assigned_admin_id for c in conversations_map.values() if c.assigned_admin_id is not None}
        )
        latest_admin_comments = await self._load_latest_admin_comments(conversation_ids)

        items: list[AttentionItemRead] = []

        # Follow-up по сообщениям
        for m in messages:
            patient = patients_map.get(m.patient_id) if m.patient_id is not None else None
            conv = conversations_map.get(m.conversation_id)
            admin = admin_map.get(conv.assigned_admin_id) if conv and conv.assigned_admin_id else None
            comment = latest_admin_comments.get(m.conversation_id)

            patient_full_name = patient.full_name if patient else None
            patient_phone = patient.phone if patient else ""
            title = f"Перезвонить: {patient_full_name or patient_phone or 'Пациент'}"
            description = (m.follow_up_reason or m.body or "").strip()
            if len(description) > 240:
                description = description[:237] + "..."

            has_comment = comment is not None
            last_comment_preview: str | None = None
            if comment is not None:
                body = (comment.body or "").replace("\n", " ").strip()
                if body:
                    last_comment_preview = body[:120]

            items.append(
                AttentionItemRead(
                    id=m.id,
                    clinic_id=m.clinic_id,
                    patient_id=m.patient_id if m.patient_id is not None else (patient.id if patient else UUID(int=0)),
                    kind="follow_up",
                    title=title,
                    description=description,
                    priority=80,
                    due_at=m.follow_up_at,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                    patient_full_name=patient_full_name,
                    patient_phone=patient_phone,
                    patient_tags=[],
                    status="open" if not m.follow_up_closed else "resolved",
                    assigned_admin_id=conv.assigned_admin_id if conv else None,
                    assigned_admin_name=admin.full_name if admin else None,
                    has_comment=has_comment,
                    last_comment_preview=last_comment_preview,
                    conversation_id=m.conversation_id,
                )
            )

        # Follow-up по ошибкам ERP при завершении визитов
        for b in erp_bookings:
            patient = patients_map.get(b.patient_id)
            patient_full_name = patient.full_name if patient else None
            patient_phone = patient.phone if patient else ""
            title = f"ERP ошибка по визиту: {patient_full_name or patient_phone or 'Пациент'}"
            description = f"Код ошибки ERP: {b.erp_error_code or 'unknown'}. Проверьте настройки касс/ЗП/склада."

            items.append(
                AttentionItemRead(
                    id=b.id,
                    clinic_id=b.clinic_id,
                    patient_id=b.patient_id,
                    kind="follow_up",
                    title=title,
                    description=description,
                    priority=85,
                    due_at=None,
                    created_at=datetime.combine(b.appointment_date, datetime.min.time()),
                    updated_at=b.updated_at,
                    patient_full_name=patient_full_name,
                    patient_phone=patient_phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=None,
                    assigned_admin_name=None,
                    has_comment=False,
                    last_comment_preview=None,
                    conversation_id=None,
                )
            )

        return items

    async def _build_retention_gap_items(self, clinic_id: UUID) -> list[AttentionItemRead]:
        """Items for patients who have not visited for a long time but brought revenue."""
        # Aggregate last visit date and total amount per patient
        stmt: Select[tuple[UUID, datetime, Decimal]] = (
            select(
                Booking.patient_id,
                func.max(Booking.appointment_date).label("last_visit_at"),
                func.coalesce(func.sum(Booking.prepayment_amount), 0).label("total_amount"),
            )
            .where(
                Booking.clinic_id == clinic_id,
                Booking.status.in_(("confirmed", "completed")),
            )
            .group_by(Booking.patient_id)
        )
        result = await self.session.execute(stmt)
        rows: list[tuple[UUID, datetime, Decimal]] = list(result.all())
        if not rows:
            return []

        # Basic threshold in days; approximation of months
        threshold_months = RETENTION_DEFAULT_MONTHS
        threshold_days = threshold_months * 30
        today = utc_now().date()

        candidates: list[tuple[UUID, datetime, Decimal]] = []
        for patient_id, last_visit_at, total_amount in rows:
            if total_amount is None or total_amount <= 0:
                continue
            if last_visit_at is None:
                continue
            days_since = (today - last_visit_at).days
            if days_since > threshold_days:
                candidates.append((patient_id, last_visit_at, total_amount))

        if not candidates:
            return []

        # Sort by total_amount desc and take top N
        candidates.sort(key=lambda x: x[2], reverse=True)
        top_candidates = candidates[:RETENTION_MAX_ITEMS]
        patient_ids = {pid for pid, _, _ in top_candidates}

        patients_map = await self._load_patients(patient_ids)
        # conversations/admins/comments are optional here; only for enrichment
        conversations_map = await self._load_conversations_by_patient(clinic_id, patient_ids)
        admin_map = await self._load_admins(
            {c.assigned_admin_id for c in conversations_map.values() if c.assigned_admin_id is not None}
        )
        latest_admin_comments = await self._load_latest_admin_comments(set(conversations_map.keys()))

        items: list[AttentionItemRead] = []
        for patient_id, last_visit_at, total_amount in top_candidates:
            patient = patients_map.get(patient_id)
            if not patient:
                continue
            conv = conversations_map.get(patient_id)
            admin = admin_map.get(conv.assigned_admin_id) if conv and conv.assigned_admin_id else None
            comment = latest_admin_comments.get(conv.id) if conv else None

            patient_full_name = patient.full_name
            patient_phone = patient.phone
            title = f"Давно не был: {patient_full_name or patient_phone}"
            description = (
                f"Последний визит: {last_visit_at.isoformat()}, "
                f"суммарная выручка: {total_amount:.0f} ₽"
            )

            has_comment = comment is not None
            last_comment_preview: str | None = None
            if comment is not None:
                body = (comment.body or "").replace("\n", " ").strip()
                if body:
                    last_comment_preview = body[:120]

            # Simple priority: higher for higher revenue
            priority = 60
            if total_amount and total_amount > 0:
                priority += min(30, int(total_amount // 10000))

            items.append(
                AttentionItemRead(
                    id=patient_id,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    kind="retention_gap",
                    title=title,
                    description=description,
                    priority=priority,
                    due_at=None,
                    created_at=datetime.combine(last_visit_at, datetime.min.time()),
                    updated_at=utc_now(),
                    patient_full_name=patient_full_name,
                    patient_phone=patient_phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=conv.assigned_admin_id if conv else None,
                    assigned_admin_name=admin.full_name if admin else None,
                    has_comment=has_comment,
                    last_comment_preview=last_comment_preview,
                    conversation_id=conv.id if conv else None,
                )
            )

        return items

    async def _load_loyalty_thresholds(self, clinic_id: UUID) -> dict[str, Decimal | int]:
        """Return per-clinic loyalty thresholds based on LoyaltyPolicy or defaults.

        This keeps business thresholds configurable without impacting ERP revenue
        accounting: we only use them to decide whom to highlight in attention feed.
        """
        result = await self.session.execute(
            select(LoyaltyPolicy).where(LoyaltyPolicy.clinic_id == clinic_id)
        )
        policy: LoyaltyPolicy | None = result.scalar_one_or_none()
        if not policy:
            return {
                "expiry_days": LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT,
                "min_remaining_visits": LOYALTY_MIN_REMAINING_VISITS_DEFAULT,
                "min_remaining_amount": LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT,
                "wallet_min_balance": LOYALTY_WALLET_MIN_BALANCE_DEFAULT,
                "inactive_days_with_balance": LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT,
            }
        # For Phase 1 we reuse points_expire_days / min_check_for_cashback as soft hints;
        # if they are not configured, we fall back to defaults.
        expiry_days = policy.points_expire_days or LOYALTY_EXPIRY_DAYS_THRESHOLD_DEFAULT
        wallet_min_balance = (
            policy.min_check_for_cashback or LOYALTY_WALLET_MIN_BALANCE_DEFAULT
        )
        return {
            "expiry_days": expiry_days,
            "min_remaining_visits": LOYALTY_MIN_REMAINING_VISITS_DEFAULT,
            "min_remaining_amount": LOYALTY_MIN_REMAINING_AMOUNT_DEFAULT,
            "wallet_min_balance": wallet_min_balance,
            "inactive_days_with_balance": LOYALTY_INACTIVE_DAYS_WITH_BALANCE_DEFAULT,
        }

    async def _build_loyalty_loyalty_gap_items(
        self,
        clinic_id: UUID,
    ) -> list[AttentionItemRead]:
        """Items for patients with loyalty balances (subscriptions/wallet) that risk not being used.

        Phase 1: simple heuristics without heavy joins:
        - subscriptions that are close to expires_at;
        - wallets with positive balance.
        """
        today = utc_now().date()
        thresholds = await self._load_loyalty_thresholds(clinic_id)
        expiry_days = int(thresholds["expiry_days"])
        min_remaining_visits = int(thresholds["min_remaining_visits"])
        min_remaining_amount = Decimal(thresholds["min_remaining_amount"])
        wallet_min_balance = Decimal(thresholds["wallet_min_balance"])
        inactive_days_with_balance = int(thresholds["inactive_days_with_balance"])

        # Subscriptions close to expiry and those с существенными остатками и
        # длительным отсутствием визитов.
        subs_stmt: Select[tuple[CustomerSubscription]] = (
            select(CustomerSubscription)
            .where(
                CustomerSubscription.clinic_id == clinic_id,
                CustomerSubscription.status == "active",
            )
            .limit(RETENTION_MAX_ITEMS * 2)
        )
        subs_result = await self.session.execute(subs_stmt)
        subs: list[CustomerSubscription] = list(subs_result.scalars().all())

        expiring_subs: list[CustomerSubscription] = []
        balance_but_inactive_patient_ids: set[UUID] = set()

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

            if s.expires_at is not None:
                days_left = (s.expires_at.date() - today).days
                if 0 <= days_left <= expiry_days:
                    expiring_subs.append(s)
                    continue

            # Отдельно отметим пациентов с существенными остатками, у которых давно не было визитов.
            balance_but_inactive_patient_ids.add(s.patient_id)

        # Wallets with positive balance.
        wallets_stmt: Select[tuple[Wallet]] = (
            select(Wallet)
            .where(
                Wallet.clinic_id == clinic_id,
                Wallet.balance >= wallet_min_balance,
            )
            .limit(RETENTION_MAX_ITEMS * 2)
        )
        wallets_result = await self.session.execute(wallets_stmt)
        wallets: list[Wallet] = list(wallets_result.scalars().all())

        if not expiring_subs and not wallets and not balance_but_inactive_patient_ids:
            return []

        patient_ids: set[UUID] = {s.patient_id for s in expiring_subs} | {
            w.patient_id for w in wallets
        } | balance_but_inactive_patient_ids

        # Посчитаем, когда пациент последний раз был в клинике (по завершённым визитам).
        last_visit_stmt: Select[tuple[UUID, date]] = (
            select(
                Booking.patient_id,
                func.max(Booking.appointment_date).label("last_visit"),
            )
            .where(
                Booking.clinic_id == clinic_id,
                Booking.patient_id.in_(patient_ids),
                Booking.status.in_(("confirmed", "completed")),
            )
            .group_by(Booking.patient_id)
        )
        last_visit_result = await self.session.execute(last_visit_stmt)
        last_visit_map: dict[UUID, date] = {
            row[0]: row[1] for row in last_visit_result.all() if row[0] is not None
        }

        patients_map = await self._load_patients(patient_ids)

        items: list[AttentionItemRead] = []

        for s in expiring_subs:
            patient = patients_map.get(s.patient_id)
            if not patient:
                continue
            days_left = (s.expires_at.date() - today).days if s.expires_at else None
            title = f"Скоро сгорит абонемент: {patient.full_name or patient.phone}"
            description = (
                f"Абонемент истекает {s.expires_at.date().isoformat()} "
                f"({days_left} дн. осталось). "
                f"Остаток визитов: {s.remaining_visits or 0}, "
                f"остаток суммы: {s.remaining_amount or Decimal('0')}."
            )
            items.append(
                AttentionItemRead(
                    id=s.id,
                    clinic_id=clinic_id,
                    patient_id=s.patient_id,
                    kind="retention_gap",
                    title=title,
                    description=description,
                    priority=80,
                    due_at=None,
                    created_at=s.purchased_at,
                    updated_at=s.activated_at or s.purchased_at,
                    patient_full_name=patient.full_name,
                    patient_phone=patient.phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=None,
                    assigned_admin_name=None,
                    has_comment=False,
                    last_comment_preview=None,
                    conversation_id=None,
                )
            )

        for w in wallets:
            patient = patients_map.get(w.patient_id)
            if not patient or w.balance < wallet_min_balance:
                continue
            title = f"У клиента есть баллы: {patient.full_name or patient.phone}"
            description = (
                f"Баланс кошелька: {w.balance} {w.currency}. "
                "Клиент давно не был в клинике — предложите записаться и использовать баллы."
            )
            items.append(
                AttentionItemRead(
                    id=w.id,
                    clinic_id=clinic_id,
                    patient_id=w.patient_id,
                    kind="retention_gap",
                    title=title,
                    description=description,
                    priority=70,
                    due_at=None,
                    created_at=w.updated_at,
                    updated_at=w.updated_at,
                    patient_full_name=patient.full_name,
                    patient_phone=patient.phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=None,
                    assigned_admin_name=None,
                    has_comment=False,
                    last_comment_preview=None,
                    conversation_id=None,
                )
            )

        # Дополнительный слой: клиенты с существенными остатками по подпискам,
        # у которых давно не было визитов, даже если срок действия ещё не близко к истечению.
        for patient_id in balance_but_inactive_patient_ids:
            patient = patients_map.get(patient_id)
            if not patient:
                continue
            last_visit = last_visit_map.get(patient_id)
            if not last_visit:
                continue
            days_since = (today - last_visit).days
            if days_since < inactive_days_with_balance:
                continue
            title = f"Неиспользованные абонементы: {patient.full_name or patient.phone}"
            description = (
                f"У пациента есть активные абонементы с остатками, "
                f"но последний визит был {last_visit.isoformat()} "
                f"({days_since} дн. назад). Предложите записаться и использовать пакет."
            )
            items.append(
                AttentionItemRead(
                    id=patient_id,
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    kind="retention_gap",
                    title=title,
                    description=description,
                    priority=65,
                    due_at=None,
                    created_at=datetime.combine(last_visit, datetime.min.time()),
                    updated_at=utc_now(),
                    patient_full_name=patient.full_name,
                    patient_phone=patient.phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=None,
                    assigned_admin_name=None,
                    has_comment=False,
                    last_comment_preview=None,
                    conversation_id=None,
                )
            )

        return items

    async def _enrich_with_tasks_and_status(
        self,
        clinic_id: UUID,
        items: list[AttentionItemRead],
    ) -> None:
        """Attach aggregated task info and compute attention status for each item.

        Mapping rules (tasks ↔ attention feed):
        - new: нет связанных задач
        - in_progress: есть хотя бы одна задача open|in_progress
        - resolved: все задачи done|cancelled
        - archived: зарезервирован под отдельное явное действие (пока не реализовано)
        """
        if not items:
            return

        stmt: Select[tuple[Task]] = (
            select(Task)
            .where(Task.clinic_id == clinic_id)
            .where(
                func.row(
                    Task.attention_kind,
                    Task.attention_ref_id,
                ).in_(
                    [
                        (item.kind, item.id)
                        for item in items
                    ]
                )
            )
        )
        result = await self.session.execute(stmt)
        tasks: list[Task] = list(result.scalars().all())

        by_key: dict[tuple[str, UUID], list[Task]] = defaultdict(list)
        for t in tasks:
            if t.attention_kind and t.attention_ref_id:
                by_key[(t.attention_kind, t.attention_ref_id)].append(t)

        for item in items:
            key = (item.kind, item.id)
            related = by_key.get(key, [])
            if not related:
                item.tasks_total = 0
                item.tasks_open = 0
                item.tasks_in_progress = 0
                item.tasks_done = 0
                item.tasks_cancelled = 0
                # Если из исходных данных уже выставлен статус resolved (например, follow_up_closed),
                # не понижаем его до new.
                if item.status not in ("resolved", "archived"):
                    item.status = "new"
                continue

            total = len(related)
            open_count = sum(1 for t in related if t.status == "open")
            in_progress_count = sum(1 for t in related if t.status == "in_progress")
            done_count = sum(1 for t in related if t.status == "done")
            cancelled_count = sum(1 for t in related if t.status == "cancelled")

            item.tasks_total = total
            item.tasks_open = open_count
            item.tasks_in_progress = in_progress_count
            item.tasks_done = done_count
            item.tasks_cancelled = cancelled_count

            if open_count > 0 or in_progress_count > 0:
                item.status = "in_progress"
            elif total > 0 and done_count + cancelled_count == total:
                item.status = "resolved"
            elif item.status not in ("resolved", "archived"):
                item.status = "new"

    async def _build_conflict_items(self, clinic_id: UUID) -> list[AttentionItemRead]:
        """Items for conflict / complaint clients.

        V1: базируемся только на сообщениях пациента с негативной лексикой за последние 30 дней.
        """
        # created_at в БД хранится как naive timestamp, поэтому используем utc_now_naive
        now = utc_now_naive()
        since = now - timedelta(days=30)
        # Простая эвристика по тексту сообщения; при появлении тегов можно заменить.
        negative_keywords = ("жалоб", "недовол", "плохо", "ужас", "отврат", "скандал")

        stmt: Select[tuple[ChatMessage]] = (
            select(ChatMessage)
            .where(
                ChatMessage.clinic_id == clinic_id,
                ChatMessage.sender_type == "patient",
                ChatMessage.created_at >= since,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(500)
        )
        result = await self.session.execute(stmt)
        candidate_messages: list[ChatMessage] = list(result.scalars().all())
        if not candidate_messages:
            return []

        per_patient: dict[UUID, ChatMessage] = {}
        for m in candidate_messages:
            if m.patient_id is None:
                continue
            body_lower = (m.body or "").lower()
            if not any(k in body_lower for k in negative_keywords):
                continue
            # берём самое свежее сообщение на пациента
            if m.patient_id not in per_patient:
                per_patient[m.patient_id] = m

        if not per_patient:
            return []

        # Ограничиваем количество
        items_messages = list(per_patient.values())[:CONFLICT_MAX_ITEMS]
        patient_ids = {m.patient_id for m in items_messages if m.patient_id is not None}
        conversation_ids = {m.conversation_id for m in items_messages}

        patients_map = await self._load_patients(patient_ids)
        conversations_map = await self._load_conversations(conversation_ids)
        admin_map = await self._load_admins(
            {c.assigned_admin_id for c in conversations_map.values() if c.assigned_admin_id is not None}
        )
        latest_admin_comments = await self._load_latest_admin_comments(conversation_ids)

        items: list[AttentionItemRead] = []
        for m in items_messages:
            if m.patient_id is None:
                continue
            patient = patients_map.get(m.patient_id)
            if not patient:
                continue
            conv = conversations_map.get(m.conversation_id)
            admin = admin_map.get(conv.assigned_admin_id) if conv and conv.assigned_admin_id else None
            comment = latest_admin_comments.get(m.conversation_id)

            patient_full_name = patient.full_name
            patient_phone = patient.phone
            title = f"Конфликт/жалоба: {patient_full_name or patient_phone}"
            description = (m.body or "").strip()
            if len(description) > 240:
                description = description[:237] + "..."

            has_comment = comment is not None
            last_comment_preview: str | None = None
            if comment is not None:
                body = (comment.body or "").replace("\n", " ").strip()
                if body:
                    last_comment_preview = body[:120]

            items.append(
                AttentionItemRead(
                    id=m.patient_id,
                    clinic_id=clinic_id,
                    patient_id=m.patient_id,
                    kind="conflict",
                    title=title,
                    description=description,
                    priority=95,
                    due_at=None,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                    patient_full_name=patient_full_name,
                    patient_phone=patient_phone,
                    patient_tags=[],
                    status="open",
                    assigned_admin_id=conv.assigned_admin_id if conv else None,
                    assigned_admin_name=admin.full_name if admin else None,
                    has_comment=has_comment,
                    last_comment_preview=last_comment_preview,
                    conversation_id=m.conversation_id,
                )
            )

        return items

    async def close_follow_up(self, clinic_id: UUID, message_id: UUID) -> bool:
        """Mark follow-up on a chat message as closed."""
        stmt = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.clinic_id == clinic_id,
            ChatMessage.follow_up_at.is_not(None),
        )
        result = await self.session.execute(stmt)
        msg: ChatMessage | None = result.scalars().first()
        if msg is None:
            return False
        if msg.follow_up_closed:
            return True
        msg.follow_up_closed = True
        msg.updated_at = utc_now()
        self.session.add(msg)
        await self.session.commit()
        return True

    async def _load_patients(self, patient_ids: Iterable[UUID]) -> dict[UUID, Patient]:
        ids = [pid for pid in patient_ids if pid is not None]
        if not ids:
            return {}
        stmt: Select[tuple[Patient]] = select(Patient).where(Patient.id.in_(ids))
        result = await self.session.execute(stmt)
        return {p.id: p for p in result.scalars().all()}

    async def _load_conversations(self, conversation_ids: Iterable[UUID]) -> dict[UUID, Conversation]:
        ids = [cid for cid in conversation_ids if cid is not None]
        if not ids:
            return {}
        stmt: Select[tuple[Conversation]] = select(Conversation).where(Conversation.id.in_(ids))
        result = await self.session.execute(stmt)
        return {c.id: c for c in result.scalars().all()}

    async def _load_conversations_by_patient(
        self,
        clinic_id: UUID,
        patient_ids: Iterable[UUID],
    ) -> dict[UUID, Conversation]:
        ids = [pid for pid in patient_ids if pid is not None]
        if not ids:
            return {}
        stmt: Select[tuple[Conversation]] = select(Conversation).where(
            Conversation.clinic_id == clinic_id,
            Conversation.patient_id.in_(ids),
        )
        result = await self.session.execute(stmt)
        convs = list(result.scalars().all())
        by_patient: dict[UUID, Conversation] = {}
        for c in convs:
            # если несколько, берём тот, по которому была последняя активность
            existing = by_patient.get(c.patient_id)
            if existing is None or (c.last_message_at or datetime.min) > (existing.last_message_at or datetime.min):
                by_patient[c.patient_id] = c
        return by_patient

    async def _load_admins(self, admin_ids: Iterable[UUID]) -> dict[UUID, AdminUser]:
        ids = [aid for aid in admin_ids if aid is not None]
        if not ids:
            return {}
        stmt: Select[tuple[AdminUser]] = select(AdminUser).where(AdminUser.id.in_(ids))
        result = await self.session.execute(stmt)
        return {a.id: a for a in result.scalars().all()}

    async def _load_latest_admin_comments(
        self,
        conversation_ids: Iterable[UUID],
    ) -> dict[UUID, ChatMessage]:
        """Return latest admin message per conversation."""
        ids = [cid for cid in conversation_ids if cid is not None]
        if not ids:
            return {}
        stmt: Select[tuple[ChatMessage]] = (
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id.in_(ids),
                ChatMessage.sender_type == "admin",
            )
            .order_by(ChatMessage.conversation_id, ChatMessage.created_at.desc())
        )
        result = await self.session.execute(stmt)
        rows: list[ChatMessage] = list(result.scalars().all())
        latest: dict[UUID, ChatMessage] = {}
        for m in rows:
            if m.conversation_id not in latest:
                latest[m.conversation_id] = m
        return latest

    async def claim_item(
        self,
        clinic_id: UUID,
        item_type: str,
        item_id: UUID,
        admin_id: UUID,
    ) -> bool:
        """Assign feed item to current admin (claim). task: set Task.assignee_id; follow_up: assign conversation or acknowledge ERP."""
        if item_type == "task":
            task = await self.session.get(Task, item_id)
            if not task or task.clinic_id != clinic_id:
                return False
            task.assignee_id = admin_id
            await self.session.flush()
            return True

        if item_type == "follow_up":
            msg = await self.session.get(ChatMessage, item_id)
            if msg and msg.clinic_id == clinic_id:
                conv = await self.session.get(Conversation, msg.conversation_id)
                if conv and conv.clinic_id == clinic_id:
                    conv.assigned_admin_id = admin_id
                    await self.session.flush()
                    return True
            booking = await self.session.get(Booking, item_id)
            if booking and booking.clinic_id == clinic_id and booking.erp_error_code:
                return True
            return False

        return False