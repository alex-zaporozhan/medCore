"""AI Orchestrator for omnichannel assistant (Phase 4).

MVP behaviour:
- reads effective settings (BUSINESS → CHANNEL → CHAT);
- for DISABLED: no-op;
- for AUTO_REPLY: tries to generate reply and send as outbound AI message;
- for SUGGEST_ONLY: generates draft reply as TEMPLATE message visible только админам.

All external AI calls go through SafeAiClient; on any error we fall back to no-op.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai.tools_base import ToolContext, ToolError
from src.application.ai.tools_registry import list_tools_for_context
from src.application.dto.chat_ai_agent_dto import (
    AgentResult,
    ChatMessage as AgentChatMessage,
    ToolCall,
)
from src.application.services.ai_config_service import AiConfigService
from src.application.services.booking_service import BookingService
from src.application.services.omnichannel_ai_settings_service import (
    EffectiveOmniAISettings,
    OmnichannelAISettingsService,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.application.services.omnichannel_outbound_dispatcher import (
    OmnichannelOutboundDispatcher,
)
from src.application.services.patient_service import PatientService
from src.application.services.schedule_service import ScheduleService
from src.application.booking_error_codes import normalize_booking_error_code
from src.application.booking_error_observability import record_booking_error_event
from src.application.services.task_service import TaskService
from src.core.config import settings
from src.core.context import RequestContext
from src.core.datetime_utils import utc_now
from src.core.prometheus_labels import account_bucket_label
from src.core.metrics import (
    omni_ai_auto_replies_total,
    omni_ai_escalations_total,
    omni_ai_provider_errors_total,
    omni_ai_suggestions_total,
    business_chain_omni_ai_duration_seconds,
    business_chain_omni_ai_errors_total,
    business_chain_omni_ai_step_duration_seconds,
    business_chain_omni_ai_total,
    ai_tool_calls_total,
    ai_tool_call_duration_seconds,
)
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_contact import Contact as OmniContact
from src.domain.entities.omnichannel_message import Message as OmniMessage
from src.domain.entities.ai_tool_event import AiToolEvent
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.infrastructure.external_apis.ai_client import AiClientError
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient
from src.application.services.ai_client_factory import build_safe_ai_client
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)


def _json_safe_tool_payload(obj: Any) -> Any:
    """Recursively convert Pydantic models / UUIDs to JSON-serializable structures (AiToolEvent JSONB)."""
    if isinstance(obj, BaseModel):
        return json.loads(obj.model_dump_json())
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, list):
        return [_json_safe_tool_payload(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe_tool_payload(v) for k, v in obj.items()}
    return obj


@dataclass
class AIContext:
    business_account_id: UUID
    chat: OmniChat
    contact: OmniContact | None
    last_messages: list[OmniMessage]
    effective_settings: EffectiveOmniAISettings
    clinic_name: str | None = None  # Domain context for prompt (Phase 4)


@dataclass
class LLMReply:
    text: str
    confidence: float
    meta: dict[str, Any]


class LLMClient:
    """
    Thin wrapper around SafeAiClient for omnichannel orchestrator.

    When constructed without an explicit SafeAiClient, it uses the defaults from
    SafeAiClient(), which in turn creates AiSanitizer(allow_personal_data=False).
    This means that in legacy mode all outbound text is sanitized and personal
    data is masked before calling external AI, even if provider configuration
    is misconfigured or missing.
    """

    def __init__(self, safe_client: SafeAiClient | None = None) -> None:
        # In legacy mode we still allow constructing without explicit config;
        # for orchestrator we always inject a SafeAiClient built via factory.
        self._client = safe_client or SafeAiClient()

    def is_configured(self) -> bool:
        return self._client.is_configured()

    async def generate_reply(self, context: AIContext) -> LLMReply | None:
        """Call LLM provider and return structured reply; on failure returns None."""
        # Build simple prompt using last messages only; domain data can be added later.
        lines: list[str] = []
        for m in context.last_messages[-10:]:
            role = "КЛИЕНТ" if m.direction == "INBOUND" and m.actor_type == "CLIENT" else "ОПЕРАТОР"
            body = (m.content or "").strip()
            if not body:
                continue
            lines.append(f"{role}: {body}")
        transcript = "\n".join(lines)

        system_prompt = (
            "Ты помощник контакт-центра клиники. "
            "Отвечай вежливо, кратко, без медицинских рекомендаций и без обещаний скидок. "
            "Верни строго JSON вида {\"text\": \"...\", \"confidence\": 0.0}."
        )
        if context.clinic_name:
            system_prompt = f"Клиника: {context.clinic_name}.\n{system_prompt}"
        user_content = f"История диалога:\n{transcript}\n\nСформулируй ответ клиенту на последнюю реплику."

        payload = {
            "model": settings.ai_provider_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 256,
        }

        try:
            data = await self._client.complete(payload)
        except AiClientError as exc:
            omni_ai_provider_errors_total.labels(
                source="omni_orchestrator",
                error_type="ai_client_error",
            ).inc()
            logger.warning("LLMClient.generate_reply AiClientError", extra={"error": str(exc)})
            return None
        except Exception:  # noqa: BLE001
            omni_ai_provider_errors_total.labels(
                source="omni_orchestrator",
                error_type="unexpected_error",
            ).inc()
            logger.exception("LLMClient.generate_reply unexpected error")
            return None

        content = _extract_message_content(data) or ""
        try:
            import json

            parsed = json.loads(content)
            text = str(parsed.get("text") or "").strip()
            if not text:
                return None
            confidence = float(parsed.get("confidence") or 0.5)
            return LLMReply(text=text, confidence=confidence, meta=parsed)
        except Exception:
            # If provider did not return structured JSON, treat content as plain text.
            text = content.strip()
            if not text:
                return None
            return LLMReply(text=text, confidence=0.5, meta={})


OPERATOR_REQUEST_PHRASES = [
    "оператор",
    "живой человек",
    "менеджер",
    "позовите",
    "хочу поговорить с человеком",
    "соедините с оператором",
]


def _client_asks_for_operator(text: str) -> bool:
    """Return True if client text indicates request for a live operator."""
    if not (text and isinstance(text, str)):
        return False
    normalized = " ".join((text or "").lower().split())
    return any(phrase in normalized for phrase in OPERATOR_REQUEST_PHRASES)


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


class OmnichannelAIOrchestrator:
    """Core AI orchestrator for omnichannel inbound messages."""

    def __init__(
        self,
        session: AsyncSession,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.session = session
        self.chat_service = OmnichannelChatService(session)
        self.settings_service = OmnichannelAISettingsService(session)
        # LLM client for legacy AUTO_REPLY / SUGGEST_ONLY path.
        # It is populated lazily via build_safe_ai_client(...) in handle_incoming_for_ai
        # to ensure all legacy calls also respect centralized AI policy.
        self.llm_client = llm_client
        self.dispatcher = OmnichannelOutboundDispatcher(session)

    # ------------------------------------------------------------------
    # New function-calling agent entrypoint (Phase: AI agent)
    # ------------------------------------------------------------------

    async def run_ai_agent(
        self,
        chat: OmniChat,
        incoming_message: OmniMessage,
        request_context: RequestContext,
        max_tool_iterations: int = 3,
        max_total_duration_seconds: int = 20,
    ) -> AgentResult | None:
        """
        Run function-calling AI agent for given omnichannel chat.

        - builds chat history;
        - resolves clinic AI config;
        - prepares tools and executes tool_calls loop;
        - writes final AI message into omnichannel chat.
        """
        clinic_id: UUID = chat.business_account_id

        started_at = utc_now()

        # Resolve AI provider configuration for clinic and build SafeAiClient
        safe_client, client_ctx = await build_safe_ai_client(clinic_id=clinic_id, session=self.session)
        if not safe_client.is_configured():
            logger.info(
                "OmnichannelAIOrchestrator.run_ai_agent: provider not configured",
                extra={
                    "chat_id": str(chat.id),
                    "clinic_id": str(clinic_id),
                    "provider_type": client_ctx.provider_type,
                    "allow_personal_data": client_ctx.allow_personal_data,
                },
            )
            return None

        business_chain_omni_ai_total.labels(
            account_bucket=account_bucket_label(clinic_id),
            status="attempt",
        ).inc()

        # Tool context + filtered registry (RBAC: booking.ai_tools.use for Omni system actor)
        tool_ctx = ToolContext(
            db=self.session,
            clinic_id=clinic_id,
            request_context=request_context,
            source="omni_chat",
            booking_service=BookingService(self.session),
            schedule_service=ScheduleService(self.session),
            patient_service=PatientService(self.session),
        )
        tools = list_tools_for_context(tool_ctx, source="omni_chat")

        def _build_tools_schema() -> list[dict[str, Any]]:
            schema: list[dict[str, Any]] = []
            for tool in tools.values():
                params_schema = tool.args_schema.model_json_schema()
                schema.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": params_schema,
                        },
                    }
                )
            return schema

        tools_schema = _build_tools_schema()

        # Build chat history for LLM
        history: list[AgentChatMessage] = []
        last_messages = await self.chat_service.list_messages(chat_id=chat.id, limit=20)
        for m in last_messages:
            body = (m.content or "").strip()
            if not body:
                continue
            if m.direction == "INBOUND" and m.actor_type == "CLIENT":
                role: str = "user"
            elif m.actor_type in ("AI",):
                role = "assistant"
            else:
                # other internal/system/admin messages are treated as assistant context
                role = "assistant"
            history.append(AgentChatMessage(role=role, content=body))

        # Append current inbound message as latest user message
        incoming_text = (incoming_message.content or "").strip()
        if incoming_text:
            history.append(AgentChatMessage(role="user", content=incoming_text))

        if not history:
            return None

        # System prompt can be extended with business-specific instructions later
        system_prompt = (
            "Ты AI‑агент клиники, помогающий записывать клиентов на приём. "
            "Отвечай вежливо и кратко. Для действий с расписанием и записями "
            "всегда используй доступные функции инструментов."
        )
        messages: list[AgentChatMessage] = [AgentChatMessage(role="system", content=system_prompt)] + history

        tool_events: list[dict[str, Any]] = []

        async def _call_llm(
            msgs: Iterable[AgentChatMessage],
            with_tools: bool,
            *,
            metrics_step: str,
        ) -> tuple[dict[str, Any], list[ToolCall]]:
            tool_choice: str | dict[str, Any] | None
            if with_tools:
                tool_choice = "auto"
            else:
                tool_choice = "none"
            llm_started = utc_now()
            data, tool_calls = await safe_client.chat_with_tools(
                messages=msgs,
                tools_schema=tools_schema if with_tools else None,
                tool_choice=tool_choice,
            )
            llm_elapsed = (utc_now() - llm_started).total_seconds()
            business_chain_omni_ai_step_duration_seconds.labels(
                account_bucket=account_bucket_label(clinic_id),
                step=metrics_step,
            ).observe(llm_elapsed)
            return data, tool_calls

        try:
            # First LLM call with tools enabled
            data, tool_calls = await _call_llm(messages, with_tools=True, metrics_step="llm_first")
        except AiClientError as exc:
            logger.warning(
                "run_ai_agent: AiClientError on first call",
                extra={"chat_id": str(chat.id), "error": str(exc)},
            )
            business_chain_omni_ai_errors_total.labels(
                account_bucket=account_bucket_label(clinic_id),
                error_type="ai_client_error",
            ).inc()
            return AgentResult(
                reply_message=AgentChatMessage(role="assistant", content=""),
                tool_events=tool_events,
                error="ai_client_error",
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "run_ai_agent: unexpected error on first call",
                extra={"chat_id": str(chat.id)},
            )
            business_chain_omni_ai_errors_total.labels(
                account_bucket=account_bucket_label(clinic_id),
                error_type="unexpected_error",
            ).inc()
            return AgentResult(
                reply_message=AgentChatMessage(role="assistant", content=""),
                tool_events=tool_events,
                error="unexpected_error",
            )

        iterations = 0
        while tool_calls and iterations < max_tool_iterations:
            # Global timeout for the whole agent run
            if (utc_now() - started_at) > timedelta(seconds=max_total_duration_seconds):
                logger.info(
                    "run_ai_agent: reached max_total_duration_seconds, stopping tool loop",
                    extra={
                        "chat_id": str(chat.id),
                        "clinic_id": str(clinic_id),
                        "iterations": iterations,
                    },
                )
                break
            iterations += 1
            for call in tool_calls:
                tool = tools.get(call.name)
                if tool is None:
                    logger.info(
                        "ai_tool_call_unknown_tool",
                        extra={
                            "trace_id": request_context.trace_id,
                            "tool_id": call.name,
                            "source": "omni_chat",
                            "clinic_id": str(clinic_id),
                            "actor_type": request_context.user_type,
                            "actor_id": str(request_context.user_id) if request_context.user_id else None,
                            "status": "error",
                            "error_code": "unknown_tool",
                        },
                    )
                    tool_events.append(
                        {
                            "tool": call.name,
                            "status": "error",
                            "code": "unknown_tool",
                        }
                    )
                    continue

                try:
                    args = tool.args_schema.model_validate_json(call.arguments_json)
                except Exception as exc:
                    ai_tool_calls_total.labels(
                        tool_id=call.name,
                        source="omni_chat",
                        status="invalid_arguments",
                    ).inc()
                    logger.info(
                        "ai_tool_call_invalid_arguments",
                        extra={
                            "trace_id": request_context.trace_id,
                            "tool_id": tool.name,
                            "source": "omni_chat",
                            "clinic_id": str(clinic_id),
                            "actor_type": request_context.user_type,
                            "actor_id": str(request_context.user_id) if request_context.user_id else None,
                            "status": "error",
                            "error_code": "invalid_arguments",
                        },
                    )
                    tool_events.append(
                        {
                            "tool": tool.name,
                            "status": "error",
                            "code": "invalid_arguments",
                            "error": str(exc),
                        }
                    )
                    messages.append(
                        AgentChatMessage(
                            role="tool",
                            content=f"Ошибка разбора аргументов для инструмента {tool.name}.",
                            name=tool.name,
                        )
                    )
                    continue

                tool_started = utc_now()
                result = await tool(tool_ctx, args)
                elapsed = (utc_now() - tool_started).total_seconds()
                ai_tool_call_duration_seconds.labels(
                    tool_id=tool.name,
                    source="omni_chat",
                ).observe(elapsed)
                business_chain_omni_ai_step_duration_seconds.labels(
                    account_bucket=account_bucket_label(clinic_id),
                    step="tool_execute",
                ).observe(elapsed)

                if isinstance(result, ToolError):
                    ai_tool_calls_total.labels(
                        tool_id=tool.name,
                        source="omni_chat",
                        status="error",
                    ).inc()
                    logger.info(
                        "ai_tool_call",
                        extra={
                            "trace_id": request_context.trace_id,
                            "tool_id": tool.name,
                            "source": "omni_chat",
                            "clinic_id": str(clinic_id),
                            "actor_type": request_context.user_type,
                            "actor_id": str(request_context.user_id) if request_context.user_id else None,
                            "status": "error",
                            "error_code": result.code,
                        },
                    )
                    if tool.name in {
                        "get_available_slots",
                        "create_booking",
                        "cancel_booking",
                        "reschedule_booking",
                    }:
                        await record_booking_error_event(
                            clinic_id=clinic_id,
                            code=normalize_booking_error_code(result.code),
                            source="ai_tool",
                            trace_id=request_context.trace_id,
                            tool_name=tool.name,
                        )
                    event = AiToolEvent(
                        clinic_id=clinic_id,
                        chat_id=chat.id,
                        message_id=incoming_message.id,
                        tool_name=tool.name,
                        status="error",
                        error_code=result.code,
                        args={"raw": _json_safe_tool_payload(args)},
                        result=None,
                    )
                    self.session.add(event)

                    # Tasks/Attention сигнал для повторяющихся/критичных ошибок tools.
                    # V1: создаём Task при ошибке выполнения tool,
                    # чтобы владелец/админ увидел это в Tasks/Attention.
                    try:
                        # Throttle: do not create Tasks for simple validation mistakes
                        # to avoid spamming Tasks on benign parameter issues.
                        non_actionable_codes = {
                            "validation_error",
                            "invalid_arguments",
                            "invalid_args",
                            "invalid_patient_token",
                            "invalid_booking_token",
                            "doctor_required",
                            "invalid_date_range",
                            "date_range_too_large",
                            "clinic_mismatch",
                            "patient_required",
                            "slot_unavailable",
                            "slot_conflict",
                        }
                        if result.code in non_actionable_codes:
                            raise RuntimeError("skip_task_for_non_actionable_error")

                        task_svc = TaskService(TaskRepositoryImpl(self.session))
                        raw_args = _json_safe_tool_payload(args)
                        if not isinstance(raw_args, dict):
                            raw_args = {}
                        # Heuristic extraction: if token is present, keep it in description (no PD).
                        booking_token = raw_args.get("booking_token")
                        patient_token = raw_args.get("patient_token")
                        title = f"BOOKING_AI_TOOL_FAILURE: {tool.name}"
                        desc = json.dumps(
                            {
                                "tool_id": tool.name,
                                "error_code": result.code,
                                "trace_id": request_context.trace_id,
                                "booking_token": booking_token,
                                "patient_token": patient_token,
                                "source": "omni_chat",
                            },
                            ensure_ascii=False,
                        )
                        await task_svc.create_task(
                            clinic_id=clinic_id,
                            title=title,
                            description=desc,
                            priority="high",
                            creator_id=None,
                            assignee_id=None,
                            role_assignee=None,
                            due_at=None,
                            booking_id=None,
                            patient_id=None,
                            source="system",
                            attention_kind="follow_up",
                            attention_ref_id=incoming_message.id,
                            trace_id=request_context.trace_id,
                        )
                    except Exception:  # noqa: BLE001
                        logger.warning(
                            "Failed to create Task for tool error",
                            extra={
                                "trace_id": request_context.trace_id,
                                "tool_id": tool.name,
                                "clinic_id": str(clinic_id),
                                "error_code": result.code,
                            },
                        )
                    tool_events.append(
                        {
                            "tool": tool.name,
                            "status": "error",
                            "code": result.code,
                            "details": result.details,
                        }
                    )
                    content = json.dumps({"error": _json_safe_tool_payload(result)}, ensure_ascii=False)
                else:
                    ai_tool_calls_total.labels(
                        tool_id=tool.name,
                        source="omni_chat",
                        status="success",
                    ).inc()
                    logger.info(
                        "ai_tool_call",
                        extra={
                            "trace_id": request_context.trace_id,
                            "tool_id": tool.name,
                            "source": "omni_chat",
                            "clinic_id": str(clinic_id),
                            "actor_type": request_context.user_type,
                            "actor_id": str(request_context.user_id) if request_context.user_id else None,
                            "status": "success",
                            "error_code": None,
                        },
                    )
                    event = AiToolEvent(
                        clinic_id=clinic_id,
                        chat_id=chat.id,
                        message_id=incoming_message.id,
                        tool_name=tool.name,
                        status="success",
                        error_code=None,
                        args={"raw": _json_safe_tool_payload(args)},
                        result=_json_safe_tool_payload(result),
                    )
                    self.session.add(event)
                    tool_events.append(
                        {
                            "tool": tool.name,
                            "status": "success",
                        }
                    )
                    content = json.dumps(_json_safe_tool_payload(result), ensure_ascii=False)

                messages.append(
                    AgentChatMessage(
                        role="tool",
                        content=content,
                        name=tool.name,
                    )
                )

            # After executing tools, ask LLM again without new tool calls (tool_choice="none")
            try:
                _, tool_calls = await _call_llm(messages, with_tools=False, metrics_step="llm_followup")
            except Exception:  # noqa: BLE001
                logger.exception(
                    "run_ai_agent: error during follow-up LLM call",
                    extra={"chat_id": str(chat.id)},
                )
                return AgentResult(
                    reply_message=AgentChatMessage(
                        role="assistant",
                        content="Произошла техническая ошибка при обработке запроса. Администратор подключится лично.",
                    ),
                    tool_events=tool_events,
                    error="llm_followup_error",
                )

        # Final response: extract last assistant message text
        try:
            final_data, _ = await _call_llm(messages, with_tools=False, metrics_step="llm_final")
            choices = final_data.get("choices") or []
            content = ""
            if choices:
                msg_obj = choices[0].get("message") or {}
                content = str(msg_obj.get("content") or "")
        except Exception:  # noqa: BLE001
            content = ""
            business_chain_omni_ai_errors_total.labels(
                account_bucket=account_bucket_label(clinic_id),
                error_type="llm_final_error",
            ).inc()

        reply_text = content.strip()
        if not reply_text:
            reply_text = "Сейчас техническая пауза, администратор подключится лично."

        # Persist outbound AI message in omnichannel chat
        msg = await self.chat_service.append_outbound_message(
            chat=chat,
            actor_type="AI",
            content=reply_text,
            channel_id=incoming_message.channel_id,
        )
        await self.dispatcher.dispatch_to_channel(msg)

        # Service message for admins about AI action
        try:
            summary = f"AI_ACTION_SUCCESS: tools={','.join({e['tool'] for e in tool_events if e.get('status') == 'success'})}"
            if not any(e.get("status") == "success" for e in tool_events):
                summary = "AI_ACTION_ERROR: no successful tool actions"
            await self.chat_service.append_outbound_message(
                chat=chat,
                actor_type="SYSTEM",
                content=summary,
                channel_id=None,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "run_ai_agent: failed to write AI_ACTION_* service message",
                extra={"chat_id": str(chat.id)},
            )

        total_elapsed = (utc_now() - started_at).total_seconds()
        business_chain_omni_ai_duration_seconds.labels(
            account_bucket=account_bucket_label(clinic_id),
        ).observe(total_elapsed)
        business_chain_omni_ai_total.labels(
            account_bucket=account_bucket_label(clinic_id),
            status="success",
        ).inc()

        return AgentResult(
            reply_message=AgentChatMessage(role="assistant", content=reply_text),
            tool_events=tool_events,
            error=None,
        )

    async def _get_telegram_admin_chat_id(self, chat: OmniChat) -> str | None:
        """Admin chat ID for Telegram notifications: TELEGRAM_BOT credentials or settings (delegates to shared helper)."""
        from src.application.services.omnichannel_integrations_config_service import (
            OmnichannelIntegrationsConfigService,
        )
        config_svc = OmnichannelIntegrationsConfigService(self.session)
        return await config_svc.get_telegram_admin_chat_id_for_clinic(chat.business_account_id)

    async def _allow_notification_once(
        self,
        *,
        key: str,
        ttl_seconds: int,
    ) -> bool:
        """Deduplicate chat notifications via Redis NX+EX."""
        try:
            redis = await get_redis()
            created = await redis.set(key, "1", nx=True, ex=ttl_seconds)
            return bool(created)
        except Exception:  # noqa: BLE001
            # Fail-open: do not lose critical operational notification due to Redis issue.
            return True

    async def handle_incoming_for_ai(
        self,
        message: OmniMessage,
        chat: OmniChat,
        contact: OmniContact | None,
    ) -> None:
        """Entry point after createInboundMessage(...).

        Legacy behaviour (LLMClient.generate_reply) is preserved when clinic AI agent
        is disabled; when clinic-level AI is enabled (ClinicAiSettings.ai_enabled=True)
        run_ai_agent is used instead, with graceful degradation on any error.
        """
        # Try to derive trace_id for this inbound message from source metadata
        trace_id = None
        if isinstance(message.source_metadata, dict):
            raw_trace = message.source_metadata.get("trace_id")
            if isinstance(raw_trace, str) and raw_trace:
                trace_id = raw_trace

        # Resolve effective settings
        effective = await self.settings_service.get_effective_settings(
            business_account_id=chat.business_account_id,
            channel_id=message.channel_id,
            chat_id=chat.id,
        )

        ai_mode = (effective.ai_mode or "DISABLED").upper()

        # Determine if full AI agent (function-calling) is enabled at clinic level.
        use_agent = False
        try:
            config = await AiConfigService(self.session).get_clinic_ai_config(chat.business_account_id)
            # Minimal and safe rule: when ai_enabled is false inside AiConfigService logic,
            # allow_personal_data is also False, but we still explicitly require base_url to be configured.
            if config.base_url:
                from src.domain.entities.clinic_ai_settings import ClinicAiSettings
                from sqlalchemy import select as sa_select

                result = await self.session.execute(
                    sa_select(ClinicAiSettings).where(ClinicAiSettings.clinic_id == chat.business_account_id).limit(1)
                )
                row = result.scalar_one_or_none()
                use_agent = bool(row and row.ai_enabled)
        except Exception:  # noqa: BLE001
            # If config resolution fails, fall back to legacy behaviour.
            logger.exception(
                "OmnichannelAIOrchestrator: failed to resolve clinic AI config for agent",
                extra={"chat_id": str(chat.id)},
            )

        if ai_mode == "DISABLED" and not use_agent:
            logger.info(
                "OmnichannelAIOrchestrator.skip_disabled",
                extra={
                    "component": "omni_ai_orchestrator",
                    "trace_id": trace_id,
                    "event": "ai_disabled",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "ai_mode": ai_mode,
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        # If full agent is enabled and provider configured, route to run_ai_agent;
        # otherwise use legacy suggestion/auto-reply flow via LLMClient.
        if use_agent:
            try:
                ctx = RequestContext(
                    clinic_id=chat.business_account_id,
                    user_id=None,
                    user_type="system",
                    trace_id=trace_id,
                    roles=set(),
                    permissions={"booking.ai_tools.use"},
                )
                result = await self.run_ai_agent(
                    chat=chat,
                    incoming_message=message,
                    request_context=ctx,
                )
                if result is None:
                    # Agent chose not to reply; behaviour same as legacy no-op.
                    return
                return
            except Exception:  # noqa: BLE001
                logger.exception(
                    "OmnichannelAIOrchestrator: run_ai_agent failed, falling back to legacy LLMClient",
                    extra={"chat_id": str(chat.id), "message_id": str(message.id)},
                )

        # Legacy path: use simple LLMClient.generate_reply with SafeAiClient built via factory.
        safe_client, client_ctx = await build_safe_ai_client(
            clinic_id=chat.business_account_id,
            session=self.session,
        )
        self.llm_client = self.llm_client or LLMClient(safe_client)

        if not self.llm_client.is_configured():
            logger.info(
                "OmnichannelAIOrchestrator: AI disabled because provider not configured",
                extra={
                    "component": "omni_ai_orchestrator",
                    "trace_id": trace_id,
                    "event": "provider_not_configured",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "clinic_id": str(chat.business_account_id),
                    "provider_type": client_ctx.provider_type,
                    "allow_personal_data": client_ctx.allow_personal_data,
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        # Escalation: client asked for live operator — set status and notify, do not call LLM
        if _client_asks_for_operator(message.content or ""):
            chat.status = "WAITING_FOR_OPERATOR"
            chat.ai_mode = "SUGGEST_ONLY"
            await self.session.flush()
            logger.info(
                "omni_escalation_client_asked_operator",
                extra={
                    "trace_id": trace_id,
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "business_account_id": str(chat.business_account_id),
                },
            )
            try:
                from src.application.services.notification_service import send_with_fallback

                message_text = f"Клиент запросил живого оператора в чате {chat.id}."
                admin_chat_id = await self._get_telegram_admin_chat_id(chat)
                if not settings.omni_ai_notify_operator_telegram_enabled:
                    return
                dedup_key = f"omni:notify:operator:{chat.id}"
                if await self._allow_notification_once(
                    key=dedup_key,
                    ttl_seconds=max(30, int(settings.omni_ai_notify_operator_dedup_seconds)),
                ):
                    await send_with_fallback(
                        message=message_text,
                        template="omni_ai_suggestion",
                        chat_id=admin_chat_id,
                        preferred_channel="telegram",
                    )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "OmnichannelAIOrchestrator: failed to notify admins about operator request",
                    extra={"chat_id": str(chat.id)},
                    exc_info=True,
                )
            return

        # Collect context messages and optional domain context (clinic name for prompt)
        last_messages = await self.chat_service.list_messages(chat_id=chat.id, limit=20)
        clinic_name: str | None = None
        from sqlalchemy import select
        from src.domain.entities.clinic import Clinic
        result = await self.session.execute(
            select(Clinic.name).where(Clinic.id == chat.business_account_id).limit(1)
        )
        name_val = result.scalar_one_or_none()
        if name_val and isinstance(name_val, str):
            clinic_name = name_val
        ctx = AIContext(
            business_account_id=chat.business_account_id,
            chat=chat,
            contact=contact,
            last_messages=last_messages,
            effective_settings=effective,
            clinic_name=clinic_name,
        )

        # Legacy LLM call; SafeAiClient inside LLMClient already respects provider policy.
        logger.info(
            "OmnichannelAIOrchestrator.legacy_llm_call",
            extra={
                "component": "omni_ai_orchestrator",
                "trace_id": trace_id,
                "event": "legacy_llm_call",
                "chat_id": str(chat.id),
                "message_id": str(message.id),
                "clinic_id": str(chat.business_account_id),
                "provider_type": client_ctx.provider_type,
                "allow_personal_data": client_ctx.allow_personal_data,
                "ai_mode": ai_mode,
            },
        )

        llm_reply = await self.llm_client.generate_reply(ctx)
        if llm_reply is None or not llm_reply.text.strip():
            logger.info(
                "OmnichannelAIOrchestrator.no_reply",
                extra={
                    "component": "omni_ai_orchestrator",
                    "trace_id": trace_id,
                    "event": "no_reply",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "ai_mode": ai_mode,
                    "correlation_chat_id": str(chat.id),
                    "correlation_message_id": str(message.id),
                },
            )
            return

        thresholds = effective.confidence_thresholds or {}
        auto_threshold = float(thresholds.get("auto_reply", 0.7))

        if ai_mode == "AUTO_REPLY":
            if llm_reply.confidence >= auto_threshold:
                logger.info(
                    "OmnichannelAIOrchestrator.auto_reply_success",
                    extra={
                        "component": "omni_ai_orchestrator",
                        "trace_id": trace_id,
                        "event": "auto_reply_success",
                        "chat_id": str(chat.id),
                        "message_id": str(message.id),
                        "clinic_id": str(chat.business_account_id),
                        "provider_type": client_ctx.provider_type,
                        "allow_personal_data": client_ctx.allow_personal_data,
                        "confidence": llm_reply.confidence,
                        "threshold": auto_threshold,
                    },
                )
                await self._auto_reply(chat, llm_reply)
            else:
                # Low confidence: mark for operator attention only (no message to client).
                omni_ai_escalations_total.labels(reason="low_confidence").inc()
                logger.info(
                    "OmnichannelAIOrchestrator: AUTO_REPLY below threshold, skipping reply",
                    extra={
                        "component": "omni_ai_orchestrator",
                        "event": "auto_reply_below_threshold",
                        "chat_id": str(chat.id),
                        "message_id": str(message.id),
                        "confidence": llm_reply.confidence,
                        "threshold": auto_threshold,
                        "correlation_chat_id": str(chat.id),
                        "correlation_message_id": str(message.id),
                    },
                )
        elif ai_mode == "SUGGEST_ONLY":
            logger.info(
                "OmnichannelAIOrchestrator.suggest_only_success",
                extra={
                    "component": "omni_ai_orchestrator",
                    "trace_id": trace_id,
                    "event": "suggest_only_success",
                    "chat_id": str(chat.id),
                    "message_id": str(message.id),
                    "clinic_id": str(chat.business_account_id),
                    "provider_type": client_ctx.provider_type,
                    "allow_personal_data": client_ctx.allow_personal_data,
                    "confidence": llm_reply.confidence,
                },
            )
            await self._suggest_only(chat, llm_reply)

    async def _auto_reply(self, chat: OmniChat, reply: LLMReply) -> None:
        """Create outbound AI message and dispatch to channel."""
        msg = await self.chat_service.append_outbound_message(
            chat=chat,
            actor_type="AI",
            content=reply.text,
            channel_id=chat.channel_id,
        )
        omni_ai_auto_replies_total.labels(
            account_bucket=account_bucket_label(chat.business_account_id),
        ).inc()
        await self.dispatcher.dispatch_to_channel(msg)

    async def _suggest_only(self, chat: OmniChat, reply: LLMReply) -> None:
        """Create TEMPLATE message as AI draft suggestion for admins."""
        draft = OmniMessage(
            chat_id=chat.id,
            contact_id=None,
            channel_id=None,
            direction="OUTBOUND",
            actor_type="AI",
            content_type="TEMPLATE",
            content=reply.text,
            source_metadata={
                "kind": "ai_suggestion",
                "confidence": reply.confidence,
            },
        )
        self.session.add(draft)
        await self.session.flush()
        omni_ai_suggestions_total.labels(
            account_bucket=account_bucket_label(chat.business_account_id),
        ).inc()
        logger.info(
            "omni_ai_suggestion_created",
            extra={
                "chat_id": str(chat.id),
                "message_id": str(draft.id),
                "business_account_id": str(chat.business_account_id),
            },
        )
        # Notify admins (log + optional Telegram to admin chat)
        try:
            from src.application.services.notification_service import send_with_fallback

            message_text = (
                f"Новый черновик ответа AI в омниканальном чате. Chat ID: {chat.id}. "
                "Откройте раздел «Единый чат» в админке."
            )
            admin_chat_id = await self._get_telegram_admin_chat_id(chat)
            if not settings.omni_ai_notify_suggestion_telegram_enabled:
                return
            dedup_key = f"omni:notify:suggest:{chat.id}"
            if await self._allow_notification_once(
                key=dedup_key,
                ttl_seconds=max(30, int(settings.omni_ai_notify_suggestion_dedup_seconds)),
            ):
                await send_with_fallback(
                    message=message_text,
                    template="omni_ai_suggestion",
                    chat_id=admin_chat_id,
                    preferred_channel="telegram",
                )
        except Exception:  # noqa: BLE001
            logger.warning(
                "OmnichannelAIOrchestrator: failed to notify admins about suggestion",
                extra={"chat_id": str(chat.id), "message_id": str(draft.id)},
                exc_info=True,
            )

