"""ServiceDoctor entity model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ServiceDoctor(Base):
    """Link between services and doctors."""

    __tablename__ = "service_doctors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False, index=True
    )
    custom_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ux_service_doctors_service_doctor",
            "service_id",
            "doctor_id",
            unique=True,
        ),
    )

