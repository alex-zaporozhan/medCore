"""Publish policy for staff announcements (wall)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffAnnouncementPublishPolicy(Base):
    __tablename__ = "staff_announcement_publish_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)  # role | user
    scope_value: Mapped[str] = mapped_column(String(64), nullable=False)  # role code or UUID string
    can_publish: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "scope_type",
            "scope_value",
            name="ux_staff_announce_policy_scope",
        ),
        Index("ix_staff_announce_policy_clinic", "clinic_id"),
    )

