"""ESignature entity model for electronic signatures of digital forms."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, String, TIMESTAMP, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ESignature(Base):
    """Electronic signature attached to a digital form submission."""

    __tablename__ = "e_signatures"

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
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=True,
        index=True,
    )
    digital_form_submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_form_submissions.id"),
        nullable=False,
        index=True,
    )

    signed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    signer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signer_role: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # patient|legal_representative|admin|doctor
    signature_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # drawn|checkbox|external_provider

    signature_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "idx_e_signatures_clinic_patient",
            "clinic_id",
            "patient_id",
        ),
    )

