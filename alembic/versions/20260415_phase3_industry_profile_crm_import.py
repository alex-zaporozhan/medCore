"""Phase 3+: organizations.industry_profile, CRM import staging, catalog import.crm_v1.

Revision ID: 20260415_phase3_industry_profile_crm_import
Revises: 20260414_phase2_domain_outbox
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260415_phase3_industry_profile_crm_import"
down_revision: Union[str, Sequence[str], None] = "20260414_phase2_domain_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "industry_profile",
            sa.String(length=64),
            server_default="industry_dental",
            nullable=False,
        ),
    )

    op.create_table(
        "crm_import_staging_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=True),
        sa.Column("source_profile", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_import_staging_jobs_organization_id",
        "crm_import_staging_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_crm_import_staging_jobs_clinic_id",
        "crm_import_staging_jobs",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ux_crm_import_staging_jobs_org_idempotency",
        "crm_import_staging_jobs",
        ["organization_id", "idempotency_key"],
        unique=True,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_options (id, entitlement_key, display_name, description, list_price_rub, is_active, sort_order)
            VALUES
              ('a0000001-0000-4000-8000-000000000009'::uuid, 'import.crm_v1', 'Импорт из CRM v1', 'ADR-010: контакты/сделки, staging per org', 1990.00, true, 70)
            ON CONFLICT (entitlement_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM platform_catalog_options WHERE entitlement_key = 'import.crm_v1'
            """
        )
    )
    op.drop_index("ux_crm_import_staging_jobs_org_idempotency", table_name="crm_import_staging_jobs")
    op.drop_index("ix_crm_import_staging_jobs_clinic_id", table_name="crm_import_staging_jobs")
    op.drop_index("ix_crm_import_staging_jobs_organization_id", table_name="crm_import_staging_jobs")
    op.drop_table("crm_import_staging_jobs")
    op.drop_column("organizations", "industry_profile")
