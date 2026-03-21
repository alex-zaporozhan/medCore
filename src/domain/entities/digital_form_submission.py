"""DigitalFormSubmission entity — form instance (Paperless FormInstance)."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, String, TIMESTAMP, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class DigitalFormSubmission(Base):
    """Concrete form instance linked to patient/booking (template snapshot via template_id)."""

    __tablename__ = "digital_form_submissions"

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

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_form_templates.id"),
        nullable=False,
        index=True,
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=True,
        index=True,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="signed", index=True
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )

    submitted_by: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # patient|admin|doctor|system|issued

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Payload validated against template.schema (filled_data).
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    signature_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("e_signatures.id"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index(
            "idx_digital_form_submissions_clinic_patient",
            "clinic_id",
            "patient_id",
        ),
        Index(
            "idx_digital_form_submissions_clinic_booking",
            "clinic_id",
            "booking_id",
        ),
        Index(
            "idx_digital_form_submissions_booking_status",
            "booking_id",
            "status",
        ),
    )

