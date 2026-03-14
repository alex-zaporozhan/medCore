"""TrafficSource entity model for marketing channels (UTM source/medium)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TrafficSource(Base):
    """Marketing traffic source for attribution (e.g. Google Ads, VK, Instagram)."""

    __tablename__ = "traffic_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    budget_planned: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    budget_actual: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    start_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
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
        Index("idx_traffic_sources_clinic_id", "clinic_id"),
        Index("idx_traffic_sources_clinic_code", "clinic_id", "code"),
    )

