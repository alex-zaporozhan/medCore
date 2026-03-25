from __future__ import annotations

from uuid import UUID
from typing import Dict

from src.application.ai.tools_base import AiTool, AiToolContext
from src.application.ai.tools_booking import (
    CancelBookingTool,
    CreateBookingTool,
    GetAvailableSlotsTool,
    RescheduleBookingTool,
)
from src.application.ai.tools_crm import (
    CreateTaskForLeadTool,
    SuggestNextStageForLeadTool,
    SummarizeLeadContextTool,
    UpdateLeadStageTool,
)
from src.application.ai.tools_tasks import AnalyzeAttentionForTasksTool


# Global registry of AI tools available for agents.
# Keys are stable tool identifiers used both by orchestrators and LLM tools schema.
_TOOLS_REGISTRY: Dict[str, AiTool] = {
    "get_available_slots": GetAvailableSlotsTool(),
    "create_booking": CreateBookingTool(),
    "cancel_booking": CancelBookingTool(),
    "reschedule_booking": RescheduleBookingTool(),
    # CRM AI tools (CRM_AI_009)
    "summarize_lead_context": SummarizeLeadContextTool(),
    "suggest_next_stage_for_lead": SuggestNextStageForLeadTool(),
    "update_lead_stage": UpdateLeadStageTool(),
    "create_task_for_lead": CreateTaskForLeadTool(),
    # Tasks AI tools (TASKS_AI_021)
    "analyze_attention_for_tasks": AnalyzeAttentionForTasksTool(),
}


def get_tool(tool_id: str) -> AiTool | None:
    """Return tool by id or None if not registered."""
    return _TOOLS_REGISTRY.get(tool_id)


def list_tools_for_context(context: AiToolContext, source: str | None = None) -> dict[str, AiTool]:
    """
    Return tools available for given AiToolContext and logical source.

    ARCH contract (QA_ARCH):
    - takes full AiToolContext (clinic_id, roles, permissions, trace_id, source);
    - uses RBAC rules and channel/source to filter out tools that must not be
      exposed in the current context;
    - returns a mapping of tool_id → AiTool that is then used to build tools_schema.

    vNext implementation:
    - each AiTool may declare `allowed_roles` / `required_permissions` metadata;
    - list_tools_for_context enforces this metadata against context.roles and
      context.permissions and can additionally restrict tools for specific
      sources/channels (e.g. patient vs admin chats).
    """
    # Derive effective source from explicit argument or context.
    effective_source = source or context.source

    result: Dict[str, AiTool] = {}

    for tool_id, tool in _TOOLS_REGISTRY.items():
        roles = {r.lower() for r in (context.roles or set())}
        perms = {p.lower() for p in (context.permissions or set())}

        # Enforce per-tool allowed_roles / required_permissions metadata if present.
        if getattr(tool, "allowed_roles", None):
            allowed = {r.lower() for r in tool.allowed_roles}  # type: ignore[attr-defined]
            if not (roles & allowed):
                continue

        if getattr(tool, "required_permissions", None):
            required = {p.lower() for p in tool.required_permissions}  # type: ignore[attr-defined]
            if not required.issubset(perms):
                continue

        # Example of channel-level restriction: disallow any modifying tools in
        # чисто пациентском канале. Для этого полагаемся на соглашение об id
        # канала, чтобы не зашивать бизнес-логику в AiTool.
        if effective_source == "patient_chat" and tool_id.startswith(
            ("create_", "update_", "cancel_", "reschedule_")
        ):
            continue

        result[tool_id] = tool

    return result


def get_default_tools_for_clinic(clinic_id: UUID) -> dict[str, AiTool]:
    """
    Backwards-compatible helper used by existing orchestrator code.

    Clinic-specific filtering will be implemented later on top of the shared
    registry; for now all clinics share the same tool set.
    """
    return dict(_TOOLS_REGISTRY)

