"""Staff feed post acknowledgement (read receipt)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffFeedPostAck(Base):
    __tablename__ = "staff_feed_post_acks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "admin_id", name="ux_staff_feed_post_acks_post_admin"),
        Index("ix_staff_feed_post_acks_post_id", "post_id"),
    )

