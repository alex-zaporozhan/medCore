"""Paperless PPR-2: form instance status, audit, required templates, link->submission.

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, Sequence[str], None] = "g3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "digital_form_templates",
        sa.Column(
            "required_for_visit_completion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "form_audit_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digital_form_submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["digital_form_submission_id"],
            ["digital_form_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_form_audit_submission_created",
        "form_audit_entries",
        ["digital_form_submission_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_form_audit_entries_digital_form_submission_id"),
        "form_audit_entries",
        ["digital_form_submission_id"],
        unique=False,
    )

    op.add_column(
        "digital_form_submissions",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="signed",
        ),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column("created_by", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "digital_form_submissions",
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )

    op.execute(
        """
        UPDATE digital_form_submissions
        SET signed_at = submitted_at,
            created_at = submitted_at,
            updated_at = submitted_at
        WHERE submitted_at IS NOT NULL
        """
    )

    op.alter_column(
        "digital_form_submissions",
        "submitted_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    op.create_index(
        "idx_digital_form_submissions_booking_status",
        "digital_form_submissions",
        ["booking_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_form_submissions_status"),
        "digital_form_submissions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_digital_form_submissions_expires_at"),
        "digital_form_submissions",
        ["expires_at"],
        unique=False,
    )

    op.add_column(
        "form_link_tokens",
        sa.Column("digital_form_submission_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_form_link_tokens_digital_form_submission_id",
        "form_link_tokens",
        "digital_form_submissions",
        ["digital_form_submission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_form_link_tokens_digital_form_submission_id"),
        "form_link_tokens",
        ["digital_form_submission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_form_link_tokens_digital_form_submission_id"),
        table_name="form_link_tokens",
    )
    op.drop_constraint(
        "fk_form_link_tokens_digital_form_submission_id",
        "form_link_tokens",
        type_="foreignkey",
    )
    op.drop_column("form_link_tokens", "digital_form_submission_id")

    op.drop_index(
        op.f("ix_digital_form_submissions_expires_at"),
        table_name="digital_form_submissions",
    )
    op.drop_index(
        op.f("ix_digital_form_submissions_status"),
        table_name="digital_form_submissions",
    )
    op.drop_index(
        "idx_digital_form_submissions_booking_status",
        table_name="digital_form_submissions",
    )

    op.alter_column(
        "digital_form_submissions",
        "submitted_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    op.drop_column("digital_form_submissions", "updated_by")
    op.drop_column("digital_form_submissions", "created_by")
    op.drop_column("digital_form_submissions", "updated_at")
    op.drop_column("digital_form_submissions", "created_at")
    op.drop_column("digital_form_submissions", "signed_at")
    op.drop_column("digital_form_submissions", "expires_at")
    op.drop_column("digital_form_submissions", "status")

    op.drop_index(
        op.f("ix_form_audit_entries_digital_form_submission_id"),
        table_name="form_audit_entries",
    )
    op.drop_index("idx_form_audit_submission_created", table_name="form_audit_entries")
    op.drop_table("form_audit_entries")

    op.drop_column("digital_form_templates", "required_for_visit_completion")
