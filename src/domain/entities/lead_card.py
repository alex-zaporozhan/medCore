"""LeadCard entity model for CRM leads (sales deals)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    TIMESTAMP,
    Numeric,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class LeadCard(Base):
    """Single lead/deal in clinic CRM sales pipeline."""

    __tablename__ = "lead_cards"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lead_pipelines.id"), nullable=False, index=True
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lead_stages.id"), nullable=False, index=True
    )
    omnichannel_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("omni_contacts.id"), nullable=True, index=True
    )
    # Optional link to marketing attribution / visit entity (if available in the system)
    visit_attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True, index=True
    )
    primary_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    # Optional raw UTM tags for basic attribution and reporting
    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Forecast only (e.g. catalog price); not an ERP financial fact.
    estimated_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )
    # Mirror of ERP income (financial_transactions); updated via LeadService.update_actual_value_from_erp.
    actual_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0.00"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="open"
    )  # open|success|lost
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    lost_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_lead_cards_clinic_stage",
            "clinic_id",
            "stage_id",
        ),
        Index(
            "idx_lead_cards_clinic_status",
            "clinic_id",
            "status",
        ),
        Index(
            "idx_lead_cards_clinic_created_at",
            "clinic_id",
            "created_at",
        ),
    )

