"""Per-clinic integration settings (1C, Bitrix24): URL and encrypted credentials."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ClinicIntegrationSettings(Base):
    """One row per clinic per provider: 1C, Bitrix24."""

    __tablename__ = "clinic_integration_settings"
    __table_args__ = (UniqueConstraint("clinic_id", "provider", name="uq_clinic_integration_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    api_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
