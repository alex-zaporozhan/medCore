"""Add CRM lead pipelines, stages, cards and notes.

Revision ID: crm_leads_0001
Revises: z1a2b3c4d5e6
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "crm_leads_0001"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "lead_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_lead_pipelines_clinic_id",
        "lead_pipelines",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "lead_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["pipeline_id"], ["lead_pipelines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pipeline_id",
            "code",
            name="ux_lead_stages_pipeline_code",
        ),
    )
    op.create_index(
        "idx_lead_stages_clinic_pipeline_order",
        "lead_stages",
        ["clinic_id", "pipeline_id", "order"],
        unique=False,
    )

    op.create_table(
        "lead_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("omnichannel_contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "estimated_value",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "actual_value",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("lost_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["pipeline_id"], ["lead_pipelines.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["lead_stages.id"]),
        sa.ForeignKeyConstraint(
            ["omnichannel_contact_id"],
            ["omni_contacts.id"],
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["primary_booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_lead_cards_clinic_id",
        "lead_cards",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_lead_cards_clinic_stage",
        "lead_cards",
        ["clinic_id", "stage_id"],
        unique=False,
    )
    op.create_index(
        "idx_lead_cards_clinic_status",
        "lead_cards",
        ["clinic_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_lead_cards_clinic_created_at",
        "lead_cards",
        ["clinic_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "lead_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["lead_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_lead_notes_clinic_lead",
        "lead_notes",
        ["clinic_id", "lead_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_lead_notes_clinic_lead", table_name="lead_notes")
    op.drop_table("lead_notes")

    op.drop_index("idx_lead_cards_clinic_created_at", table_name="lead_cards")
    op.drop_index("idx_lead_cards_clinic_status", table_name="lead_cards")
    op.drop_index("idx_lead_cards_clinic_stage", table_name="lead_cards")
    op.drop_index("idx_lead_cards_clinic_id", table_name="lead_cards")
    op.drop_table("lead_cards")

    op.drop_index(
        "idx_lead_stages_clinic_pipeline_order",
        table_name="lead_stages",
    )
    op.drop_table("lead_stages")

    op.drop_index("idx_lead_pipelines_clinic_id", table_name="lead_pipelines")
    op.drop_table("lead_pipelines")

