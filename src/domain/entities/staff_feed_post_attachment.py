"""File attachment on a staff feed post."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffFeedPostAttachment(Base):
    __tablename__ = "staff_feed_post_attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_feed_posts.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_staff_feed_post_attachments_post_id", "post_id"),)
