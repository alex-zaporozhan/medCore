"""Stream 1e + Phase 3+: embed audit, RAG KB per org, vertical/import/export audit, embed RBAC permissions.

Revision ID: 20260424_stream_1e_phase3_plus_tables
Revises: 20260423_phase1a_founder_totp_org_ent_rls
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260424_stream_1e_phase3_plus_tables"
down_revision: Union[str, Sequence[str], None] = "20260423_phase1a_founder_totp_org_ent_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_embed_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("embed_api_key_id", sa.Uuid(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["embed_api_key_id"], ["organization_embed_api_keys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_embed_audit_log_org_created",
        "organization_embed_audit_log",
        ["organization_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "organization_rag_kb_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_org_rag_kb_documents_organization_id",
        "organization_rag_kb_documents",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "organization_industry_profile_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("old_profile", sa.String(length=64), nullable=False),
        sa.Column("new_profile", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_org_industry_audit_org_created",
        "organization_industry_profile_audit",
        ["organization_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "crm_import_job_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["crm_import_staging_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_import_job_audit_job_created",
        "crm_import_job_audit",
        ["job_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "organization_data_export_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("export_kind", sa.String(length=64), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_org_data_export_requests_org_created",
        "organization_data_export_requests",
        ["organization_id", "created_at"],
        unique=False,
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'view_embed_settings', 'Просмотр настроек встраивания (ключи по префиксу, URL webhook)'),
            (gen_random_uuid(), 'manage_embed_settings', 'Выпуск и отзыв embed API keys, ротация webhook secret')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'view_embed_settings'
            WHERE r.code IN ('owner', 'manager', 'admin')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'manage_embed_settings'
            WHERE r.code = 'owner'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
              AND p.code IN ('view_embed_settings', 'manage_embed_settings')
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN ('view_embed_settings', 'manage_embed_settings')"
        )
    )

    op.drop_index("ix_org_data_export_requests_org_created", table_name="organization_data_export_requests")
    op.drop_table("organization_data_export_requests")
    op.drop_index("ix_crm_import_job_audit_job_created", table_name="crm_import_job_audit")
    op.drop_table("crm_import_job_audit")
    op.drop_index("ix_org_industry_audit_org_created", table_name="organization_industry_profile_audit")
    op.drop_table("organization_industry_profile_audit")
    op.drop_index("ix_org_rag_kb_documents_organization_id", table_name="organization_rag_kb_documents")
    op.drop_table("organization_rag_kb_documents")
    op.drop_index("ix_organization_embed_audit_log_org_created", table_name="organization_embed_audit_log")
    op.drop_table("organization_embed_audit_log")
