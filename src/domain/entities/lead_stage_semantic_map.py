"""Semantic mapping for lead pipeline stages (CRM_EVENTS_007 / CRM_AI_009).

We keep this as a separate table to avoid changing LeadStage schema while
still allowing clinics to configure semantic meaning of their custom stages.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class LeadStageSemanticMap(Base):
    __tablename__ = "lead_stage_semantic_map"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lead_pipelines.id"),
        nullable=False,
        index=True,
    )
    semantic: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lead_stages.id"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("pipeline_id", "semantic", name="ux_lead_stage_semantic_pipeline_semantic"),
        Index("idx_lead_stage_semantic_pipeline", "clinic_id", "pipeline_id"),
    )

