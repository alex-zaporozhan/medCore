"""Message in staff chat room."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffChatMessage(Base):
    __tablename__ = "staff_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_chat_rooms.id"), nullable=False)
    author_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_staff_chat_messages_room_created", "room_id", "created_at"),)
