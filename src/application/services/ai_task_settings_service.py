"""Service for managing AiTaskSettings per clinic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.ai_task_settings import AiTaskSettings


ALLOWED_CREATION_MODES = {"confirm", "auto"}


class AiTaskSettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_default(self, clinic_id: UUID) -> AiTaskSettings:
        result = await self._session.execute(
            select(AiTaskSettings).where(AiTaskSettings.clinic_id == clinic_id).limit(1)
        )
        row: AiTaskSettings | None = result.scalars().first()
        if row is not None:
            return row
        row = AiTaskSettings(clinic_id=clinic_id)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update_settings(self, clinic_id: UUID, data: dict) -> AiTaskSettings:
        settings = await self.get_or_create_default(clinic_id)

        if "creation_mode" in data:
            mode = str(data["creation_mode"] or "").strip()
            if mode and mode not in ALLOWED_CREATION_MODES:
                raise ValueError("Invalid creation_mode")
            settings.creation_mode = mode or settings.creation_mode

        if "ai_tasks_enabled" in data:
            settings.ai_tasks_enabled = bool(data["ai_tasks_enabled"])

        if "allowed_task_classes" in data and data["allowed_task_classes"] is not None:
            settings.allowed_task_classes = [str(x) for x in (data["allowed_task_classes"] or [])]

        for field in ("daily_clinic_limit", "daily_patient_limit", "daily_doctor_limit"):
            if field in data and data[field] is not None:
                value = int(data[field])
                if value < 0:
                    raise ValueError(f"Invalid {field}")
                setattr(settings, field, value)

        if "analyzer_thresholds" in data:
            settings.analyzer_thresholds = data["analyzer_thresholds"]

        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings

