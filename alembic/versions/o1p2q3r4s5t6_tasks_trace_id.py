"""tasks: optional trace_id for observability (OBS_CHAINS_023 B4)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "o1p2q3r4s5t6"
down_revision = "n0o1p2q3r4s5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("trace_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_tasks_trace_id", "tasks", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_trace_id", table_name="tasks")
    op.drop_column("tasks", "trace_id")
