"""VisitAttribution entity model for marketing source attribution (first-touch)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class VisitAttribution(Base):
    """Single marketing attribution record tied to a landing/session."""

    __tablename__ = "visit_attributions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    # Optional links filled as the contact converts through the funnel
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True, index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    traffic_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    landing_page: Mapped[str | None] = mapped_column(String(512), nullable=True)
    anchor: Mapped[str | None] = mapped_column(String(128), nullable=True)

    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_visit_attr_clinic_created",
            "clinic_id",
            "created_at",
        ),
        Index(
            "idx_visit_attr_clinic_session",
            "clinic_id",
            "session_id",
        ),
    )
