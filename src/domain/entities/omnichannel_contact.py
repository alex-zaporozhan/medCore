"""Omnichannel Contact entity model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Contact(Base):
    """Contact model for omnichannel assistant."""

    __tablename__ = "omni_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_account_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emails: Mapped[list[str] | None] = mapped_column(
        postgresql.ARRAY(String(255)), nullable=True
    )
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_ids: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # telegram_user_id, whatsapp_number, vk_user_id, etc.
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(
        postgresql.ARRAY(String(64)), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_omni_contacts_business_account_phone",
            "business_account_id",
            "primary_phone",
        ),
    )

