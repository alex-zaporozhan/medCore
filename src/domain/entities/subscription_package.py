"""SubscriptionPackage entity model for loyalty subscription packages."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class SubscriptionPackage(Base):
    """Commercial subscription/loyalty package offered by clinic."""

    __tablename__ = "subscription_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # visits | balance | mixed
    kind: Mapped[str] = mapped_column(String(32), nullable=False)

    # list of service IDs covered by this package
    services_included: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
    )

    total_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    __table_args__ = (
        Index("idx_subscription_packages_clinic_id", "clinic_id"),
        Index("idx_subscription_packages_clinic_code", "clinic_id", "code"),
    )

