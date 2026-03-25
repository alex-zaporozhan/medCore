from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.booking_service import BookingService
from src.application.services.schedule_service import ScheduleService
from src.application.services.patient_service import PatientService
from src.core.context import RequestContext


@dataclass
class ToolContext:
    """
    Execution context passed to all AI tools.

    AiToolContext (ARCH contract, QA_ARCH):
    - trace_id: logical trace for the whole AI interaction;
    - clinic_id: current clinic / business account;
    - user_id / system actor: who initiates the call (admin, system, AI runner);
    - roles / permissions: RBAC snapshot used for tool filtering and handlers;
    - source: logical channel identifier (\"omni_chat\", \"ai_task_manager\", \"admin_tool\", etc.).
    """

    db: AsyncSession
    clinic_id: UUID
    request_context: RequestContext
    source: str

    booking_service: BookingService
    schedule_service: ScheduleService
    patient_service: PatientService | None = None

    @property
    def trace_id(self) -> str | None:
        return self.request_context.trace_id

    @property
    def user_id(self) -> UUID | None:
        return self.request_context.user_id

    @property
    def user_type(self) -> str | None:
        return self.request_context.user_type

    @property
    def roles(self) -> set[str]:
        return self.request_context.roles

    @property
    def permissions(self) -> set[str]:
        return self.request_context.permissions


class ToolError(BaseModel):
    """Structured error result returned by tools instead of raising."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class Tool(ABC):
    """Base interface for AI tools used via function calling."""

    name: str
    description: str
    args_schema: type[BaseModel]
    # Optional RBAC metadata used by tools_registry to filter availability.
    allowed_roles: set[str] | None = None
    required_permissions: set[str] | None = None

    @abstractmethod
    async def __call__(self, ctx: ToolContext, args: BaseModel) -> BaseModel | ToolError:  # pragma: no cover - interface only
        """Execute tool with given context and validated args."""
        raise NotImplementedError


@runtime_checkable
class AiTool(Protocol):
    """
    ARCH alias for AI tool interface.

    Semantically equivalent to Tool, kept as a separate protocol to make the
    AiTool / AiToolContext contract explicit in code and docs.
    """

    name: str
    description: str
    args_schema: type[BaseModel]
    allowed_roles: set[str] | None
    required_permissions: set[str] | None

    async def __call__(self, ctx: "AiToolContext", args: BaseModel) -> BaseModel | ToolError: ...


AiToolContext = ToolContext

