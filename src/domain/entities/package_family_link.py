"""PackageFamilyLink entity: family members allowed to use a customer subscription (B6.1)."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PackageFamilyLink(Base):
    """Link: customer_subscription_id -> patient_id (family member who can spend from this package). Owner (CustomerSubscription.patient_id) has access by default."""

    __tablename__ = "package_family_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "customer_subscription_id",
            "patient_id",
            name="uq_package_family_link_sub_patient",
        ),
    )
