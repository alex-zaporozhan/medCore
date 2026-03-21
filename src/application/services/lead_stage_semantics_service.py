from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_stage_semantic_map import LeadStageSemanticMap


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


class LeadStageSemanticsService:
    """
    Resolve semantic meaning of pipeline stages.

    Priority:
    1) explicit mapping table lead_stage_semantic_map (pipeline_id + semantic -> stage_id)
    2) infer semantic from stage.code (best-effort, non-breaking)
    """

    # Stable semantic codes used by state-machine and event mapping.
    SEM_START = "start"
    SEM_SCHEDULED = "scheduled"
    SEM_STALE = "stale"
    SEM_WON = "won"
    SEM_LOST = "lost"

    _INFER_MAP: dict[str, str] = {
        # start
        "new": SEM_START,
        "inbox": SEM_START,
        "lead_new": SEM_START,
        "created": SEM_START,
        # scheduled
        "booked": SEM_SCHEDULED,
        "scheduled": SEM_SCHEDULED,
        "appointment": SEM_SCHEDULED,
        "appt": SEM_SCHEDULED,
        # stale
        "stale": SEM_STALE,
        "follow_up": SEM_STALE,
        "need_follow_up": SEM_STALE,
        # won
        "won": SEM_WON,
        "win": SEM_WON,
        "success": SEM_WON,
        "closed_won": SEM_WON,
        # lost
        "lost": SEM_LOST,
        "cancelled": SEM_LOST,
        "canceled": SEM_LOST,
        "no_show": SEM_LOST,
        "noshow": SEM_LOST,
        "closed_lost": SEM_LOST,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_stage_id_for_semantic(
        self,
        *,
        clinic_id: UUID,
        pipeline_id: UUID,
        semantic: str,
    ) -> UUID | None:
        sem = _norm(semantic)
        if not sem:
            return None
        stmt: Select[tuple[LeadStageSemanticMap]] = select(LeadStageSemanticMap).where(
            LeadStageSemanticMap.clinic_id == clinic_id,
            LeadStageSemanticMap.pipeline_id == pipeline_id,
            LeadStageSemanticMap.semantic == sem,
        ).limit(1)
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        return row.stage_id if row else None

    async def get_semantic_for_stage(
        self,
        *,
        clinic_id: UUID,
        pipeline_id: UUID,
        stage: LeadStage,
    ) -> str | None:
        # Reverse lookup via mapping table.
        stmt: Select[tuple[str]] = select(LeadStageSemanticMap.semantic).where(
            LeadStageSemanticMap.clinic_id == clinic_id,
            LeadStageSemanticMap.pipeline_id == pipeline_id,
            LeadStageSemanticMap.stage_id == stage.id,
        ).limit(1)
        res = await self.session.execute(stmt)
        sem = res.scalar_one_or_none()
        if sem:
            return _norm(sem)
        # Infer from stage.code.
        return self._INFER_MAP.get(_norm(stage.code))

    async def set_semantic_mapping(
        self,
        *,
        clinic_id: UUID,
        pipeline_id: UUID,
        semantic: str,
        stage_id: UUID,
    ) -> None:
        sem = _norm(semantic)
        if not sem:
            raise ValueError("semantic is required")
        # Replace any existing mapping for semantic in this pipeline.
        await self.session.execute(
            delete(LeadStageSemanticMap).where(
                LeadStageSemanticMap.pipeline_id == pipeline_id,
                LeadStageSemanticMap.semantic == sem,
            )
        )
        self.session.add(
            LeadStageSemanticMap(
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                semantic=sem,
                stage_id=stage_id,
            )
        )
        await self.session.flush()

