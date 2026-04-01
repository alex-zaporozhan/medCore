"""Comment on a staff feed post."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffFeedComment(Base):
    __tablename__ = "staff_feed_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_feed_posts.id"), nullable=False)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_feed_comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_staff_feed_comments_post_id", "post_id"),
        Index("ix_staff_feed_comments_parent_comment_id", "parent_comment_id"),
        Index("ix_staff_feed_comments_deleted_at", "deleted_at"),
    )
