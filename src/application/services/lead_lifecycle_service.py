from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.lead_lifecycle_dto import (
    LIFECYCLE_EVENT_BOOKING_CANCELLED,
    LIFECYCLE_EVENT_BOOKING_CREATED,
    LIFECYCLE_EVENT_NO_SHOW,
    LIFECYCLE_EVENT_STALE,
    LIFECYCLE_EVENT_VISIT_COMPLETED,
    LeadEventBookingCancelled,
    LeadEventBookingCreated,
    LeadEventContactCreated,
    LeadEventNoShow,
    LeadEventStale,
    LeadEventVisitCompleted,
)
from src.application.services.lead_service import LeadService
from src.application.services.lead_stage_semantics_service import LeadStageSemanticsService
from src.core.context import RequestContext
from src.core.metrics import (
    crm_lead_booking_onboarded_total,
    crm_lead_lifecycle_transitions_total,
    crm_lead_stale_handled_total,
    crm_lead_visit_completion_outcomes_total,
)

logger = logging.getLogger(__name__)


class LeadLifecycleService:
    """
    Event-driven lead lifecycle transitions (CRM_EVENTS_007).

    Uses LeadStage.code mapping with best-effort fallback:
    - if target stage code doesn't exist in pipeline, no stage change is applied.
    - stage transitions are executed via LeadService.update_stage_from_ai(initiated_by_ai=False)
      so they are validated by the stage state-machine but not counted as AI acceptance.

    Semantic / stage resolution: ``LeadStageSemanticsService`` + DB map ``lead_stage_semantic_map``;
    transition rules: ``LeadStageStateMachine`` inside ``LeadService``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.leads = LeadService(session)
        self.semantics = LeadStageSemanticsService(session)

    async def handle_contact_created(self, event: LeadEventContactCreated) -> None:
        """
        Create lead when new omnichannel contact is created (if patient is not linked yet).
        """
        if not (event.clinic_id and event.contact_id):
            return
        if event.patient_id is not None:
            return

        existing = await self.leads.repository.find_open_lead_for_contact_or_patient(
            clinic_id=event.clinic_id,
            omnichannel_contact_id=event.contact_id,
            patient_id=None,
        )
        if existing:
            return

        title = f"Новый лид из чата ({event.contact_id})"
        await self.leads.create_lead_from_contact(
            clinic_id=event.clinic_id,
            omnichannel_contact_id=event.contact_id,
            patient_id=None,
            title=title,
            source=event.source or "omnichannel",
            estimated_value=None,
            utm_source=event.utm_source,
            utm_medium=event.utm_medium,
            utm_campaign=event.utm_campaign,
        )

    async def handle_booking_created(self, event: LeadEventBookingCreated) -> None:
        if not (event.clinic_id and event.patient_id and event.booking_id):
            return
        lead = await self.leads.repository.find_open_lead_for_contact_or_patient(
            clinic_id=event.clinic_id,
            omnichannel_contact_id=event.contact_id,
            patient_id=event.patient_id,
        )
        created_fresh = False
        if not lead:
            try:
                lead = await self.leads.create_lead_for_patient_booking(
                    event.clinic_id,
                    event.patient_id,
                    event.booking_id,
                    omnichannel_contact_id=event.contact_id,
                    source=event.source or "booking",
                )
                created_fresh = True
                crm_lead_booking_onboarded_total.labels(
                    clinic_id=str(event.clinic_id),
                    outcome="created_lead",
                ).inc()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "crm_lead_booking_created_no_pipeline",
                    extra={
                        "clinic_id": str(event.clinic_id),
                        "patient_id": str(event.patient_id),
                        "booking_id": str(event.booking_id),
                        "error": str(exc),
                    },
                )
                return
        else:
            crm_lead_booking_onboarded_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="existing_lead",
            ).inc()

        if not created_fresh:
            await self.leads.attach_booking(
                clinic_id=event.clinic_id,
                lead_id=lead.id,
                booking_id=event.booking_id,
                new_stage_id=None,
                new_estimated_value=None,
            )

        target = await self.semantics.get_stage_id_for_semantic(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            semantic=LeadStageSemanticsService.SEM_SCHEDULED,
        ) or await self._first_existing_stage_id(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            candidate_codes=("scheduled", "booked", "appointment", "appt"),
        )
        if target:
            await self._transition(
                clinic_id=event.clinic_id,
                lead_id=lead.id,
                target_stage_id=target,
                reason="event_booking_created",
                event_type=LIFECYCLE_EVENT_BOOKING_CREATED,
                ctx=self._ctx(event.clinic_id, event.trace_id, user_type="system"),
            )

    async def handle_visit_completed(self, event: LeadEventVisitCompleted) -> None:
        if not (event.clinic_id and event.booking_id):
            return
        lead = await self.leads.repository.get_lead_by_any_booking_id(
            clinic_id=event.clinic_id,
            booking_id=event.booking_id,
        )
        if not lead:
            return

        target = await self._first_existing_stage_id(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            candidate_codes=("success", "won", "win", "closed_won"),
        )
        target = await self.semantics.get_stage_id_for_semantic(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            semantic=LeadStageSemanticsService.SEM_WON,
        ) or target
        if not target:
            logger.warning(
                "crm_lead_visit_completed_no_won_stage",
                extra={
                    "trace_id": event.trace_id,
                    "clinic_id": str(event.clinic_id),
                    "lead_id": str(lead.id),
                    "booking_id": str(event.booking_id),
                    "chain": "crm_lifecycle",
                    "step": "resolve_target",
                },
            )
            crm_lead_visit_completion_outcomes_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="skipped_no_won_stage",
            ).inc()
            return

        ok = await self._transition(
            clinic_id=event.clinic_id,
            lead_id=lead.id,
            target_stage_id=target,
            reason="event_booking_completed",
            event_type=LIFECYCLE_EVENT_VISIT_COMPLETED,
            ctx=self._ctx(event.clinic_id, event.trace_id, user_type="system"),
        )
        if not ok:
            logger.error(
                "crm_lead_visit_completed_transition_failed_skip_close",
                extra={
                    "trace_id": event.trace_id,
                    "clinic_id": str(event.clinic_id),
                    "lead_id": str(lead.id),
                    "booking_id": str(event.booking_id),
                    "target_stage_id": str(target),
                    "chain": "crm_lifecycle",
                    "step": "transition",
                },
            )
            crm_lead_visit_completion_outcomes_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="skipped_transition_failed",
            ).inc()
            return

        await self.leads.close_lead_as_success(
            clinic_id=event.clinic_id,
            lead_id=lead.id,
            success_stage_id=target,
            update_stage=False,
        )
        await self.leads.update_actual_value_from_erp(
            clinic_id=event.clinic_id,
            lead_id=lead.id,
            trace_id=event.trace_id,
            source="lead_event_visit_completed",
            extra_booking_ids=[event.booking_id],
        )
        crm_lead_visit_completion_outcomes_total.labels(
            clinic_id=str(event.clinic_id),
            outcome="closed",
        ).inc()

    async def handle_booking_cancelled(self, event: LeadEventBookingCancelled) -> None:
        if not (event.clinic_id and event.booking_id):
            return
        lead = await self.leads.repository.get_lead_by_any_booking_id(
            clinic_id=event.clinic_id,
            booking_id=event.booking_id,
        )
        if not lead:
            return

        target = await self.semantics.get_stage_id_for_semantic(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            semantic=LeadStageSemanticsService.SEM_LOST,
        ) or await self._first_existing_stage_id(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            candidate_codes=("cancelled", "canceled", "lost", "closed_lost"),
        )
        if target:
            await self._transition(
                clinic_id=event.clinic_id,
                lead_id=lead.id,
                target_stage_id=target,
                reason="event_booking_cancelled",
                event_type=LIFECYCLE_EVENT_BOOKING_CANCELLED,
                ctx=self._ctx(event.clinic_id, event.trace_id, user_type="system"),
            )
            try:
                await self.leads.close_lead_as_lost(
                    clinic_id=event.clinic_id,
                    lead_id=lead.id,
                    lost_stage_id=target,
                    lost_reason="booking_cancelled",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "crm_lead_close_lost_failed_after_cancel_transition",
                    extra={
                        "trace_id": event.trace_id,
                        "clinic_id": str(event.clinic_id),
                        "lead_id": str(lead.id),
                        "error": str(exc),
                        "chain": "crm_lifecycle",
                        "step": "close_lost",
                    },
                )

    async def handle_no_show(self, event: LeadEventNoShow) -> None:
        if not (event.clinic_id and event.booking_id):
            return
        lead = await self.leads.repository.get_lead_by_any_booking_id(
            clinic_id=event.clinic_id,
            booking_id=event.booking_id,
        )
        if not lead:
            return

        target = await self.semantics.get_stage_id_for_semantic(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            semantic=LeadStageSemanticsService.SEM_LOST,
        ) or await self._first_existing_stage_id(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            candidate_codes=("no_show", "noshow", "lost", "closed_lost"),
        )
        if target:
            await self._transition(
                clinic_id=event.clinic_id,
                lead_id=lead.id,
                target_stage_id=target,
                reason="event_booking_no_show",
                event_type=LIFECYCLE_EVENT_NO_SHOW,
                ctx=self._ctx(event.clinic_id, event.trace_id, user_type="system"),
            )
            try:
                await self.leads.close_lead_as_lost(
                    clinic_id=event.clinic_id,
                    lead_id=lead.id,
                    lost_stage_id=target,
                    lost_reason="booking_no_show",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "crm_lead_close_lost_failed_after_no_show_transition",
                    extra={
                        "trace_id": event.trace_id,
                        "clinic_id": str(event.clinic_id),
                        "lead_id": str(lead.id),
                        "error": str(exc),
                        "chain": "crm_lifecycle",
                        "step": "close_lost",
                    },
                )

    async def handle_stale_lead(self, event: LeadEventStale) -> None:
        if not (event.clinic_id and event.lead_id):
            return
        lead = await self.leads.repository.get_lead_by_id(event.clinic_id, event.lead_id)
        if not lead or lead.status != "open":
            crm_lead_stale_handled_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="skipped_not_open",
            ).inc()
            return

        target = await self.semantics.get_stage_id_for_semantic(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            semantic=LeadStageSemanticsService.SEM_STALE,
        ) or await self._first_existing_stage_id(
            clinic_id=event.clinic_id,
            pipeline_id=lead.pipeline_id,
            candidate_codes=("stale", "follow_up", "need_follow_up"),
        )
        if target and target != lead.stage_id:
            ok = await self._transition(
                clinic_id=event.clinic_id,
                lead_id=lead.id,
                target_stage_id=target,
                reason="event_lead_stale",
                event_type=LIFECYCLE_EVENT_STALE,
                ctx=self._ctx(event.clinic_id, event.trace_id, user_type="system"),
            )
            crm_lead_stale_handled_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="stage_applied" if ok else "transition_failed",
            ).inc()
        else:
            crm_lead_stale_handled_total.labels(
                clinic_id=str(event.clinic_id),
                outcome="noop",
            ).inc()

    async def _transition(
        self,
        *,
        clinic_id: UUID,
        lead_id: UUID,
        target_stage_id: UUID,
        reason: str,
        event_type: str,
        ctx: RequestContext,
    ) -> bool:
        from_stage_id: str | None = None
        from_semantic: str | None = None
        to_semantic: str | None = None
        lead_row = None
        try:
            lead_row = await self.leads.repository.get_lead_by_id(clinic_id, lead_id)
            if lead_row:
                from_stage_id = str(lead_row.stage_id)
                from_st = await self.leads.repository.get_stage_by_id(clinic_id, lead_row.stage_id)
                if from_st:
                    from_semantic = await self.semantics.get_semantic_for_stage(
                        clinic_id=clinic_id,
                        pipeline_id=lead_row.pipeline_id,
                        stage=from_st,
                    )
            to_st = await self.leads.repository.get_stage_by_id(clinic_id, target_stage_id)
            if to_st and lead_row:
                to_semantic = await self.semantics.get_semantic_for_stage(
                    clinic_id=clinic_id,
                    pipeline_id=lead_row.pipeline_id,
                    stage=to_st,
                )
        except Exception:  # noqa: BLE001
            pass

        log_base = {
            "trace_id": ctx.trace_id,
            "clinic_id": str(clinic_id),
            "lead_id": str(lead_id),
            "event_type": event_type,
            "from_stage_id": from_stage_id,
            "from_semantic": from_semantic,
            "to_stage_id": str(target_stage_id),
            "to_semantic": to_semantic,
            "reason": reason,
            "initiator": ctx.user_type,
            "chain": "crm_lifecycle",
            "step": "crm_lifecycle_transition",
        }
        try:
            logger.info(
                "crm_lead_lifecycle_transition_attempt",
                extra=log_base,
            )
            await self.leads.update_stage_from_ai(
                clinic_id=clinic_id,
                lead_id=lead_id,
                target_stage_id=target_stage_id,
                reason=reason,
                initiated_by_ai=False,
                request_context=ctx,
            )
            logger.info(
                "crm_lead_lifecycle_transition_applied",
                extra=log_base,
            )
            crm_lead_lifecycle_transitions_total.labels(
                clinic_id=str(clinic_id),
                event_type=event_type,
                outcome="success",
            ).inc()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "lead_lifecycle_transition_failed",
                extra={**log_base, "error": str(exc)},
            )
            crm_lead_lifecycle_transitions_total.labels(
                clinic_id=str(clinic_id),
                event_type=event_type,
                outcome="failed",
            ).inc()
            return False

    async def _first_existing_stage_id(
        self,
        *,
        clinic_id: UUID,
        pipeline_id: UUID,
        candidate_codes: tuple[str, ...],
    ) -> UUID | None:
        for code in candidate_codes:
            stage = await self.leads.repository.get_stage_by_pipeline_and_code(
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                code=code,
            )
            if stage:
                return stage.id
        return None

    @staticmethod
    def _ctx(clinic_id: UUID, trace_id: str | None, *, user_type: str) -> RequestContext:
        return RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type=user_type,
            trace_id=trace_id,
            roles=set(),
            permissions=set(),
        )
