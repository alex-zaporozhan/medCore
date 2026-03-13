"""ClinicPlan entity — таблица clinic_plans (legacy). Не используется в API и UI."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ClinicPlan(Base):
    """Legacy: plan per clinic. Table may exist in DB; no endpoints or UI use it."""

    __tablename__ = "clinic_plans"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), primary_key=True
    )
    plan: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="basic"
    )
    feature_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
