from __future__ import annotations

import json
import logging
from uuid import UUID

from src.application.ai.tokenization import make_lead_token, parse_lead_token
from src.application.ai.tools_base import Tool, ToolContext, ToolError
from src.application.dto.crm_ai_dto import (
    CreateLeadTaskInput as CreateLeadTaskArgs,
    CreateLeadTaskOutput as CreateLeadTaskResult,
    LeadContextForAi,
    LeadSummary,
    SuggestNextStageInput as SuggestNextStageArgs,
    SuggestNextStageOutput as SuggestNextStageResult,
    SummarizeLeadContextInput as SummarizeLeadContextArgs,
    SummarizeLeadContextOutput as SummarizeLeadContextResult,
    UpdateLeadStageInput as UpdateLeadStageArgs,
    UpdateLeadStageOutput as UpdateLeadStageResult,
)
from src.application.services.ai_client_factory import build_safe_ai_client
from src.application.services.lead_service import LeadService
from src.application.services.task_service import TaskService
from src.core.config import settings
from src.core.metrics import ai_tool_calls_total, crm_ai_recommendations_total
from src.core.prometheus_labels import clinic_bucket_label
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.infrastructure.external_apis.ai_client import AiClientError

logger = logging.getLogger(__name__)

def _context_for_external_ai(context: LeadContextForAi) -> dict:
    """
    Reduce context before sending to external AI.

    Important: do NOT include free-text fields that may contain personal data
    (e.g. notes). We only send structured lead summary + task counters.
    """
    data = context.model_dump(mode="json")
    data.pop("notes_preview", None)
    return data


def _resolve_lead_id(*, lead_token: str | None, lead_id: UUID | None) -> UUID:
    if lead_token:
        return parse_lead_token(lead_token)
    if lead_id is not None:
        return lead_id
    raise ValueError("lead_token (preferred) or lead_id is required")


def _lead_to_summary(lead) -> LeadSummary:
    return LeadSummary(
        lead_token=make_lead_token(lead.id),
        clinic_id=lead.clinic_id,
        pipeline_id=lead.pipeline_id,
        stage_id=lead.stage_id,
        status=lead.status,
        title=lead.title,
        source=lead.source,
        estimated_value=lead.estimated_value,
        actual_value=lead.actual_value,
        created_at=getattr(lead, "created_at", None),
        closed_at=getattr(lead, "closed_at", None),
    )


async def _build_lead_context(ctx: ToolContext, lead_id: UUID) -> LeadContextForAi:
    service = LeadService(ctx.db)
    return await service.get_lead_context_for_ai(
        clinic_id=ctx.clinic_id,
        lead_id=lead_id,
        allow_personal_data=False,
    )


