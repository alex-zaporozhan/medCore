"""DigitalFormTemplate entity model for paperless office form templates."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, JSON, String, TIMESTAMP, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class DigitalFormTemplate(Base):
    """Template for digital forms (questionnaires, consents, contracts)."""

    __tablename__ = "digital_form_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    # Schema describing fields; subset of JSON Schema / custom lightweight format.
    schema: Mapped[dict] = mapped_column(JSON, nullable=False)

    requires_signature: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "code",
            "version",
            name="ux_digital_form_templates_clinic_code_version",
        ),
        Index(
            "idx_digital_form_templates_clinic_code_active",
            "clinic_id",
            "code",
            "active",
        ),
    )

