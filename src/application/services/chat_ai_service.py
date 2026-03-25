"""AI assistant for admin chat and patient insights."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.chat_ai_dto import (
    ConversationSummaryResponse,
    PatientAiInsight,
    SuggestReplyResponse,
)
from src.application.services.chat_service import ChatService
from src.core.context import RequestContext
from src.core.config import settings
from src.core.datetime_utils import utc_now
from src.core.metrics import omni_ai_provider_errors_total
from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient
from src.infrastructure.external_apis.ai_client import AiClientError
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient
from src.application.services.ai_client_factory import build_safe_ai_client


logger = logging.getLogger(__name__)


class ChatAiServiceError(Exception):
    """High-level error for AI assistant operations."""

    pass


class ChatAiService:
    def __init__(self, session: AsyncSession, ctx: RequestContext, ai_client: SafeAiClient | None = None) -> None:
        self.session = session
        self.ctx = ctx
        # ai_client is expected to be provided via factory in new code paths;
        # legacy call sites will lazily create SafeAiClient on first use.
        self.ai_client = ai_client
        self.chat_service = ChatService(session)

    async def _ensure_ai_client(self) -> None:
        """Lazily initialize SafeAiClient using centralized factory."""
        if self.ai_client is not None:
            return
        clinic_id = self.ctx.clinic_id or self.ctx.user_id  # type: ignore[assignment]
        safe_client, ctx = await build_safe_ai_client(clinic_id=clinic_id, session=self.session)  # type: ignore[arg-type]
        logger.info(
            "build_safe_ai_client used for chat_ai_service",
            extra={
                "source": "chat_ai",
                "clinic_id": str(clinic_id) if clinic_id else None,
                "provider_type": ctx.provider_type,
                "allow_personal_data": ctx.allow_personal_data,
            },
        )
        self.ai_client = safe_client

    def _base_ai_mode(self) -> str:
        """Return base AI mode for current configuration."""
        return "external_active" if self.ai_client.is_configured() else "fallback_local"

    async def summarize_conversation(self, clinic_id: UUID, conversation_id: UUID) -> ConversationSummaryResponse:
        await self._ensure_ai_client()
        # Reuse existing chat service to fetch last messages
        messages_resp = await self.chat_service.list_messages_for_admin(
            clinic_id=clinic_id,
            conversation_id=conversation_id,
            cursor=None,
            limit=100,
        )
        base_mode = self._base_ai_mode()
        if messages_resp is None or not messages_resp.items:
            return ConversationSummaryResponse(
                summary="Диалог пока пустой или недоступен.",
                ai_status=base_mode,
            )

        # Build plain-text transcript
        lines: list[str] = []
        for m in messages_resp.items:
            role = "КЛИЕНТ" if m.sender_type == "patient" else "АДМИН"
            body = (m.body or "").strip()
            if not body:
                continue
            lines.append(f"{role}: {body}")
        transcript = "\n".join(lines[-50:])

        def _heuristic_summary() -> ConversationSummaryResponse:
            if not transcript:
                return ConversationSummaryResponse(
                    summary="В диалоге пока нет текстовых сообщений.",
                    ai_status="fallback_local",
                )
            total = len(messages_resp.items)
            last = messages_resp.items[-1]
            who = "пациент" if last.sender_type == "patient" else "администратор"
            return ConversationSummaryResponse(
                summary=(
                    f"Небольшой диалог на {total} сообщений. "
                    f"Последним писал {who}. "
                    "Подключите внешний AI‑провайдер (AI_PROVIDER_BASE_URL), чтобы получать развернутые резюме."
                ),
                ai_status="fallback_local",
            )

        # If no external AI configured, return simple heuristic summary
        if not self.ai_client or not self.ai_client.is_configured():
            logger.info(
                "AI summary fallback: provider not configured",
                extra={"clinic_id": str(clinic_id), "conversation_id": str(conversation_id)},
            )
            return _heuristic_summary()

        system_prompt = (
            "Ты помощник администратора клиники. "
            "Проанализируй диалог и верни строго JSON со структурой: "
            '{"summary": "...", "sentiment": "negative|neutral|positive", '
            '"main_issue": "price|schedule|service|doctor|payment|other", '
            '"is_conflict": true|false, "is_resolved": true|false, '
            '"suggested_actions": ["...", "..."]}. Не добавляй пояснений вне JSON.'
        )
        user_content = f"История диалога:\n{transcript}"

        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 300,
        }

        try:
            data = await self.ai_client.complete(payload)
        except AiClientError as exc:
            # External AI not reachable/misconfigured — use heuristic instead of 5xx.
            omni_ai_provider_errors_total.labels(
                source="legacy_chat_ai_summary",
                error_type="ai_client_error",
            ).inc()
            logger.warning(
                "AI summary fallback: AiClientError",
                extra={
                    "clinic_id": str(clinic_id),
                    "conversation_id": str(conversation_id),
                    "error": str(exc),
                },
            )
            return _heuristic_summary()
        except Exception:  # noqa: BLE001
            # Any unexpected error from external AI: also fall back to heuristic summary.
            omni_ai_provider_errors_total.labels(
                source="legacy_chat_ai_summary",
                error_type="unexpected_error",
            ).inc()
            logger.exception(
                "AI summary fallback: unexpected error",
                extra={"clinic_id": str(clinic_id), "conversation_id": str(conversation_id)},
            )
            return _heuristic_summary()

        content = _extract_message_content(data) or ""
        try:
            import json

            parsed = json.loads(content)
            dto = ConversationSummaryResponse.model_validate(parsed)
        except Exception:
            summary = content or "Не удалось получить сводку диалога от AI."
            dto = ConversationSummaryResponse(summary=summary)
        dto.ai_status = base_mode
        return dto

    async def suggest_reply(
        self,
        clinic_id: UUID,
        conversation_id: UUID,
        admin_id: UUID | None,
        intent: str | None,
    ) -> SuggestReplyResponse:
        await self._ensure_ai_client()
        base_mode = self._base_ai_mode()
        messages_resp = await self.chat_service.list_messages_for_admin(
            clinic_id=clinic_id,
            conversation_id=conversation_id,
            cursor=None,
            limit=20,
        )
        if messages_resp is None or not messages_resp.items:
            return SuggestReplyResponse(
                variants=["Диалог пока пустой. Сначала поздоровайтесь с пациентом."],
                ai_status=base_mode,
            )

        lines: list[str] = []
        for m in messages_resp.items[-10:]:
            role = "КЛИЕНТ" if m.sender_type == "patient" else "АДМИН"
            body = (m.body or "").strip()
            if not body:
                continue
            lines.append(f"{role}: {body}")
        transcript = "\n".join(lines)

        def _local_suggest() -> SuggestReplyResponse:
            # Simple local suggestion: echo polite confirmation based on last patient message.
            last_patient = next(
                (m for m in reversed(messages_resp.items) if m.sender_type == "patient"),
                None,
            )
            base = "Ответьте вежливо и уточните детали записи."
            if last_patient and last_patient.body:
                base = f"Клиент написал: «{last_patient.body}». Ответьте вежливо и уточните детали."
            return SuggestReplyResponse(variants=[base], ai_status="fallback_local")

        if not self.ai_client or not self.ai_client.is_configured():
            logger.info(
                "AI suggest_reply fallback: provider not configured",
                extra={
                    "clinic_id": str(clinic_id),
                    "conversation_id": str(conversation_id),
                    "admin_id": str(admin_id) if admin_id else None,
                },
            )
            return _local_suggest()

        intent_str = intent or "auto"
        system_prompt = (
            "Ты помогаешь администратору клиники отвечать клиентам. "
            "Верни строго JSON вида {\"variants\": [\"ответ1\", \"ответ2\", \"ответ3\"]} без пояснений. "
            "Ответы должны быть короткими, вежливыми и без медицинских рекомендаций. "
            "Не обещай скидок или услуг, которых нет в тексте. Не используй агрессивный тон."
        )
        user_content = (
            f"Последние сообщения в диалоге:\n{transcript}\n\n"
            f"Намерение администратора: {intent_str}."
        )
        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 256,
        }

        try:
            data = await self.ai_client.complete(payload)
        except Exception:  # noqa: BLE001
            # Любая ошибка внешнего AI (включая сетевые/401 и т.п.) — локальный fallback без 5xx.
            omni_ai_provider_errors_total.labels(
                source="legacy_chat_ai_suggest_reply",
                error_type="unexpected_error",
            ).inc()
            logger.exception(
                "AI suggest_reply fallback: error from provider",
                extra={
                    "clinic_id": str(clinic_id),
                    "conversation_id": str(conversation_id),
                    "admin_id": str(admin_id) if admin_id else None,
                },
            )
            return _local_suggest()

        content = _extract_message_content(data) or ""
        try:
            import json

            parsed = json.loads(content)
            dto = SuggestReplyResponse.model_validate(parsed)
        except Exception:
            dto = SuggestReplyResponse(
                variants=["Не удалось получить подсказку. Напишите ответ вручную."],
            )
        dto.ai_status = base_mode
        return dto

    async def analyze_patient(self, clinic_id: UUID, patient_id: UUID) -> PatientAiInsight:
        await self._ensure_ai_client()
        base_mode = self._base_ai_mode()
        patient = await self._load_patient(patient_id, clinic_id)
        if patient is None:
            raise ChatAiServiceError("Patient not found")

        stats = await self._aggregate_patient_stats(clinic_id, patient_id)
        visits_count, last_visit, total_revenue, cancelled_count, no_show_count = stats

        # Local heuristic insight builder (used when AI is disabled or fails).
        def _heuristic_insight() -> PatientAiInsight:
            summary_parts: list[str] = []
            summary_parts.append(
                f"Клиент {patient.full_name or patient.phone} совершил(а) {visits_count} визитов."
            )
            if last_visit:
                summary_parts.append(f"Последний визит: {last_visit.isoformat()}.")
            if total_revenue:
                summary_parts.append(f"Суммарная выручка: около {total_revenue:.0f} ₽.")
            if no_show_count:
                summary_parts.append(f"Есть {no_show_count} неявок.")
            if cancelled_count:
                summary_parts.append(f"Есть {cancelled_count} отмен.")

            risk_flags: list[str] = []
            if no_show_count >= 2:
                risk_flags.append("no_show_often")
            if total_revenue and total_revenue > 100_000:
                risk_flags.append("high_value")

            nba: str | None = None
            if visits_count and last_visit and (utc_now().date() - last_visit).days > 180:
                nba = "Пригласить на профилактический осмотр в ближайшее время."

            return PatientAiInsight(
                summary=" ".join(summary_parts),
                risk_flags=risk_flags,
                next_best_action=nba,
                ai_status="fallback_local",
            )

        # If external AI is not configured at all, always return heuristic.
        if not self.ai_client or not self.ai_client.is_configured():
            logger.info(
                "AI analyze_patient fallback: provider not configured",
                extra={"clinic_id": str(clinic_id), "patient_id": str(patient_id)},
            )
            return _heuristic_insight()

        try:
            system_prompt = (
                "Ты помогаешь владельцу и администратору клиники понять профиль клиента и следующий шаг. "
                "Верни строго JSON со структурой: "
                '{"summary": "...", "risk_flags": ["...", "..."], "next_best_action": "... или null"}. '
                "Не добавляй пояснений вне JSON."
            )
            stats_text = _format_patient_stats_for_prompt(
                patient=patient,
                visits_count=visits_count,
                last_visit=last_visit,
                total_revenue=total_revenue,
                cancelled_count=cancelled_count,
                no_show_count=no_show_count,
            )
            user_content = f"Данные по клиенту:\n{stats_text}"

            payload = {
                "model": settings.ai_provider_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 256,
            }

            data = await self.ai_client.complete(payload)
        except AiClientError as exc:
            # External AI failed (e.g. network/auth) — fall back to heuristic instead of 5xx.
            omni_ai_provider_errors_total.labels(
                source="legacy_chat_ai_analyze_patient",
                error_type="ai_client_error",
            ).inc()
            logger.warning(
                "AI analyze_patient fallback: AiClientError",
                extra={
                    "clinic_id": str(clinic_id),
                    "patient_id": str(patient_id),
                    "error": str(exc),
                },
            )
            return _heuristic_insight()
        except Exception:  # noqa: BLE001
            # Any other unexpected error from external AI: also fall back to heuristic.
            omni_ai_provider_errors_total.labels(
                source="legacy_chat_ai_analyze_patient",
                error_type="unexpected_error",
            ).inc()
            logger.exception(
                "AI analyze_patient fallback: unexpected error",
                extra={"clinic_id": str(clinic_id), "patient_id": str(patient_id)},
            )
            return _heuristic_insight()

        content = _extract_message_content(data) or ""
        try:
            import json

            parsed = json.loads(content)
            dto = PatientAiInsight.model_validate(parsed)
        except Exception:
            # fallback: сохранить текст как summary без структурирования
            dto = PatientAiInsight(
                summary=content or "Не удалось получить обзор от AI.",
                risk_flags=[],
                next_best_action=None,
            )
        dto.ai_status = base_mode
        return dto

    async def _load_patient(self, patient_id: UUID, clinic_id: UUID) -> Patient | None:
        stmt: Select[tuple[Patient]] = select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _aggregate_patient_stats(
        self,
        clinic_id: UUID,
        patient_id: UUID,
    ) -> tuple[int, date | None, Decimal | None, int, int]:
        """Return (visits_count, last_visit_date, total_revenue, cancelled_count, no_show_count)."""
        stmt: Select[tuple[int, date, Decimal, int, int]] = select(
            func.count().label("visits_count"),
            func.max(Booking.appointment_date).label("last_visit_date"),
            func.coalesce(func.sum(Booking.prepayment_amount), 0).label("total_revenue"),
            func.sum(case((Booking.status == "cancelled", 1), else_=0)).label("cancelled_count"),
            func.sum(case((Booking.status == "no_show", 1), else_=0)).label("no_show_count"),
        ).where(
            Booking.clinic_id == clinic_id,
            Booking.patient_id == patient_id,
            Booking.status.in_(("confirmed", "completed", "cancelled", "no_show")),
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return 0, None, None, 0, 0
        visits_count, last_visit_date, total_revenue, cancelled_count, no_show_count = row
        return (
            int(visits_count or 0),
            last_visit_date,
            total_revenue,
            int(cancelled_count or 0),
            int(no_show_count or 0),
        )


def _extract_message_content(data: dict) -> str:
    """Extract `choices[0].message.content` from generic chat-completions response."""
    try:
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return str(content)
    except Exception:  # noqa: BLE001
        return ""


def _format_patient_stats_for_prompt(
    *,
    patient: Patient,
    visits_count: int,
    last_visit: date | None,
    total_revenue: Decimal | None,
    cancelled_count: int,
    no_show_count: int,
) -> str:
    lines: list[str] = []
    # Avoid sending raw name/phone to external AI – keep only aggregated behavioral data.
    lines.append("Идентификатор клиента не раскрывается. Используй только агрегированные данные ниже.")
    lines.append(f"Количество визитов: {visits_count}.")
    if last_visit:
        lines.append(f"Последний визит: {last_visit.isoformat()}.")
    if total_revenue is not None:
        lines.append(f"Суммарная выручка: примерно {total_revenue:.0f} ₽.")
    if cancelled_count:
        lines.append(f"Отменено визитов: {cancelled_count}.")
    if no_show_count:
        lines.append(f"Неявок (no-show): {no_show_count}.")
    return "\n".join(lines)