class SummarizeLeadContextTool(Tool):
    name = "summarize_lead_context"
    description = "Сформировать краткое резюме по лиду (без персональных данных)."
    args_schema = SummarizeLeadContextArgs
    required_permissions = {"view_crm"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: SummarizeLeadContextArgs,
    ) -> SummarizeLeadContextResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Инструмент может работать только в пределах одной клиники.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        try:
            lead_id = _resolve_lead_id(lead_token=args.lead_token, lead_id=args.lead_id)
        except ValueError as exc:
            return ToolError(code="lead_required", message=str(exc))

        try:
            await ctx.db.flush()
            context = await _build_lead_context(ctx, lead_id)
        except LookupError as exc:
            return ToolError(code="lead_not_found", message=str(exc))
        except Exception as exc:  # noqa: BLE001
            return ToolError(code="unexpected_error", message="Не удалось собрать контекст лида.", details={"error": str(exc)})

        # Build provider client via centralized factory (policy-aware).
        safe_client, _client_ctx = await build_safe_ai_client(clinic_id=clinic_id, session=ctx.db)
        base_mode = "external_active" if safe_client.is_configured() else "fallback_local"
        if not safe_client.is_configured():
            # Local heuristic summary (no external calls).
            lead = context.lead
            parts = [
                f"Лид «{lead.title}» в статусе {lead.status}.",
                f"Стадия: {lead.stage_id}.",
                f"Оценка (прогноз CRM) / факт (ERP): {lead.estimated_value} / {lead.actual_value}.",
                f"Задачи: open={context.open_tasks_count}, in_progress={context.in_progress_tasks_count}, done={context.done_tasks_count}.",
            ]
            if context.notes_preview:
                parts.append("Последние заметки: " + " | ".join(context.notes_preview[:3]))
            return SummarizeLeadContextResult(
                summary=" ".join(parts),
                highlights=[],
                risks=[],
                suggested_actions=[],
                ai_status=base_mode,
                trace_id=args.trace_id or ctx.trace_id,
            )

        system_prompt = (
            "Ты помогаешь менеджеру клиники вести CRM. "
            "Используй только агрегированные данные (персональные данные скрыты). "
            "Верни строго JSON вида {"
            "\"summary\":\"...\","
            "\"highlights\":[\"...\"],"
            "\"risks\":[\"...\"],"
            "\"suggested_actions\":[\"...\"]"
            "} без пояснений вне JSON."
        )
        user_content = "Контекст лида:\n" + json.dumps(
            _context_for_external_ai(context),
            ensure_ascii=False,
        )

        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 300,
        }

        try:
            data = await safe_client.complete(payload)
            content = _extract_message_content(data)
            parsed = json.loads(content) if content else {}
            dto = SummarizeLeadContextResult.model_validate(parsed)
            crm_ai_recommendations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                kind="summary",
                outcome="generated",
            ).inc()
            logger.info(
                "crm_ai_tool_call",
                extra={
                    "trace_id": args.trace_id or ctx.trace_id,
                    "clinic_id": str(clinic_id),
                    "tool_id": self.name,
                    "action": "summarize_lead_context",
                    "status": "success",
                },
            )
        except AiClientError as exc:
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="ai_client_error").inc()
            crm_ai_recommendations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                kind="summary",
                outcome="error",
            ).inc()
            logger.warning("summarize_lead_context: ai_client_error", extra={"clinic_id": str(clinic_id), "error": str(exc)})
            return SummarizeLeadContextResult(
                summary="Не удалось получить резюме от AI-провайдера. Проверьте конфигурацию.",
                highlights=[],
                risks=[],
                suggested_actions=[],
                ai_status="fallback_local",
                trace_id=args.trace_id or ctx.trace_id,
            )
        except Exception as exc:  # noqa: BLE001
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="unexpected_error").inc()
            logger.exception("summarize_lead_context: unexpected_error", extra={"clinic_id": str(clinic_id)})
            return ToolError(code="unexpected_error", message="Не удалось сформировать резюме лида.", details={"error": str(exc)})

        dto.ai_status = base_mode
        dto.trace_id = args.trace_id or ctx.trace_id
        return dto


