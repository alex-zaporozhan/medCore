"""TaskComment entity for task discussion."""

import uuid
from datetime import datetime

from sqlalchemy import Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TaskComment(Base):
    """Comment attached to a Task."""

    __tablename__ = "task_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

