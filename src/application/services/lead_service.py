"""LeadService for CRM Kanban (pipelines, stages, leads, notes).

Money semantics (CRM_MONEY_008):
- ``estimated_value`` is a CRM forecast (e.g. catalog price of linked booking), not an ERP fact.
- ``actual_value`` is copied from ERP income (``financial_transactions``) only; CRM does not
  accrue revenue from raw payment events.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai.tokenization import make_lead_token
from src.application.dto.crm_ai_dto import LeadContextForAi, LeadSummary
from src.application.events.event_bus import get_event_bus
from src.application.events.standard_events import make_lead_stage_changed_event
from src.core.ai_sanitizer import AiSanitizer
from src.core.context import RequestContext
from src.core.prometheus_labels import clinic_bucket_label
from src.core.metrics import (
    crm_ai_recommendations_total,
    crm_lead_actual_value_erp_missing_fact_total,
    crm_lead_actual_value_erp_updates_total,
    crm_leads_created_total,
    crm_lead_stage_transitions_total,
    crm_lead_time_to_close_seconds,
)
from src.application.services.erp_reports_repository import ErpReportsRepository
from src.application.services.lead_stage_semantics_service import LeadStageSemanticsService
from src.application.services.lead_stage_state_machine import LeadStageStateMachine
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.service import Service
from src.domain.entities.lead_note import LeadNote
from src.domain.entities.task import Task
from src.domain.interfaces.repositories.lead_repository import LeadRepository
from src.infrastructure.database.lead_repo_impl import LeadRepositoryImpl

logger = logging.getLogger(__name__)


class SemanticTransitionBlockedError(Exception):
    """Raised when enforce_semantic_transition is True and the move violates the stage state machine."""

    def __init__(self, from_semantic: str, to_semantic: str) -> None:
        self.from_semantic = from_semantic
        self.to_semantic = to_semantic
        super().__init__(f"semantic_transition_invalid:{from_semantic}->{to_semantic}")


class LeadService:
    """Application service for CRM leads and pipelines."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository: LeadRepository = LeadRepositoryImpl(session)
        self._erp_reports = ErpReportsRepository(session)
        self.stage_sm = LeadStageStateMachine()
        self.stage_semantics = LeadStageSemanticsService(session)

    async def _booking_ids_for_erp_actual(
        self,
        lead: LeadCard,
        extra_booking_ids: list[UUID] | None,
    ) -> list[UUID]:
        ids: set[UUID] = set(extra_booking_ids or [])
        if lead.primary_booking_id:
            ids.add(lead.primary_booking_id)
        secondary = await self.repository.list_secondary_booking_ids_for_lead(
            lead.clinic_id, lead.id
        )
        ids.update(secondary)
        return list(ids)

    # Pipelines & stages (Phase 1 – только чтение)
    async def get_default_pipeline_id(self, clinic_id: UUID) -> UUID | None:
        pipeline = await self.repository.get_default_pipeline(clinic_id)
        return pipeline.id if pipeline else None

    async def list_pipelines(self, clinic_id: UUID):
        return await self.repository.list_pipelines(clinic_id)

    async def list_stages_for_pipeline(self, clinic_id: UUID, pipeline_id: UUID):
        return await self.repository.list_stages_for_pipeline(clinic_id, pipeline_id)

    # Leads
    async def list_leads(
        self,
        clinic_id: UUID,
        stage_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        search: str | None = None,
        patient_id: UUID | None = None,
        booking_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        *,
        kanban_projection: bool = False,
    ) -> tuple[list[LeadCard], int]:
        return await self.repository.list_leads(
            clinic_id=clinic_id,
            stage_id=stage_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            source=source,
            search=search,
            patient_id=patient_id,
            booking_id=booking_id,
            skip=skip,
            limit=limit,
            kanban_projection=kanban_projection,
        )

    async def list_leads_cursor(
        self,
        clinic_id: UUID,
        stage_id: UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source: str | None = None,
        search: str | None = None,
        patient_id: UUID | None = None,
        booking_id: UUID | None = None,
        cursor_token: str | None = None,
        limit: int = 50,
        *,
        kanban_projection: bool = False,
    ) -> tuple[list[LeadCard], str | None, int | None]:
        return await self.repository.list_leads_cursor(
            clinic_id=clinic_id,
            stage_id=stage_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            source=source,
            search=search,
            patient_id=patient_id,
            booking_id=booking_id,
            cursor_token=cursor_token,
            limit=limit,
            kanban_projection=kanban_projection,
        )

    async def get_lead_details(self, clinic_id: UUID, lead_id: UUID) -> tuple[LeadCard, list[LeadNote]] | None:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            return None
        notes = await self.repository.list_notes_for_lead(clinic_id, lead_id)
        return lead, notes

    async def create_lead_from_contact(
        self,
        clinic_id: UUID,
        omnichannel_contact_id: UUID | None,
        patient_id: UUID | None,
        title: str,
        source: str,
        estimated_value: Decimal | None = None,
        *,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
    ) -> LeadCard:
        default_pipeline = await self.repository.get_default_pipeline(clinic_id)
        if not default_pipeline:
            raise RuntimeError("Default lead pipeline is not configured for clinic")

        stages = await self.repository.list_stages_for_pipeline(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
        )
        if not stages:
            raise RuntimeError("Lead stages are not configured for default pipeline")

        first_stage = sorted(stages, key=lambda s: s.order)[0]
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
            stage_id=first_stage.id,
            omnichannel_contact_id=omnichannel_contact_id,
            patient_id=patient_id,
            primary_booking_id=None,
            title=title,
            source=source,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            estimated_value=estimated_value or Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        lead = await self.repository.create_lead(lead)
        logger.info(
            "[CRM] Lead created from contact",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "contact_id": str(omnichannel_contact_id) if omnichannel_contact_id else None,
                "patient_id": str(patient_id) if patient_id else None,
            },
        )
        crm_leads_created_total.labels(
            clinic_id=str(clinic_id),
            source=str(source or "unknown"),
            utm_campaign=str(getattr(lead, "utm_campaign", None) or "none"),
        ).inc()
        return lead

    async def create_lead_for_patient_booking(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        booking_id: UUID,
        *,
        omnichannel_contact_id: UUID | None = None,
        source: str = "booking",
    ) -> LeadCard:
        """Create open lead when first booking appears without a prior CRM card (CRM_EVENTS_007)."""
        default_pipeline = await self.repository.get_default_pipeline(clinic_id)
        if not default_pipeline:
            raise RuntimeError("Default lead pipeline is not configured for clinic")

        stages = await self.repository.list_stages_for_pipeline(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
        )
        if not stages:
            raise RuntimeError("Lead stages are not configured for default pipeline")

        first_stage = sorted(stages, key=lambda s: s.order)[0]
        title = f"Запись ({booking_id})"
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=default_pipeline.id,
            stage_id=first_stage.id,
            omnichannel_contact_id=omnichannel_contact_id,
            patient_id=patient_id,
            primary_booking_id=booking_id,
            title=title,
            source=source,
            estimated_value=Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        lead = await self.repository.create_lead(lead)
        logger.info(
            "[CRM] Lead created from booking (no prior open lead)",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "patient_id": str(patient_id),
                "booking_id": str(booking_id),
            },
        )
        crm_leads_created_total.labels(
            clinic_id=str(clinic_id),
            source=str(source or "unknown"),
            utm_campaign=str(getattr(lead, "utm_campaign", None) or "none"),
        ).inc()
        try:
            lead = await self.recalculate_estimated_value(clinic_id, lead.id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "crm_recalc_estimated_after_booking_lead_failed",
                extra={"lead_id": str(lead.id), "clinic_id": str(clinic_id)},
            )
        return lead

    async def change_lead_stage(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        new_stage_id: UUID,
        *,
        request_context: RequestContext | None = None,
        enforce_semantic: bool = False,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        stage = await self.repository.get_stage_by_id(clinic_id, new_stage_id)
        if not stage:
            raise LookupError("LeadStage not found for clinic")

        # Resolve semantics (mapping table + code infer) — same as GET .../stage-semantics resolved_stage_semantics.
        try:
            current_stage = await self.repository.get_stage_by_id(clinic_id, lead.stage_id)
            from_sem: str | None = None
            to_sem: str | None = None
            if current_stage:
                from_sem = await self.stage_semantics.get_semantic_for_stage(
                    clinic_id=clinic_id,
                    pipeline_id=lead.pipeline_id,
                    stage=current_stage,
                )
            to_sem = await self.stage_semantics.get_semantic_for_stage(
                clinic_id=clinic_id,
                pipeline_id=lead.pipeline_id,
                stage=stage,
            )
            if from_sem and to_sem and not self.stage_sm.can_transition_semantic(from_sem, to_sem):
                if enforce_semantic:
                    raise SemanticTransitionBlockedError(from_sem, to_sem)
                logger.info(
                    "crm_lead_stage_transition_nonstandard",
                    extra={
                        "clinic_id": str(clinic_id),
                        "lead_id": str(lead_id),
                        "from_stage_id": str(current_stage.id) if current_stage else None,
                        "to_stage_id": str(stage.id),
                        "from_semantic": from_sem,
                        "to_semantic": to_sem,
                        "initiator": "manual",
                    },
                )
        except SemanticTransitionBlockedError:
            raise
        except Exception:  # noqa: BLE001
            if enforce_semantic:
                logger.warning(
                    "crm_lead_stage_semantic_resolution_failed",
                    extra={"clinic_id": str(clinic_id), "lead_id": str(lead_id)},
                    exc_info=True,
                )
            # Non-strict: never block manual transition due to diagnostics.
            pass

        # Manual transition is executed via the same audited mechanism as event-driven transitions.
        ctx = request_context or RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="admin",
            trace_id=None,
            roles=set(),
            permissions=set(),
        )
        updated = await self.update_stage_from_ai(
            clinic_id=clinic_id,
            lead_id=lead_id,
            target_stage_id=new_stage_id,
            reason="manual_kanban_drag_drop",
            initiated_by_ai=False,
            request_context=ctx,
        )
        return updated

    async def attach_booking(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        booking_id: UUID,
        new_stage_id: UUID | None = None,
        new_estimated_value: Decimal | None = None,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        primary_was_empty = lead.primary_booking_id is None
        if lead.primary_booking_id is None:
            lead.primary_booking_id = booking_id
        elif booking_id != lead.primary_booking_id:
            await self.repository.add_secondary_booking_link(clinic_id, lead_id, booking_id)

        if new_stage_id is not None:
            stage = await self.repository.get_stage_by_id(clinic_id, new_stage_id)
            if not stage:
                raise LookupError("LeadStage not found for clinic")
            lead.stage_id = new_stage_id

        if new_estimated_value is not None:
            lead.estimated_value = new_estimated_value

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead booking attached",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "booking_id": str(booking_id),
                "primary_booking_id": str(lead.primary_booking_id),
            },
        )
        if new_estimated_value is None and primary_was_empty and lead.primary_booking_id is not None:
            try:
                lead = await self.recalculate_estimated_value(clinic_id, lead_id)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "crm_recalc_estimated_after_attach_failed",
                    extra={"lead_id": str(lead_id), "clinic_id": str(clinic_id)},
                )
        return lead

    async def recalculate_estimated_value(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        *,
        explicit: Decimal | None = None,
    ) -> LeadCard:
        """Set ``estimated_value`` from an explicit forecast or primary booking catalog price."""
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        if explicit is not None:
            lead.estimated_value = explicit
        elif lead.primary_booking_id is not None:
            row = await self.session.execute(
                select(Service.price)
                .select_from(Booking)
                .join(Service, Service.id == Booking.service_id)
                .where(Booking.id == lead.primary_booking_id, Booking.clinic_id == clinic_id)
                .limit(1)
            )
            price = row.scalar_one_or_none()
            if price is not None:
                lead.estimated_value = Decimal(price)

        lead = await self.repository.update_lead(lead)
        logger.info(
            "crm_lead_estimated_value_updated",
            extra={
                "clinic_id": str(clinic_id),
                "lead_id": str(lead_id),
                "estimated_value": str(lead.estimated_value),
            },
        )
        return lead

    async def append_estimated_value_compliance_audit(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        old_value: Decimal,
        new_value: Decimal,
        *,
        admin_user_id: UUID,
        trace_id: str | None,
    ) -> None:
        """Append immutable audit row when compliance mode is on and forecast changed (CRM_MONEY H6)."""
        from uuid import uuid4
        from decimal import ROUND_HALF_UP

        from src.core.config import settings
        from src.domain.entities.crm_lead_estimated_value_audit import CrmLeadEstimatedValueAudit

        if not settings.compliance_crm_audit_enabled:
            return
        q = Decimal("0.01")
        old_q = old_value.quantize(q, ROUND_HALF_UP)
        new_q = new_value.quantize(q, ROUND_HALF_UP)
        if old_q == new_q:
            return
        self.session.add(
            CrmLeadEstimatedValueAudit(
                id=uuid4(),
                clinic_id=clinic_id,
                lead_id=lead_id,
                admin_user_id=admin_user_id,
                old_estimated_value=old_q,
                new_estimated_value=new_q,
                trace_id=trace_id,
            )
        )

    async def update_actual_value_from_erp(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        *,
        trace_id: str | None = None,
        source: str = "erp_sync",
        extra_booking_ids: list[UUID] | None = None,
        request_context: RequestContext | None = None,
    ) -> LeadCard:
        """Refresh ``actual_value`` from ERP income rows (``ErpReportsRepository``)."""
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        booking_ids = await self._booking_ids_for_erp_actual(lead, extra_booking_ids)
        total = await self._erp_reports.sum_income_revenue_for_crm_lead(
            clinic_id=clinic_id,
            lead_id=lead_id,
            booking_ids=booking_ids,
        )

        effective_trace = trace_id or (request_context.trace_id if request_context else None)
        old_val = lead.actual_value or Decimal("0.00")
        changed = total != old_val
        lead.actual_value = total
        lead = await self.repository.update_lead(lead)

        crm_lead_actual_value_erp_updates_total.labels(
            clinic_id=str(clinic_id),
            source=str(source or "unknown"),
            changed="true" if changed else "false",
        ).inc()

        if total == Decimal("0.00") and booking_ids:
            st_row = await self.session.execute(
                select(Booking.status).where(
                    Booking.clinic_id == clinic_id,
                    Booking.id.in_(booking_ids),
                )
            )
            statuses = [r[0] for r in st_row.all()]
            if any(s == BookingStatus.COMPLETED for s in statuses):
                crm_lead_actual_value_erp_missing_fact_total.labels(
                    clinic_id=str(clinic_id),
                    source=str(source or "unknown"),
                ).inc()
                logger.warning(
                    "crm_lead_actual_value_erp_missing_fact",
                    extra={
                        "trace_id": effective_trace,
                        "clinic_id": str(clinic_id),
                        "lead_id": str(lead_id),
                        "source": source,
                        "booking_ids": [str(b) for b in booking_ids],
                    },
                )

        logger.info(
            "crm_lead_actual_value_from_erp",
            extra={
                "trace_id": effective_trace,
                "clinic_id": str(clinic_id),
                "lead_id": str(lead_id),
                "source": source,
                "old_actual_value": str(old_val),
                "new_actual_value": str(lead.actual_value),
                "booking_ids": [str(b) for b in booking_ids],
            },
        )
        return lead

    async def close_lead_as_success(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        success_stage_id: UUID | None,
        *,
        update_stage: bool = True,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        if update_stage:
            if success_stage_id is None:
                raise ValueError("success_stage_id is required when update_stage=True")
            stage = await self.repository.get_stage_by_id(clinic_id, success_stage_id)
            if not stage:
                raise LookupError("LeadStage not found for clinic")
            lead.stage_id = success_stage_id

        lead.status = "success"
        lead.closed_at = datetime.now(timezone.utc)

        # Time-to-close from creation to terminal status.
        try:
            delta = (lead.closed_at - lead.created_at).total_seconds() if lead.closed_at else None
            if delta is not None and delta >= 0:
                crm_lead_time_to_close_seconds.labels(
                    clinic_id=str(clinic_id),
                    outcome="success",
                ).observe(delta)
        except Exception:  # noqa: BLE001
            pass

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead closed as success",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "actual_value": str(lead.actual_value),
            },
        )
        return lead

    async def close_lead_as_lost(
        self,
        *,
        clinic_id: UUID,
        lead_id: UUID,
        lost_stage_id: UUID,
        lost_reason: str | None = None,
    ) -> LeadCard:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        stage = await self.repository.get_stage_by_id(clinic_id, lost_stage_id)
        if not stage:
            raise LookupError("LeadStage not found for clinic")

        lead.stage_id = lost_stage_id
        lead.status = "lost"
        lead.closed_at = datetime.now(timezone.utc)
        lead.lost_reason = (lost_reason or "")[:1000] if lost_reason else None

        try:
            delta = (lead.closed_at - lead.created_at).total_seconds() if lead.closed_at else None
            if delta is not None and delta >= 0:
                crm_lead_time_to_close_seconds.labels(
                    clinic_id=str(clinic_id),
                    outcome="lost",
                ).observe(delta)
        except Exception:  # noqa: BLE001
            pass

        lead = await self.repository.update_lead(lead)
        logger.info(
            "[CRM] Lead closed as lost",
            extra={
                "lead_id": str(lead.id),
                "clinic_id": str(clinic_id),
                "lost_reason": lead.lost_reason,
            },
        )
        return lead

    async def add_lead_note(
        self,
        clinic_id: UUID,
        lead_id: UUID,
        author_admin_id: UUID,
        text: str,
    ) -> LeadNote:
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        note = LeadNote(
            clinic_id=clinic_id,
            lead_id=lead_id,
            author_admin_id=author_admin_id,
            text=text,
        )
        note = await self.repository.create_note(note)
        logger.info(
            "[CRM] Lead note created",
            extra={
                "lead_id": str(lead_id),
                "clinic_id": str(clinic_id),
                "author_admin_id": str(author_admin_id),
            },
        )
        return note

    async def get_lead_context_for_ai(
        self,
        *,
        clinic_id: UUID,
        lead_id: UUID,
        allow_personal_data: bool = False,
        notes_limit: int = 3,
    ) -> LeadContextForAi:
        """
        Return aggregated lead context for AI prompts.

        Policy:
        - When allow_personal_data is False, the output must not contain raw phones/emails.
        - This method intentionally does not include patient name/phone at all.
        """
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        # Notes preview: sanitize and keep only last N items.
        notes = await self.repository.list_notes_for_lead(clinic_id, lead_id)
        sanitizer = AiSanitizer(allow_personal_data=allow_personal_data)
        preview: list[str] = []
        for n in reversed(notes[-notes_limit:]):
            body = (n.text or "").strip()
            if not body:
                continue
            sanitized = sanitizer.sanitize(body).sanitized
            sanitized = " ".join(sanitized.split())
            if len(sanitized) > 240:
                sanitized = sanitized[:237] + "..."
            preview.append(sanitized)

        # Task stats for this lead.
        stmt: Select[tuple[str, int]] = (
            select(Task.status, func.count(Task.id))
            .where(Task.clinic_id == clinic_id, Task.lead_id == lead_id)
            .group_by(Task.status)
        )
        result = await self.session.execute(stmt)
        by_status: dict[str, int] = {str(row[0]): int(row[1]) for row in result.all()}

        summary = LeadSummary(
            lead_token=make_lead_token(lead.id),
            clinic_id=lead.clinic_id,
            pipeline_id=lead.pipeline_id,
            stage_id=lead.stage_id,
            status=lead.status,
            title=lead.title,
            source=lead.source,
            estimated_value=lead.estimated_value or Decimal("0.00"),
            actual_value=lead.actual_value or Decimal("0.00"),
            created_at=lead.created_at,
            closed_at=lead.closed_at,
        )

        return LeadContextForAi(
            lead=summary,
            notes_preview=preview,
            open_tasks_count=by_status.get("open", 0),
            in_progress_tasks_count=by_status.get("in_progress", 0),
            done_tasks_count=by_status.get("done", 0),
        )

    async def update_stage_from_ai(
        self,
        *,
        clinic_id: UUID,
        lead_id: UUID,
        target_stage_id: UUID,
        reason: str | None,
        initiated_by_ai: bool,
        request_context: RequestContext | None,
    ) -> LeadCard:
        """
        Update lead stage with explicit audit metadata.

        This method enforces the same clinic boundary and stage existence checks as the
        regular change_lead_stage flow and additionally verifies that stage belongs to
        the same pipeline as the lead.
        """
        lead = await self.repository.get_lead_by_id(clinic_id, lead_id)
        if not lead:
            raise LookupError("Lead not found")

        if lead.status != "open":
            raise ValueError("Cannot change stage for a closed lead")

        stage = await self.repository.get_stage_by_id(clinic_id, target_stage_id)
        if not stage:
            raise LookupError("LeadStage not found for clinic")
        if stage.pipeline_id != lead.pipeline_id:
            raise ValueError("Target stage does not belong to the lead pipeline")

        if initiated_by_ai:
            current_stage = await self.repository.get_stage_by_id(clinic_id, lead.stage_id)
            if current_stage is None:
                raise LookupError("Current LeadStage not found for clinic")
            from_sem = await self.stage_semantics.get_semantic_for_stage(
                clinic_id=clinic_id,
                pipeline_id=lead.pipeline_id,
                stage=current_stage,
            )
            to_sem = await self.stage_semantics.get_semantic_for_stage(
                clinic_id=clinic_id,
                pipeline_id=lead.pipeline_id,
                stage=stage,
            )
            # If semantics are configured/inferrable, enforce matrix.
            if from_sem and to_sem:
                self.stage_sm.assert_transition_semantic(from_sem, to_sem)
            else:
                # Backward-compatible fallback when pipeline has custom codes not mapped yet:
                # allow only next-stage-by-order to avoid sudden hard blocks.
                if stage.id != current_stage.id and stage.order != (current_stage.order + 1):
                    raise ValueError("Stage semantics are not configured; fallback allows only next stage by order")

        prev_stage_id = lead.stage_id
        lead.stage_id = target_stage_id
        updated = await self.repository.update_lead(lead)

        # Publish domain event (best-effort, non-blocking for CRM write path).
        try:
            bus = get_event_bus()
            await bus.publish(
                make_lead_stage_changed_event(
                    clinic_id=clinic_id,
                    lead_id=lead_id,
                    prev_stage_id=prev_stage_id,
                    target_stage_id=target_stage_id,
                    initiated_by_ai=bool(initiated_by_ai),
                    reason=reason,
                    trace_id=request_context.trace_id if request_context else None,
                    actor_type=request_context.user_type if request_context else None,
                    actor_id=request_context.user_id if request_context else None,
                )
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "crm_lead_stage_changed_event_publish_failed",
                extra={
                    "clinic_id": str(clinic_id),
                    "lead_id": str(lead_id),
                    "prev_stage_id": str(prev_stage_id),
                    "target_stage_id": str(target_stage_id),
                },
            )

        logger.info(
            "crm_lead_stage_updated",
            extra={
                "trace_id": request_context.trace_id if request_context else None,
                "clinic_id": str(clinic_id),
                "lead_id": str(lead_id),
                "prev_stage_id": str(prev_stage_id),
                "target_stage_id": str(target_stage_id),
                "initiated_by_ai": bool(initiated_by_ai),
                "reason": (reason or "")[:500] if reason else None,
                "actor_type": request_context.user_type if request_context else None,
                "actor_id": str(request_context.user_id) if request_context and request_context.user_id else None,
            },
        )

        # Metrics: stage transitions (manual / event-driven / AI apply here).
        try:
            # Semantics are optional; keep cardinality low.
            prev_stage = await self.repository.get_stage_by_id(clinic_id, prev_stage_id)
            to_stage = stage
            from_sem = None
            to_sem = None
            if prev_stage is not None:
                from_sem = await self.stage_semantics.get_semantic_for_stage(
                    clinic_id=clinic_id,
                    pipeline_id=lead.pipeline_id,
                    stage=prev_stage,
                )
            if to_stage is not None:
                to_sem = await self.stage_semantics.get_semantic_for_stage(
                    clinic_id=clinic_id,
                    pipeline_id=lead.pipeline_id,
                    stage=to_stage,
                )
            crm_lead_stage_transitions_total.labels(
                clinic_id=str(clinic_id),
                from_semantic=str(from_sem or "unknown"),
                to_semantic=str(to_sem or "unknown"),
                initiator=("ai" if initiated_by_ai else (request_context.user_type if request_context else "unknown")),
            ).inc()
        except Exception:  # noqa: BLE001
            pass

        if initiated_by_ai:
            crm_ai_recommendations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                kind="stage",
                outcome="accepted",
            ).inc()
        return updated

