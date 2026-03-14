"""Warehouse entity model for ERP inventory."""

import uuid

from sqlalchemy import String, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Warehouse(Base):
    """Clinic warehouse, phase 1: usually one default per clinic."""

    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    __table_args__ = (
        Index("idx_warehouses_clinic_id", "clinic_id"),
    )