class SuggestNextStageForLeadTool(Tool):
    name = "suggest_next_stage_for_lead"
    description = "Предложить следующую стадию для лида (рекомендация; не изменяет данные)."
    args_schema = SuggestNextStageArgs
    required_permissions = {"view_crm"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: SuggestNextStageArgs,
    ) -> SuggestNextStageResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Инструмент может работать только в пределах одной клиники.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        try:
            lead_id = _resolve_lead_id(lead_token=args.lead_token, lead_id=args.lead_id)
        except ValueError as exc:
            return ToolError(code="lead_required", message=str(exc))

        try:
            context = await _build_lead_context(ctx, lead_id)
        except LookupError as exc:
            return ToolError(code="lead_not_found", message=str(exc))
        except Exception as exc:  # noqa: BLE001
            return ToolError(code="unexpected_error", message="Не удалось собрать контекст лида.", details={"error": str(exc)})

        safe_client, _client_ctx = await build_safe_ai_client(clinic_id=clinic_id, session=ctx.db)
        base_mode = "external_active" if safe_client.is_configured() else "fallback_local"
        if not safe_client.is_configured():
            # Heuristic suggestion: keep current stage (no safe decision).
            return SuggestNextStageResult(
                suggested_stage_id=context.lead.stage_id,
                confidence=0.0,
                rationale="AI-провайдер не настроен; рекомендация недоступна.",
                ai_status=base_mode,
                trace_id=args.trace_id or ctx.trace_id,
            )

        # Ask model to suggest next stage by name/code is not available here; we return stage_id only.
        # We provide list of stages in current pipeline to let the model choose the id.
        service = LeadService(ctx.db)
        stages = await service.list_stages_for_pipeline(
            clinic_id=clinic_id,
            pipeline_id=context.lead.pipeline_id,
        )
        stages_payload = [
            {"id": str(s.id), "code": s.code, "name": s.name, "order": s.order, "probability": s.probability}
            for s in stages
        ]

        system_prompt = (
            "Ты помогаешь менеджеру клиники вести CRM. "
            "На основе контекста лида и списка стадий предложи наиболее подходящую следующую стадию. "
            "Верни строго JSON вида {\"suggested_stage_id\": \"<uuid>\" или null, \"confidence\": 0.0-1.0, \"rationale\": \"...\"}."
        )
        user_content = (
            "Контекст лида (без ПД):\n"
            + json.dumps(_context_for_external_ai(context), ensure_ascii=False)
            + "\n\nСтадии пайплайна:\n"
            + json.dumps(stages_payload, ensure_ascii=False)
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
            data = await safe_client.complete(payload)
            content = _extract_message_content(data)
            parsed = json.loads(content) if content else {}
            # Accept string uuid in payload.
            suggested_raw = parsed.get("suggested_stage_id")
            suggested_uuid: UUID | None = None
            if suggested_raw:
                try:
                    suggested_uuid = UUID(str(suggested_raw))
                except Exception:
                    suggested_uuid = None
            confidence = float(parsed.get("confidence") or 0.0)
            rationale = parsed.get("rationale")
            dto = SuggestNextStageResult(
                suggested_stage_id=suggested_uuid,
                confidence=max(0.0, min(1.0, confidence)),
                rationale=str(rationale)[:2000] if rationale else None,
                ai_status=base_mode,
                trace_id=args.trace_id or ctx.trace_id,
            )
            crm_ai_recommendations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                kind="stage",
                outcome="generated",
            ).inc()
            logger.info(
                "crm_ai_tool_call",
                extra={
                    "trace_id": args.trace_id or ctx.trace_id,
                    "clinic_id": str(clinic_id),
                    "tool_id": self.name,
                    "action": "suggest_stage",
                    "status": "success",
                    "suggested_stage_id": str(suggested_uuid) if suggested_uuid else None,
                },
            )
            return dto
        except AiClientError as exc:
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="ai_client_error").inc()
            crm_ai_recommendations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                kind="stage",
                outcome="error",
            ).inc()
            logger.warning("suggest_next_stage_for_lead: ai_client_error", extra={"clinic_id": str(clinic_id), "error": str(exc)})
            return SuggestNextStageResult(
                suggested_stage_id=None,
                confidence=0.0,
                rationale="Ошибка AI-провайдера; рекомендация недоступна.",
                ai_status="fallback_local",
                trace_id=args.trace_id or ctx.trace_id,
            )
        except Exception as exc:  # noqa: BLE001
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="unexpected_error").inc()
            logger.exception("suggest_next_stage_for_lead: unexpected_error", extra={"clinic_id": str(clinic_id)})
            return ToolError(code="unexpected_error", message="Не удалось получить рекомендацию стадии.", details={"error": str(exc)})


