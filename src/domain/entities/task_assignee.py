"""Many-to-many: task ↔ admin assignees (коробка: несколько исполнителей)."""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True
    )
