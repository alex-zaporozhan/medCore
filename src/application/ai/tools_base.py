from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.booking_service import BookingService
from src.application.services.schedule_service import ScheduleService
from src.application.services.patient_service import PatientService
from src.core.context import RequestContext


@dataclass
class ToolContext:
    """Execution context passed to all AI tools."""

    db: AsyncSession
    clinic_id: UUID
    request_context: RequestContext

    booking_service: BookingService
    schedule_service: ScheduleService
    patient_service: PatientService | None = None


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

    @abstractmethod
    async def __call__(self, ctx: ToolContext, args: BaseModel) -> BaseModel | ToolError:  # pragma: no cover - interface only
        """Execute tool with given context and validated args."""
        raise NotImplementedError

