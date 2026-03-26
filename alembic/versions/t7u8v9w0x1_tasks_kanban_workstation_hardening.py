"""Tasks: kanban workstation hardening fields and transitions audit.

Revision ID: t7u8v9w0x1
Revises: s6t7u8v9w0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t7u8v9w0x1"
down_revision: Union[str, Sequence[str], None] = "s6t7u8v9w0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("rank", sa.Integer(), nullable=False, server_default="1000"))
    op.add_column("tasks", sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("tasks", sa.Column("blocked_reason", sa.Text(), nullable=True))
    op.add_column(
        "tasks", sa.Column("checklist_done", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column("tasks", sa.Column("stage_entered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.add_column("tasks", sa.Column("updated_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_tasks_updated_by_admin_id_admins",
        "tasks",
        "admins",
        ["updated_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_tasks_clinic_status_rank", "tasks", ["clinic_id", "status", "rank"], unique=False)

    op.create_table(
        "task_status_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_task_status_transitions_task_created",
        "task_status_transitions",
        ["clinic_id", "task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_task_status_transitions_clinic_created",
        "task_status_transitions",
        ["clinic_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_task_status_transitions_clinic_created", table_name="task_status_transitions")
    op.drop_index("idx_task_status_transitions_task_created", table_name="task_status_transitions")
    op.drop_table("task_status_transitions")

    op.drop_index("idx_tasks_clinic_status_rank", table_name="tasks")
    op.drop_constraint("fk_tasks_updated_by_admin_id_admins", "tasks", type_="foreignkey")
    op.drop_column("tasks", "updated_by_admin_id")
    op.drop_column("tasks", "stage_entered_at")
    op.drop_column("tasks", "checklist_done")
    op.drop_column("tasks", "blocked_reason")
    op.drop_column("tasks", "blocked")
    op.drop_column("tasks", "rank")

