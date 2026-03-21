"""Add lead_stage_semantic_map table for pipeline semantics.

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_stage_semantic_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic", sa.String(length=64), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["pipeline_id"], ["lead_pipelines.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["lead_stages.id"]),
        sa.UniqueConstraint("pipeline_id", "semantic", name="ux_lead_stage_semantic_pipeline_semantic"),
    )
    op.create_index("ix_lead_stage_semantic_map_clinic_id", "lead_stage_semantic_map", ["clinic_id"], unique=False)
    op.create_index("ix_lead_stage_semantic_map_pipeline_id", "lead_stage_semantic_map", ["pipeline_id"], unique=False)
    op.create_index("ix_lead_stage_semantic_map_stage_id", "lead_stage_semantic_map", ["stage_id"], unique=False)
    op.create_index(
        "idx_lead_stage_semantic_pipeline",
        "lead_stage_semantic_map",
        ["clinic_id", "pipeline_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_lead_stage_semantic_pipeline", table_name="lead_stage_semantic_map")
    op.drop_index("ix_lead_stage_semantic_map_stage_id", table_name="lead_stage_semantic_map")
    op.drop_index("ix_lead_stage_semantic_map_pipeline_id", table_name="lead_stage_semantic_map")
    op.drop_index("ix_lead_stage_semantic_map_clinic_id", table_name="lead_stage_semantic_map")
    op.drop_table("lead_stage_semantic_map")

