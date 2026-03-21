"""Clinic-scoped directed relationship between patients for loyalty spend/history (LOY_FAMILY_013).

Distinct from :class:`~src.domain.entities.package_family_link.PackageFamilyLink`, which
only grants access to one purchased subscription.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class FamilyLink(Base):
    """Directed link: primary (owner) -> related patient with optional loyalty permissions."""

    __tablename__ = "family_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )
    primary_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    related_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )

    relation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="other"
    )  # parent|child|spouse|guardian|other

    can_spend_from_owner_loyalty: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    can_view_owner_history: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    spending_limit_total: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    spending_limit_periodic: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )  # max monetary usage per calendar month (UTC)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional LoyaltyGroup (LOY_FAMILY I3); spend rules still use directed link fields.
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "primary_patient_id",
            "related_patient_id",
            name="uq_family_links_clinic_primary_related",
        ),
        Index(
            "idx_family_links_clinic_primary",
            "clinic_id",
            "primary_patient_id",
        ),
        Index(
            "idx_family_links_clinic_related",
            "clinic_id",
            "related_patient_id",
        ),
    )
