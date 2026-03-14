"""Marketing attribution schema: traffic sources, campaigns, visit_attributions and links to finance.

Revision ID: marketing_attr_0001_visit_attributions
Revises: crm_leads_0002_marketing_fields
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "marketing_attr_0001_visit_attributions"
down_revision: Union[str, Sequence[str], None] = "crm_leads_0002_marketing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with marketing attribution tables and columns."""
    op.create_table(
        "traffic_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("budget_planned", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_actual", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "start_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "end_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
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
        "idx_traffic_sources_clinic_id",
        "traffic_sources",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_traffic_sources_clinic_code",
        "traffic_sources",
        ["clinic_id", "code"],
        unique=False,
    )

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("traffic_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("budget_planned", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_actual", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "start_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "end_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
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
        sa.ForeignKeyConstraint(["traffic_source_id"], ["traffic_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_campaigns_clinic_id",
        "campaigns",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_campaigns_clinic_source",
        "campaigns",
        ["clinic_id", "traffic_source_id"],
        unique=False,
    )
    op.create_index(
        "idx_campaigns_clinic_code",
        "campaigns",
        ["clinic_id", "code"],
        unique=False,
    )

    op.create_table(
        "visit_attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("traffic_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("landing_page", sa.String(length=512), nullable=True),
        sa.Column("anchor", sa.String(length=128), nullable=True),
        sa.Column("utm_source", sa.String(length=128), nullable=True),
        sa.Column("utm_medium", sa.String(length=128), nullable=True),
        sa.Column("utm_campaign", sa.String(length=128), nullable=True),
        sa.Column("utm_content", sa.String(length=128), nullable=True),
        sa.Column("utm_term", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["traffic_source_id"], ["traffic_sources.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_visit_attr_clinic_created",
        "visit_attributions",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_visit_attr_clinic_session",
        "visit_attributions",
        ["clinic_id", "session_id"],
        unique=False,
    )

    op.add_column(
        "financial_transactions",
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "financial_transactions",
        sa.Column("visit_attribution_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_fin_tx_clinic_visit_attr",
        "financial_transactions",
        ["clinic_id", "visit_attribution_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade marketing attribution schema."""
    op.drop_index(
        "idx_fin_tx_clinic_visit_attr",
        table_name="financial_transactions",
    )
    op.drop_column("financial_transactions", "visit_attribution_id")
    op.drop_column("financial_transactions", "lead_id")

    op.drop_index(
        "idx_visit_attr_clinic_session",
        table_name="visit_attributions",
    )
    op.drop_index(
        "idx_visit_attr_clinic_created",
        table_name="visit_attributions",
    )
    op.drop_table("visit_attributions")

    op.drop_index(
        "idx_campaigns_clinic_code",
        table_name="campaigns",
    )
    op.drop_index(
        "idx_campaigns_clinic_source",
        table_name="campaigns",
    )
    op.drop_index(
        "idx_campaigns_clinic_id",
        table_name="campaigns",
    )
    op.drop_table("campaigns")

    op.drop_index(
        "idx_traffic_sources_clinic_code",
        table_name="traffic_sources",
    )
    op.drop_index(
        "idx_traffic_sources_clinic_id",
        table_name="traffic_sources",
    )
    op.drop_table("traffic_sources")
