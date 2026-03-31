"""Kanban board configuration (clinic or personal)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

if TYPE_CHECKING:
    from src.domain.entities.task_board_column import TaskBoardColumn


class TaskBoard(Base):
    """A board groups column layout; tasks still use global Task.status (variant A)."""

    __tablename__ = "task_boards"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    #: clinic_wide — общая доска клиники; personal — личная раскладка
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="clinic_wide")
    owner_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    columns: Mapped[list[TaskBoardColumn]] = relationship(
        "TaskBoardColumn",
        back_populates="board",
        order_by="TaskBoardColumn.sort_order",
        cascade="all, delete-orphan",
    )
