"""Add recall and messaging tables.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recall_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filter_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_segments_clinic_id", "recall_segments", ["clinic_id"])

    op.create_table(
        "recall_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_templates_clinic_id", "recall_templates", ["clinic_id"])

    op.create_table(
        "recall_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["recall_segments.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["recall_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_campaigns_clinic_id", "recall_campaigns", ["clinic_id"])

    op.create_table(
        "recall_automations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("trigger_config_json", postgresql.JSONB(), nullable=True),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["recall_segments.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["recall_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_automations_clinic_id", "recall_automations", ["clinic_id"])

    op.create_table(
        "notification_channel_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("config_json", postgresql.JSONB(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_channel_configs_clinic_id", "notification_channel_configs", ["clinic_id"])

    op.create_table(
        "patient_communication_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "channel", name="ux_patient_channel"),
    )
    op.create_index("ix_patient_communication_preferences_patient_id", "patient_communication_preferences", ["patient_id"])

    op.create_table(
        "recall_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("automation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["recall_campaigns.id"]),
        sa.ForeignKeyConstraint(["automation_id"], ["recall_automations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_logs_clinic_id", "recall_logs", ["clinic_id"])
    op.create_index("ix_recall_logs_patient_id", "recall_logs", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_recall_logs_patient_id", "recall_logs")
    op.drop_index("ix_recall_logs_clinic_id", "recall_logs")
    op.drop_table("recall_logs")
    op.drop_index("ix_patient_communication_preferences_patient_id", "patient_communication_preferences")
    op.drop_table("patient_communication_preferences")
    op.drop_index("ix_notification_channel_configs_clinic_id", "notification_channel_configs")
    op.drop_table("notification_channel_configs")
    op.drop_index("ix_recall_automations_clinic_id", "recall_automations")
    op.drop_table("recall_automations")
    op.drop_index("ix_recall_campaigns_clinic_id", "recall_campaigns")
    op.drop_table("recall_campaigns")
    op.drop_index("ix_recall_templates_clinic_id", "recall_templates")
    op.drop_table("recall_templates")
    op.drop_index("ix_recall_segments_clinic_id", "recall_segments")
    op.drop_table("recall_segments")
