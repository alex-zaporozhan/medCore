"""Admin API: omnichannel UI helpers (available AI tools)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.ai.tools_base import ToolContext
from src.application.ai.tools_registry import list_tools_for_context
from src.application.services.booking_service import BookingService
from src.application.services.schedule_service import ScheduleService
from src.application.services.patient_service import PatientService


router = APIRouter(prefix="/admin/omni", tags=["admin-omni-tools"])


class AvailableToolDto(BaseModel):
    tool_id: str
    label: str
    description: str
    required_permissions: list[str] | None = None
    allowed_roles: list[str] | None = None


class AvailableToolsResponse(BaseModel):
    items: list[AvailableToolDto]


@router.get(
    "/available-tools",
    response_model=AvailableToolsResponse,
    dependencies=[Depends(require_permissions("view_dashboard"))],
)
async def get_available_tools(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> AvailableToolsResponse:
    """
    Return AI tools available for current admin user in Omni UI context.

    This endpoint is used by frontend to disable/hide AI actions when backend tools
    are not allowed by RBAC or not registered.
    """
    if context.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic context is required",
        )

    tool_ctx = ToolContext(
        db=session,
        clinic_id=context.clinic_id,
        request_context=context,
        source="admin_ui",
        booking_service=BookingService(session),
        schedule_service=ScheduleService(session),
        patient_service=PatientService(session),
    )

    tools = list_tools_for_context(tool_ctx, source="admin_ui")
    items: list[AvailableToolDto] = []
    for tool_id, tool in tools.items():
        required = getattr(tool, "required_permissions", None)
        allowed = getattr(tool, "allowed_roles", None)
        items.append(
            AvailableToolDto(
                tool_id=tool_id,
                label=getattr(tool, "name", tool_id),
                description=getattr(tool, "description", "") or "",
                required_permissions=sorted(list(required)) if required else None,
                allowed_roles=sorted(list(allowed)) if allowed else None,
            )
        )
    items.sort(key=lambda x: x.tool_id)
    return AvailableToolsResponse(items=items)

