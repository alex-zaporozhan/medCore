"""AI tools for Tasks & Attention (TASKS_AI_021).

This module provides LLM-assisted analysis tool that proposes operational tasks
based on aggregated, non-PII signals. It is designed to be safe-by-default:
- it uses SafeAiClient (AiSanitizer) to avoid leaking personal data;
- it uses tokenization handles (PATIENT#uuid, BOOKING#uuid, LEAD#uuid) instead of raw PII.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.ai.tools_base import Tool, ToolContext, ToolError
from src.application.ai.tokenization import (
    make_booking_token,
    make_birthdate_token,
    make_lead_token,
    make_patient_token,
    parse_booking_token,
    parse_lead_token,
    parse_patient_token,
)
from src.application.dto.ai_task_manager_dto import ProposedTask
from src.application.services.ai_client_factory import build_safe_ai_client
from src.core.metrics import ai_tool_calls_total, ai_tool_call_duration_seconds
from src.infrastructure.external_apis.ai_client import AiClientError


logger = logging.getLogger(__name__)

BIRTHDATE_KEYS = {"birth_date", "birthdate", "dob", "date_of_birth"}


class AnalyzeAttentionForTasksArgs(BaseModel):
    clinic_id: UUID
    trace_id: str | None = None
    # Aggregated signals (no PII). IDs are allowed only as UUID strings.
    signals: dict[str, Any] = Field(default_factory=dict)
    allowed_task_classes: list[str] = Field(default_factory=list)
    creation_mode: str = Field(default="confirm", pattern="^(confirm|auto)$")
    existing_attention_task_keys: list[str] = Field(
        default_factory=list,
        description="Existing attention task keys as 'kind#uuid' strings for dedup hints.",
    )


class _LlmTaskItem(BaseModel):
    task_class: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    role_assignee: str | None = Field(default=None, max_length=64)
    # tokenized links (preferred) + optional raw UUIDs (fallback)
    patient_token: str | None = None
    booking_token: str | None = None
    lead_token: str | None = None
    attention_kind: str | None = Field(default=None, max_length=32)
    attention_ref_token: str | None = None
    requires_confirmation: bool = True


class _LlmResponse(BaseModel):
    tasks: list[_LlmTaskItem] = Field(default_factory=list)


class AnalyzeAttentionForTasksResult(BaseModel):
    success: bool
    proposed: list[ProposedTask] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str | None = None


def _tokenize_signals(signals: dict[str, Any]) -> dict[str, Any]:
    """Replace known UUID fields inside signals with stable token handles."""
    safe = json.loads(json.dumps(signals)) if signals else {}

    def _scrub_birthdates(obj: Any) -> Any:
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                key = str(k)
                if key.lower() in BIRTHDATE_KEYS and v is not None:
                    out[key] = make_birthdate_token(str(v))
                else:
                    out[key] = _scrub_birthdates(v)
            return out
        if isinstance(obj, list):
            return [_scrub_birthdates(x) for x in obj]
        return obj

    safe = _scrub_birthdates(safe)

    # booking_no_show_counts: { "<patient_uuid>": count }
    counts = safe.get("booking_no_show_counts")
    if isinstance(counts, dict):
        new_counts: dict[str, Any] = {}
        for raw_pid, cnt in counts.items():
            try:
                pid = UUID(str(raw_pid))
                new_counts[make_patient_token(pid)] = cnt
            except Exception:
                new_counts[str(raw_pid)] = cnt
        safe["booking_no_show_counts"] = new_counts

    # stale_lead_ids: ["<uuid>", ...]
    leads = safe.get("stale_lead_ids")
    if isinstance(leads, list):
        new_leads: list[str] = []
        for raw in leads:
            try:
                lid = UUID(str(raw))
                new_leads.append(make_lead_token(lid))
            except Exception:
                new_leads.append(str(raw))
        safe["stale_lead_ids"] = new_leads

    # attention.items[].ref_id -> token by kind when possible
    attention = safe.get("attention")
    if isinstance(attention, dict):
        items = attention.get("items")
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                kind = str(it.get("kind") or "")
                ref_id = it.get("ref_id")
                if not ref_id:
                    continue
                try:
                    uid = UUID(str(ref_id))
                except Exception:
                    continue
                if kind in {"follow_up", "conflict"}:
                    # no dedicated token type; keep UUID string
                    continue
                if kind == "retention_gap":
                    it["ref_id"] = make_patient_token(uid)
    return safe


def _extract_json_content(data: dict[str, Any]) -> str:
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


class AnalyzeAttentionForTasksTool(Tool):
    name = "analyze_attention_for_tasks"
    description = "Проанализировать сигналы attention/домена и предложить список ProposedTask (без ПД)."
    args_schema = AnalyzeAttentionForTasksArgs
    required_permissions = {"ai.tasks.run"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: AnalyzeAttentionForTasksArgs,
    ) -> AnalyzeAttentionForTasksResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Нельзя анализировать сигналы другой клиники.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        trace_id = args.trace_id or ctx.trace_id
        started = __import__("time").time()
        ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="attempt").inc()

        safe_client, meta = await build_safe_ai_client(clinic_id=clinic_id, session=ctx.db)
        if not safe_client.is_configured():
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="not_configured").inc()
            return AnalyzeAttentionForTasksResult(
                success=False,
                proposed=[],
                error_code="ai_not_configured",
                error_message="AI provider is not configured.",
                trace_id=trace_id,
            )

        tokenized = _tokenize_signals(args.signals)
        allowed = args.allowed_task_classes or []

        prompt = (
            "Ты ассистент операционного менеджера клиники. На основе агрегированных сигналов (без персональных данных) "
            "предложи список задач. Верни СТРОГО JSON без markdown с ключом 'tasks' (массив). "
            "Каждый элемент tasks: {task_class, title, description, priority, role_assignee, "
            "patient_token?, booking_token?, lead_token?, attention_kind?, attention_ref_token?, requires_confirmation}. "
            "Токены имеют вид PATIENT#<uuid>, BOOKING#<uuid>, LEAD#<uuid>. "
            "Не включай телефоны, имена, e-mail. "
            "Разрешённые task_class: "
            + (", ".join(allowed) if allowed else "любой из известных классов")
            + "."
        )

        payload: dict[str, Any] = {
            "model": (getattr(ctx, "ai_model", None) or ""),  # provider may ignore
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "signals": tokenized,
                            "existing_attention_task_keys": args.existing_attention_task_keys,
                            "creation_mode": args.creation_mode,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        try:
            data = await safe_client.complete(payload)
        except AiClientError as exc:
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="provider_error").inc()
            return AnalyzeAttentionForTasksResult(
                success=False,
                proposed=[],
                error_code="provider_error",
                error_message=str(exc),
                trace_id=trace_id,
            )
        except Exception as exc:  # noqa: BLE001
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="unexpected_error").inc()
            logger.exception("analyze_attention_for_tasks unexpected_error", extra={"clinic_id": str(clinic_id)})
            return AnalyzeAttentionForTasksResult(
                success=False,
                proposed=[],
                error_code="unexpected_error",
                error_message="AI analysis failed.",
                trace_id=trace_id,
            )
        finally:
            ai_tool_call_duration_seconds.labels(tool_id=self.name, source=ctx.source).observe(__import__("time").time() - started)

        content = _extract_json_content(data)
        if not content:
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="empty").inc()
            return AnalyzeAttentionForTasksResult(
                success=False,
                proposed=[],
                error_code="empty_response",
                error_message="AI returned empty response.",
                trace_id=trace_id,
            )

        try:
            parsed_json = json.loads(content)
            llm = _LlmResponse.model_validate(parsed_json)
        except Exception as exc:  # noqa: BLE001
            ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="invalid_json").inc()
            return AnalyzeAttentionForTasksResult(
                success=False,
                proposed=[],
                error_code="invalid_json",
                error_message="AI returned invalid JSON.",
                trace_id=trace_id,
            )

        proposed: list[ProposedTask] = []
        for t in llm.tasks:
            if allowed and t.task_class not in allowed:
                continue

            patient_id: UUID | None = None
            booking_id: UUID | None = None
            lead_id: UUID | None = None
            attention_ref_id: UUID | None = None

            try:
                if t.patient_token:
                    patient_id = parse_patient_token(t.patient_token)
            except Exception:
                patient_id = None
            try:
                if t.booking_token:
                    booking_id = parse_booking_token(t.booking_token)
            except Exception:
                booking_id = None
            try:
                if t.lead_token:
                    lead_id = parse_lead_token(t.lead_token)
            except Exception:
                lead_id = None
            try:
                if t.attention_ref_token:
                    # attention_ref_token can be patient token for retention_gap, otherwise ignore
                    if t.attention_ref_token.startswith("PATIENT#"):
                        attention_ref_id = parse_patient_token(t.attention_ref_token)
            except Exception:
                attention_ref_id = None

            proposed.append(
                ProposedTask(
                    clinic_id=clinic_id,
                    task_class=t.task_class,
                    title=t.title,
                    description=t.description,
                    priority=t.priority,
                    role_assignee=t.role_assignee,
                    booking_id=booking_id,
                    patient_id=patient_id,
                    lead_id=lead_id,
                    attention_kind=t.attention_kind,
                    attention_ref_id=attention_ref_id,
                    requires_confirmation=bool(t.requires_confirmation),
                    initiated_by_ai=True,
                )
            )

        ai_tool_calls_total.labels(tool_id=self.name, source=ctx.source, status="success").inc()
        return AnalyzeAttentionForTasksResult(success=True, proposed=proposed, trace_id=trace_id)

