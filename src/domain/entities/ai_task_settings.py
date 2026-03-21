"""AI Task Manager settings per clinic.

This is a dedicated settings entity for AI Task Manager (TASKS_AI_021) and is
intentionally separate from ClinicAiSettings:
- ClinicAiSettings controls provider policy / personal data / global AI modes.
- AiTaskSettings controls task generation heuristics, limits and confirmation mode.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AiTaskSettings(Base):
    __tablename__ = "ai_task_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Master switch for the whole feature (per clinic).
    ai_tasks_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # "confirm" -> create as ai_suggested (human-in-the-loop)
    # "auto" -> create as ai_auto
    creation_mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'confirm'"),
    )

    # Allowed "classes" of AI tasks; empty -> allow all supported classes.
    allowed_task_classes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'::text[]"),
    )

    # Limits (soft, best-effort).
    daily_clinic_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("20"),
    )
    daily_patient_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("3"),
    )
    daily_doctor_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("5"),
    )

    # Optional per-clinic thresholds for analyzer (JSON blob to avoid frequent migrations).
    # Example:
    # {
    #   "no_show_window_days": 30,
    #   "no_show_min_count": 2,
    #   "erp_error_window_days": 1,
    #   "erp_error_min_count": 3,
    #   "stale_leads_days": 7
    # }
    analyzer_thresholds: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

