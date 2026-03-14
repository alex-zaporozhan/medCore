"""ServiceConsumable entity model linking services to inventory products."""

import uuid
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ServiceConsumable(Base):
    """Technical card for service: which products and how much to consume per service."""

    __tablename__ = "service_consumables"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity_per_service: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        Index(
            "idx_service_consumables_clinic_service",
            "clinic_id",
            "service_id",
        ),
        Index(
            "idx_service_consumables_clinic_product",
            "clinic_id",
            "product_id",
        ),
    )

