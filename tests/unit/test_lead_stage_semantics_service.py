from __future__ import annotations

import uuid

import pytest

from src.application.services.lead_stage_semantics_service import LeadStageSemanticsService
from src.domain.entities.lead_stage import LeadStage


def _stage(code: str) -> LeadStage:
    s = LeadStage()
    s.id = uuid.uuid4()
    s.clinic_id = uuid.uuid4()
    s.pipeline_id = uuid.uuid4()
    s.order = 0
    s.code = code
    s.name = code
    s.probability = 0
    s.color = "#000"
    return s


@pytest.mark.asyncio
async def test_infer_semantic_from_code_without_db():
    class _NoopSession:
        async def execute(self, *args, **kwargs):
            class _Res:
                def scalar_one_or_none(self):
                    return None
            return _Res()

    svc = LeadStageSemanticsService(_NoopSession())  # type: ignore[arg-type]
    sem = await svc.get_semantic_for_stage(
        clinic_id=uuid.uuid4(),
        pipeline_id=uuid.uuid4(),
        stage=_stage("scheduled"),
    )
    assert sem == LeadStageSemanticsService.SEM_SCHEDULED

