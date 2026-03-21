"""Domain event base model used by in-process EventBus."""

from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Generic domain event."""

    name: str
    payload: Dict[str, Any]
    event_id: UUID = Field(default_factory=uuid4)