class UpdateLeadStageTool(Tool):
    name = "update_lead_stage"
    description = "Изменить стадию лида (требует прав manage_crm)."
    args_schema = UpdateLeadStageArgs
    required_permissions = {"manage_crm"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: UpdateLeadStageArgs,
    ) -> UpdateLeadStageResult | ToolError:
        # Clinic boundary
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Нельзя изменять лид в другой клинике.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        try:
            lead_id = _resolve_lead_id(lead_token=args.lead_token, lead_id=args.lead_id)
        except ValueError as exc:
            return ToolError(code="lead_required", message=str(exc))

        service = LeadService(ctx.db)
        try:
            updated = await service.update_stage_from_ai(
                clinic_id=clinic_id,
                lead_id=lead_id,
                target_stage_id=args.target_stage_id,
                reason=args.reason,
                initiated_by_ai=bool(args.initiated_by_ai),
                request_context=ctx.request_context,
            )
            return UpdateLeadStageResult(
                success=True,
                lead=_lead_to_summary(updated),
                trace_id=args.trace_id or ctx.trace_id,
            )
        except LookupError as exc:
            return UpdateLeadStageResult(
                success=False,
                lead=None,
                error_code="not_found",
                error_message=str(exc),
                trace_id=args.trace_id or ctx.trace_id,
            )
        except ValueError as exc:
            return UpdateLeadStageResult(
                success=False,
                lead=None,
                error_code="validation_error",
                error_message=str(exc),
                trace_id=args.trace_id or ctx.trace_id,
            )
        except Exception:  # noqa: BLE001
            return UpdateLeadStageResult(
                success=False,
                lead=None,
                error_code="unexpected_error",
                error_message="Не удалось изменить стадию лида из-за внутренней ошибки.",
                trace_id=args.trace_id or ctx.trace_id,
            )


class CreateTaskForLeadTool(Tool):
    name = "create_task_for_lead"
    description = "Создать задачу для лида (created_by='ai', требует manage_tasks)."
    args_schema = CreateLeadTaskArgs
    required_permissions = {"manage_tasks"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: CreateLeadTaskArgs,
    ) -> CreateLeadTaskResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Нельзя создавать задачу в другой клинике.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        try:
            lead_id = _resolve_lead_id(lead_token=args.lead_token, lead_id=args.lead_id)
        except ValueError as exc:
            return ToolError(code="lead_required", message=str(exc))

        # Ensure lead exists within clinic boundary.
        lead_service = LeadService(ctx.db)
        try:
            lead = await lead_service.repository.get_lead_by_id(clinic_id, lead_id)
            if not lead:
                raise LookupError("Lead not found")
        except LookupError as exc:
            return CreateLeadTaskResult(
                success=False,
                task_id=None,
                error_code="lead_not_found",
                error_message=str(exc),
                trace_id=args.trace_id or ctx.trace_id,
            )

        repo = TaskRepositoryImpl(ctx.db)
        service = TaskService(repo)
        try:
            task = await service.create_task(
                clinic_id=clinic_id,
                title=args.title,
                description=args.description,
                priority=args.priority,
                creator_id=ctx.user_id,
                assignee_id=None,
                role_assignee=None,
                due_at=args.due_at,
                lead_id=lead_id,
                source="ai_suggested" if args.initiated_by_ai else "manual",
                attention_kind=args.attention_kind,
                attention_ref_id=args.attention_ref_id,
            )
            logger.info(
                "crm_ai_tool_call",
                extra={
                    "trace_id": args.trace_id or ctx.trace_id,
                    "clinic_id": str(clinic_id),
                    "tool_id": self.name,
                    "action": "create_task",
                    "status": "success",
                    "lead_id": str(lead_id),
                    "task_id": str(task.id),
                },
            )
            return CreateLeadTaskResult(
                success=True,
                task_id=task.id,
                trace_id=args.trace_id or ctx.trace_id,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "crm_ai_tool_call_failed",
                extra={
                    "trace_id": args.trace_id or ctx.trace_id,
                    "clinic_id": str(clinic_id),
                    "tool_id": self.name,
                    "action": "create_task",
                    "status": "error",
                    "lead_id": str(lead_id),
                },
            )
            return CreateLeadTaskResult(
                success=False,
                task_id=None,
                error_code="unexpected_error",
                error_message="Не удалось создать задачу для лида.",
                trace_id=args.trace_id or ctx.trace_id,
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

