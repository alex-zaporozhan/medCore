"""DTOs for configurable pipeline stage semantics mapping."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadStageSemanticMappingDto(BaseModel):
    semantic: str = Field(description="Stable semantic code, e.g. start/scheduled/stale/won/lost.")
    stage_id: UUID

    model_config = ConfigDict(from_attributes=True)


class LeadStageResolvedSemanticDto(BaseModel):
    """Per-stage semantic as resolved by LeadStageSemanticsService (mapping table + code infer)."""

    stage_id: UUID
    semantic: str | None = Field(
        default=None,
        description="Resolved semantic for this stage, or null if unknown.",
    )


class LeadStageSemanticMappingsResponse(BaseModel):
    pipeline_id: UUID
    supported_semantics: list[str]
    mappings: list[LeadStageSemanticMappingDto]
    resolved_stage_semantics: list[LeadStageResolvedSemanticDto] = Field(
        default_factory=list,
        description="Same resolution logic as server-side transition checks (parity with strict Kanban).",
    )


class UpsertLeadStageSemanticMappingRequest(BaseModel):
    semantic: str
    stage_id: UUID

