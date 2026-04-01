"""Staff announcements publish policy: audit log.

Revision ID: p3q4r5s6t7u8
Revises: j2k3l4m5n6o7
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "j2k3l4m5n6o7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_announcement_publish_policy_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_staff_announce_policy_audit_clinic_created",
        "staff_announcement_publish_policy_audits",
        ["clinic_id", "created_at"],
    )
    op.create_index(
        "ix_staff_announcement_publish_policy_audits_actor_admin_id",
        "staff_announcement_publish_policy_audits",
        ["actor_admin_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_announcement_publish_policy_audits_actor_admin_id",
        table_name="staff_announcement_publish_policy_audits",
    )
    op.drop_index(
        "ix_staff_announce_policy_audit_clinic_created",
        table_name="staff_announcement_publish_policy_audits",
    )
    op.drop_table("staff_announcement_publish_policy_audits")

