"""Column on a task board: maps to Task.status with optional label override."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.domain.entities.task_board import TaskBoard


class TaskBoardColumn(Base):
    """Ordered column; mapped_status is one of TASK_STATUSES (workflow unchanged)."""

    __tablename__ = "task_board_columns"
    __table_args__ = (UniqueConstraint("board_id", "mapped_status", name="uq_task_board_column_status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_boards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mapped_status: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    board: Mapped[TaskBoard] = relationship("TaskBoard", back_populates="columns")
