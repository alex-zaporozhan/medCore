from dataclasses import dataclass, field
from typing import Literal, Set
from uuid import UUID


UserType = Literal["admin", "doctor", "patient", "system"]


@dataclass
class RequestContext:
    clinic_id: UUID | None
    user_id: UUID | None
    user_type: UserType | None
    trace_id: str | None = None
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)

