"""Association task ↔ tag definition."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TaskTaskTag(Base):
    __tablename__ = "task_task_tags"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_tag_definitions.id", ondelete="CASCADE"), primary_key=True, index=True
    )
