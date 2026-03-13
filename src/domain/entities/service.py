"""Service entity model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Service(Base):
    """Service model."""

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # терапия/хирургия/ортодонтия
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_services_clinic_id", "clinic_id"),
        Index("idx_services_is_active", "is_active"),
    )
