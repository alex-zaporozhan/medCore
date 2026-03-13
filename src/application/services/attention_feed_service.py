"""Service that builds the owner's attention feed."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.attention_feed_dto import AttentionFeedRead, AttentionItemRead
from src.core.datetime_utils import utc_now, utc_now_naive
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.conversation import Conversation
from src.domain.entities.patient import Patient


RETENTION_DEFAULT_MONTHS = 6
FOLLOW_UP_MAX_ITEMS = 200
RETENTION_MAX_ITEMS = 50
CONFLICT_MAX_ITEMS = 50


class AttentionFeedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_feed(self, clinic_id: UUID) -> AttentionFeedRead:
        follow_up_items = await self._build_follow_up_items(clinic_id)
        retention_items = await self._build_retention_gap_items(clinic_id)
        conflict_items = await self._build_conflict_items(clinic_id)
        return AttentionFeedRead(
            follow_up=follow_up_items,
            retention_gap=retention_items,
            conflicts=conflict_items,
        )

    async def _build_follow_up_items(self, clinic_id: UUID) -> list[AttentionItemRead]:
        """Items based on explicit follow-up flags on chat messages."""
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
        if not messages:
            return []

        patient_ids = {m.patient_id for m in messages if m.patient_id is not None}
        conversation_ids = {m.conversation_id for m in messages}

        patients_map = await self._load_patients(patient_ids)
        conversations_map = await self._load_conversations(conversation_ids)
        admin_map = await self._load_admins(
            {c.assigned_admin_id for c in conversations_map.values() if c.assigned_admin_id is not None}
        )
        latest_admin_comments = await self._load_latest_admin_comments(conversation_ids)

        items: list[AttentionItemRead] = []
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

            status = "open" if not m.follow_up_closed else "done"

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
                    status=status,
                    assigned_admin_id=conv.assigned_admin_id if conv else None,
                    assigned_admin_name=admin.full_name if admin else None,
                    has_comment=has_comment,
                    last_comment_preview=last_comment_preview,
                    conversation_id=m.conversation_id,
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

