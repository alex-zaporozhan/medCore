"""Domain event base model used by in-process EventBus."""

from typing import Any, Dict

from pydantic import BaseModel


class DomainEvent(BaseModel):
    """Generic domain event."""

    name: str
    payload: Dict[str, Any]

