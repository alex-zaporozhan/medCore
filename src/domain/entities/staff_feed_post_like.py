"""Staff feed post like entity (unique per post + author_admin_id)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffFeedPostLike(Base):
    __tablename__ = "staff_feed_post_likes"

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
    author_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "author_admin_id", name="ux_staff_feed_post_likes_post_admin"),
        Index("ix_staff_feed_post_likes_post_id", "post_id"),
    )

