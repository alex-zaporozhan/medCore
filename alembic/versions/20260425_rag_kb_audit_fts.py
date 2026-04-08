"""RAG KB §24.3: audit log + generated tsvector (FTS) for optional retrieval mode.

Revision ID: 20260425_rag_kb_audit_fts
Revises: 20260424_stream_1e_phase3_plus_tables
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260425_rag_kb_audit_fts"
down_revision: Union[str, Sequence[str], None] = "20260424_stream_1e_phase3_plus_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_rag_kb_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        "ix_org_rag_kb_audit_org_created",
        "organization_rag_kb_audit_log",
        ["organization_id", "created_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE organization_rag_kb_documents
            ADD COLUMN search_tsv tsvector
            GENERATED ALWAYS AS (
                to_tsvector(
                    'simple',
                    coalesce(title, '') || ' ' || coalesce(body, '')
                )
            ) STORED
            """
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_org_rag_kb_documents_search_tsv "
            "ON organization_rag_kb_documents USING GIN (search_tsv)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_org_rag_kb_documents_search_tsv"))
    op.drop_column("organization_rag_kb_documents", "search_tsv")
    op.drop_index("ix_org_rag_kb_audit_org_created", table_name="organization_rag_kb_audit_log")
    op.drop_table("organization_rag_kb_audit_log")
