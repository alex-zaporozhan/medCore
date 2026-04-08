"""Per-organization entitlements from tariff snapshot (SaaS platform billing)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OrganizationEntitlement(Base):
    """Granted feature keys for an organization (after paid provisioning)."""

    __tablename__ = "organization_entitlements"
    __table_args__ = (
        UniqueConstraint("organization_id", "entitlement_key", name="ux_org_entitlements_org_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="tariff_snapshot",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
