"""Agreement settings per clinic (PD text, allow registration without mailing consent)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AgreementSettings(Base):
    """One row per clinic: editable PD agreement text and registration policy."""

    __tablename__ = "agreement_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, unique=True, index=True
    )
    pd_agreement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_registration_without_mailing_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
