"""Cashbox entity model for ERP finance."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, ForeignKey, Index, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Cashbox(Base):
    """Logical cashbox where clinic money movements are tracked."""

    __tablename__ = "cashboxes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # cash|card|bank_account|other
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="RUB"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
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
        Index("idx_cashboxes_clinic_id", "clinic_id"),
    )

