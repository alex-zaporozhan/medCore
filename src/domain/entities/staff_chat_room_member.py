"""Membership in a staff chat room."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffChatRoomMember(Base):
    __tablename__ = "staff_chat_room_members"

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_chat_rooms.id"), nullable=False)
    admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False)
    #: task_core | invite | general | group | dm — см. StaffCollaborationService
    membership_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (PrimaryKeyConstraint("room_id", "admin_id"),)
