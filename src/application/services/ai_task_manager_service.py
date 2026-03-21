"""AI Task Manager: collect context, analyze signals, generate tasks.

Execution-first MVP (TASKS_AI_021):
- deterministic rule-based analyzer for a few high-signal scenarios
- generator applies per-clinic AiTaskSettings and simple daily limits

LLM-based analysis is intentionally optional and not required for core behaviour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
import uuid
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.ai_task_manager_dto import (
    AnalysisContext,
    CreatedTaskResult,
    ProposedTask,
    TASK_SOURCES_AI_AUTO,
    TASK_SOURCES_AI_SUGGESTED,
)
from src.application.services.ai_task_settings_service import AiTaskSettingsService
from src.application.dto.lead_lifecycle_dto import LeadEventStale
from src.application.services.lead_lifecycle_service import LeadLifecycleService
from src.application.services.task_service import TaskService
from src.core.metrics import (
    ai_task_manager_created_total,
    ai_task_manager_duration_seconds,
    ai_task_manager_errors_total,
    ai_task_manager_proposed_total,
    ai_task_manager_skipped_total,
)
from src.domain.entities.ai_task_settings import AiTaskSettings
from src.domain.entities.booking import Booking
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.task import Task
from src.domain.interfaces.repositories.task_repository import TaskRepository


logger = logging.getLogger(__name__)

AI_TASK_MANAGER_NAMESPACE = uuid.UUID("4b8b2a2a-7c8e-4c3b-b5cc-4b3f6f0b2b9a")

SUPPORTED_TASK_CLASSES = {
    "booking.no_show_pattern",
    "booking.erp_errors_cluster",
    "crm.stale_leads",
}


def _utc_midnight(dt: datetime) -> datetime:
    dt_utc = dt.astimezone(timezone.utc)
    return datetime(dt_utc.year, dt_utc.month, dt_utc.day, tzinfo=timezone.utc)


@dataclass(frozen=True)
class CollectedData:
    context: AnalysisContext
    # existing tasks keyed by (attention_kind, attention_ref_id) for dedup
    existing_attention_task_keys: set[tuple[str, UUID]]


class AiTaskContextCollector:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def collect(self, clinic_id: UUID) -> CollectedData:
        """
        Collect signals without loading personal data into memory.

        Important: we intentionally DO NOT call AttentionFeedService.get_feed(), because it
        enriches items with patient names/phones and other PII. For AI Task Manager we only
        need minimal signal identifiers and counters.
        """
        now = datetime.now(timezone.utc)

        # Minimal attention-like keys derived from underlying entities (no PII):
        # - follow_up signals are chat_messages with follow_up_at due and not closed.
        from src.domain.entities.chat_message import ChatMessage

        follow_up_stmt = (
            select(ChatMessage.id)
            .where(
                ChatMessage.clinic_id == clinic_id,
                ChatMessage.follow_up_at.is_not(None),
                ChatMessage.follow_up_closed.is_(False),
                ChatMessage.follow_up_at <= now.replace(tzinfo=None),
            )
            .order_by(ChatMessage.follow_up_at.asc())
            .limit(200)
        )
        follow_up_res = await self._session.execute(follow_up_stmt)
        follow_up_ids = [row[0] for row in follow_up_res.all() if row[0] is not None]

        keys: list[tuple[str, UUID]] = [("follow_up", fid) for fid in follow_up_ids]
        existing_keys: set[tuple[str, UUID]] = set()
        if keys:
            stmt: Select[tuple[Task]] = (
                select(Task)
                .where(Task.clinic_id == clinic_id)
                .where(
                    func.row(Task.attention_kind, Task.attention_ref_id).in_(keys)
                )
                .where(Task.status.in_(("open", "in_progress")))
            )
            res = await self._session.execute(stmt)
            tasks = list(res.scalars().all())
            for t in tasks:
                if t.attention_kind and t.attention_ref_id:
                    existing_keys.add((t.attention_kind, t.attention_ref_id))

        # Signals from domain tables (rule-based MVP).
        signals: dict = {
            "attention": {
                "items": [{"kind": "follow_up", "ref_id": str(fid), "priority": 80} for fid in follow_up_ids],
                "total": len(follow_up_ids),
            }
        }

        # No-show patterns (per patient, window days).
        no_show_window_days = 30
        no_show_since = now - timedelta(days=no_show_window_days)
        no_show_stmt = (
            select(Booking.patient_id, func.count(Booking.id))
            .where(
                Booking.clinic_id == clinic_id,
                Booking.status == "no_show",
                Booking.updated_at >= no_show_since,
            )
            .group_by(Booking.patient_id)
        )
        no_show_res = await self._session.execute(no_show_stmt)
        no_show_counts = {row[0]: int(row[1]) for row in no_show_res.all() if row[0] is not None}
        signals["booking_no_show_counts"] = {str(pid): cnt for pid, cnt in no_show_counts.items()}

        # ERP errors window for clinic.
        erp_error_window_days = 1
        erp_since = now - timedelta(days=erp_error_window_days)
        erp_stmt = (
            select(func.count(Booking.id))
            .where(
                Booking.clinic_id == clinic_id,
                Booking.erp_error_code.is_not(None),
                Booking.updated_at >= erp_since,
            )
        )
        erp_res = await self._session.execute(erp_stmt)
        erp_errors_count = int(erp_res.scalar_one() or 0)
        signals["erp_errors_count"] = erp_errors_count

        # Stale CRM leads.
        stale_leads_days = 7
        stale_since = now - timedelta(days=stale_leads_days)
        leads_stmt = (
            select(LeadCard.id)
            .where(
                LeadCard.clinic_id == clinic_id,
                LeadCard.status == "open",
                LeadCard.updated_at < stale_since,
            )
            .limit(200)
        )
        leads_res = await self._session.execute(leads_stmt)
        stale_lead_ids = [row[0] for row in leads_res.all() if row[0] is not None]
        signals["stale_lead_ids"] = [str(x) for x in stale_lead_ids]

        ctx = AnalysisContext(
            clinic_id=clinic_id,
            attention_items_total=len(follow_up_ids),
            signals=signals,
        )
        return CollectedData(context=ctx, existing_attention_task_keys=existing_keys)


class AiTaskAnalyzer:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def analyze(
        self,
        *,
        context: AnalysisContext,
        existing_attention_task_keys: set[tuple[str, UUID]],
        settings: AiTaskSettings,
    ) -> list[ProposedTask]:
        """Return proposed tasks for a clinic based on signals and thresholds."""
        # Optional LLM-assisted branch (safe-by-default). Fallback to rules on any error.
        thresholds = settings.analyzer_thresholds or {}
        llm_enabled = bool(thresholds.get("llm_enabled", False))
        if llm_enabled and self._session is not None:
            try:
                from src.application.ai.tools_registry import get_tool
                from src.application.ai.tools_base import ToolContext
                from src.application.services.booking_service import BookingService
                from src.application.services.schedule_service import ScheduleService
                from src.core.context import RequestContext
                from src.application.ai.tools_tasks import AnalyzeAttentionForTasksArgs, AnalyzeAttentionForTasksResult

                tool = get_tool("analyze_attention_for_tasks")
                if tool is not None:
                    req_ctx = RequestContext(
                        clinic_id=context.clinic_id,
                        user_id=None,
                        user_type="system",
                        trace_id=None,
                        roles=set(),
                        permissions={"ai.tasks.run"},
                    )
                    tool_ctx = ToolContext(
                        db=self._session,
                        clinic_id=context.clinic_id,
                        request_context=req_ctx,
                        source="ai_task_manager",
                        booking_service=BookingService(self._session),
                        schedule_service=ScheduleService(self._session),
                        patient_service=None,
                    )
                    args = AnalyzeAttentionForTasksArgs(
                        clinic_id=context.clinic_id,
                        signals=context.signals,
                        allowed_task_classes=list(settings.allowed_task_classes or []),
                        creation_mode=settings.creation_mode,
                        existing_attention_task_keys=[
                            f"{k}#{v}" for (k, v) in sorted(existing_attention_task_keys, key=lambda x: (x[0], str(x[1])))
                        ],
                    )
                    res = await tool(tool_ctx, args)  # type: ignore[misc]
                    if isinstance(res, ToolError):
                        raise RuntimeError(res.code)
                    if isinstance(res, AnalyzeAttentionForTasksResult) and res.success:
                        return res.proposed
            except Exception:
                # Fall back to deterministic rules.
                pass

        proposed: list[ProposedTask] = []
        clinic_id = context.clinic_id

        no_show_min_count = int(thresholds.get("no_show_min_count", 2))
        no_show_window_days = int(thresholds.get("no_show_window_days", 30))
        erp_error_min_count = int(thresholds.get("erp_error_min_count", 3))
        erp_error_window_days = int(thresholds.get("erp_error_window_days", 1))
        stale_leads_min_count = int(thresholds.get("stale_leads_min_count", 10))
        stale_leads_days = int(thresholds.get("stale_leads_days", 7))

        allowed = set(settings.allowed_task_classes or [])
        allow_all = not allowed

        def _allowed(cls: str) -> bool:
            return cls in SUPPORTED_TASK_CLASSES and (allow_all or cls in allowed)

        # 1) No-show pattern per patient.
        if _allowed("booking.no_show_pattern"):
            counts = context.signals.get("booking_no_show_counts") or {}
            for raw_pid, cnt in counts.items():
                if int(cnt) < no_show_min_count:
                    continue
                patient_id = UUID(raw_pid)
                # Tie to retention_gap kind (patient_id is used as id in attention feed for retention items).
                attention_key = ("retention_gap", patient_id)
                if attention_key in existing_attention_task_keys:
                    continue
                proposed.append(
                    ProposedTask(
                        clinic_id=clinic_id,
                        task_class="booking.no_show_pattern",
                        title="Частые no-show: связаться с пациентом",
                        description=f"У пациента {no_show_min_count}+ no-show за период. Проверьте причины и подтвердите будущие визиты.",
                        priority="high",
                        role_assignee="manager",
                        patient_id=patient_id,
                        attention_kind="retention_gap",
                        attention_ref_id=patient_id,
                        requires_confirmation=(settings.creation_mode != "auto"),
                    )
                )

        # 2) ERP errors cluster for clinic (creates 1 task per clinic per day; dedup by attention key (follow_up, clinic_id) is not available).
        if _allowed("booking.erp_errors_cluster"):
            erp_errors_count = int(context.signals.get("erp_errors_count") or 0)
            if erp_errors_count >= erp_error_min_count:
                proposed.append(
                    ProposedTask(
                        clinic_id=clinic_id,
                        task_class="booking.erp_errors_cluster",
                        title="Проверить ERP-интеграцию: много ошибок за сутки",
                        description=f"За последние сутки обнаружено ERP-ошибок по визитам: {erp_errors_count}. Проверьте кассы/политики/склад и повторную обработку.",
                        priority="urgent",
                        role_assignee="manager",
                        requires_confirmation=(settings.creation_mode != "auto"),
                    )
                )

        # 3) Stale leads cluster.
        if _allowed("crm.stale_leads"):
            stale_lead_ids = context.signals.get("stale_lead_ids") or []
            if isinstance(stale_lead_ids, list) and len(stale_lead_ids) >= stale_leads_min_count:
                # Create a task linked to first lead for navigation, but scoped as cluster.
                lead_id = UUID(stale_lead_ids[0])
                proposed.append(
                    ProposedTask(
                        clinic_id=clinic_id,
                        task_class="crm.stale_leads",
                        title="CRM: лиды без движения",
                        description=f"Есть {len(stale_lead_ids)} лидов без движения. Проверьте этапы/ответственных и настройте SLA обработки.",
                        priority="high",
                        role_assignee="manager",
                        lead_id=lead_id,
                        requires_confirmation=(settings.creation_mode != "auto"),
                    )
                )

        return proposed


class AiTaskGenerator:
    def __init__(self, task_service: TaskService, repo: TaskRepository, session: AsyncSession) -> None:
        self._task_service = task_service
        self._repo = repo
        self._session = session

    async def generate(
        self,
        *,
        proposed_tasks: list[ProposedTask],
        settings: AiTaskSettings,
    ) -> list[CreatedTaskResult]:
        if not proposed_tasks:
            return []

        now = datetime.now(timezone.utc)
        today_utc = _utc_midnight(now)

        # Count how many AI tasks already created today in this clinic (best-effort limits).
        stmt_total = (
            select(func.count(Task.id))
            .where(
                Task.clinic_id == settings.clinic_id,
                Task.created_at >= today_utc,
                Task.source.in_((TASK_SOURCES_AI_SUGGESTED, TASK_SOURCES_AI_AUTO)),
            )
        )
        res_total = await self._session.execute(stmt_total)
        created_today_total = int(res_total.scalar_one() or 0)

        # Per-patient created today (AI sources only).
        stmt_pat = (
            select(Task.patient_id, func.count(Task.id))
            .where(
                Task.clinic_id == settings.clinic_id,
                Task.created_at >= today_utc,
                Task.source.in_((TASK_SOURCES_AI_SUGGESTED, TASK_SOURCES_AI_AUTO)),
                Task.patient_id.is_not(None),
            )
            .group_by(Task.patient_id)
        )
        res_pat = await self._session.execute(stmt_pat)
        created_today_by_patient = {row[0]: int(row[1]) for row in res_pat.all() if row[0] is not None}

        # Per-doctor limit (best-effort): map doctor_id -> tasks count for tasks linked to bookings.
        stmt_doc = (
            select(Booking.doctor_id, func.count(Task.id))
            .select_from(Task)
            .join(Booking, Booking.id == Task.booking_id)
            .where(
                Task.clinic_id == settings.clinic_id,
                Task.created_at >= today_utc,
                Task.source.in_((TASK_SOURCES_AI_SUGGESTED, TASK_SOURCES_AI_AUTO)),
                Task.booking_id.is_not(None),
            )
            .group_by(Booking.doctor_id)
        )
        res_doc = await self._session.execute(stmt_doc)
        created_today_by_doctor = {row[0]: int(row[1]) for row in res_doc.all() if row[0] is not None}

        # Preload idempotency keys already present (open/in_progress only).
        stmt_existing_event_ids = (
            select(Task.source_event_id)
            .where(
                Task.clinic_id == settings.clinic_id,
                Task.status.in_(("open", "in_progress")),
                Task.source.in_((TASK_SOURCES_AI_SUGGESTED, TASK_SOURCES_AI_AUTO)),
                Task.source_event_id.is_not(None),
            )
        )
        res_existing = await self._session.execute(stmt_existing_event_ids)
        existing_event_ids: set[UUID] = {row[0] for row in res_existing.all() if row[0] is not None}

        results: list[CreatedTaskResult] = []
        for p in proposed_tasks:
            if not settings.ai_tasks_enabled:
                ai_task_manager_skipped_total.labels(
                    clinic_id=str(settings.clinic_id),
                    reason="disabled",
                ).inc()
                continue

            if created_today_total >= max(0, int(settings.daily_clinic_limit or 0)):
                ai_task_manager_skipped_total.labels(
                    clinic_id=str(settings.clinic_id),
                    reason="clinic_limit",
                ).inc()
                continue

            # Idempotency: prevent duplicates for cluster-style tasks.
            # For per-entity tasks we still allow new items when the key changes (e.g. next day).
            key_date = date.today()
            natural_key = f"{p.task_class}:{p.clinic_id}:{key_date.isoformat()}:{p.patient_id or ''}:{p.lead_id or ''}:{p.booking_id or ''}"
            event_id = uuid.uuid5(AI_TASK_MANAGER_NAMESPACE, natural_key)
            if event_id in existing_event_ids:
                ai_task_manager_skipped_total.labels(
                    clinic_id=str(settings.clinic_id),
                    reason="duplicate",
                ).inc()
                continue

            if p.patient_id is not None:
                current = created_today_by_patient.get(p.patient_id, 0)
                if current >= max(0, int(settings.daily_patient_limit or 0)):
                    ai_task_manager_skipped_total.labels(
                        clinic_id=str(settings.clinic_id),
                        reason="patient_limit",
                    ).inc()
                    continue

            if p.role_assignee == "doctor" and p.booking_id is not None:
                booking = await self._session.get(Booking, p.booking_id)
                if booking is not None and booking.doctor_id is not None:
                    current_doc = created_today_by_doctor.get(booking.doctor_id, 0)
                    if current_doc >= max(0, int(settings.daily_doctor_limit or 0)):
                        ai_task_manager_skipped_total.labels(
                            clinic_id=str(settings.clinic_id),
                            reason="doctor_limit",
                        ).inc()
                        continue

            # Respect per-proposal confirmation requirement.
            if p.requires_confirmation:
                source = TASK_SOURCES_AI_SUGGESTED
            else:
                source = TASK_SOURCES_AI_AUTO if settings.creation_mode == "auto" else TASK_SOURCES_AI_SUGGESTED
            # In confirm mode keep suggestions less intrusive.
            effective_priority = p.priority
            if source == TASK_SOURCES_AI_SUGGESTED and effective_priority in {"urgent", "high"}:
                effective_priority = "medium"

            created = await self._task_service.create_task(
                clinic_id=p.clinic_id,
                title=p.title,
                description=p.description,
                priority=effective_priority,
                role_assignee=p.role_assignee,
                due_at=p.due_at,
                booking_id=p.booking_id,
                patient_id=p.patient_id,
                lead_id=p.lead_id,
                source=source,
                source_event_id=event_id,
                attention_kind=p.attention_kind,
                attention_ref_id=p.attention_ref_id,
            )
            created_today_total += 1
            if created.patient_id is not None:
                created_today_by_patient[created.patient_id] = created_today_by_patient.get(created.patient_id, 0) + 1
            if created.booking_id is not None:
                booking = await self._session.get(Booking, created.booking_id)
                if booking is not None and booking.doctor_id is not None:
                    created_today_by_doctor[booking.doctor_id] = created_today_by_doctor.get(booking.doctor_id, 0) + 1

            ai_task_manager_created_total.labels(
                clinic_id=str(created.clinic_id),
                source=created.source,
                task_class=p.task_class,
            ).inc()

            results.append(
                CreatedTaskResult(
                    task_id=created.id,
                    source=created.source,
                    clinic_id=created.clinic_id,
                    created_at=created.created_at,
                    proposal_class=p.task_class,
                )
            )
            existing_event_ids.add(event_id)

        return results


class AiTaskManagerRunner:
    """Orchestrates: load settings -> collect -> analyze -> generate."""

    def __init__(self, session: AsyncSession, task_service: TaskService, task_repo: TaskRepository) -> None:
        self._session = session
        self._task_service = task_service
        self._task_repo = task_repo

    async def run_for_clinic(self, clinic_id: UUID) -> list[CreatedTaskResult]:
        started = datetime.now(timezone.utc)
        run_trace_id = str(uuid.uuid4())
        try:
            settings_svc = AiTaskSettingsService(self._session)
            settings = await settings_svc.get_or_create_default(clinic_id)
            if not settings.ai_tasks_enabled:
                return []

            collector = AiTaskContextCollector(self._session)
            collected = await collector.collect(clinic_id)

            # Best-effort: mark stale leads stage as "stale" when possible (CRM_EVENTS_007).
            try:
                stale_ids = (collected.context.signals or {}).get("stale_lead_ids") or []
                if isinstance(stale_ids, list) and stale_ids:
                    lifecycle = LeadLifecycleService(self._session)
                    for raw in stale_ids[:50]:
                        try:
                            lid = UUID(str(raw))
                        except Exception:
                            continue
                        await lifecycle.handle_stale_lead(
                            LeadEventStale(
                                clinic_id=clinic_id,
                                lead_id=lid,
                                trace_id=run_trace_id,
                                source="ai_task_manager",
                            )
                        )
            except Exception:
                # Never break task manager due to CRM lifecycle housekeeping.
                logger.exception(
                    "ai_task_manager stale lead stage update failed",
                    extra={"clinic_id": str(clinic_id), "trace_id": run_trace_id},
                )

            analyzer = AiTaskAnalyzer(self._session)
            proposed = await analyzer.analyze(
                context=collected.context,
                existing_attention_task_keys=collected.existing_attention_task_keys,
                settings=settings,
            )
            for p in proposed:
                ai_task_manager_proposed_total.labels(
                    clinic_id=str(clinic_id),
                    task_class=p.task_class,
                ).inc()

            generator = AiTaskGenerator(self._task_service, self._task_repo, self._session)
            created = await generator.generate(proposed_tasks=proposed, settings=settings)
            await self._session.commit()
            logger.info(
                "ai_task_manager completed",
                extra={
                    "clinic_id": str(clinic_id),
                    "trace_id": run_trace_id,
                    "proposed": len(proposed),
                    "created_count": len(created),
                },
            )
            return created
        except Exception as exc:
            await self._session.rollback()
            ai_task_manager_errors_total.labels(
                clinic_id=str(clinic_id),
                error_type=exc.__class__.__name__,
            ).inc()
            logger.exception(
                "ai_task_manager failed",
                extra={"clinic_id": str(clinic_id), "trace_id": run_trace_id},
            )
            raise
        finally:
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            ai_task_manager_duration_seconds.labels(clinic_id=str(clinic_id)).observe(elapsed)

