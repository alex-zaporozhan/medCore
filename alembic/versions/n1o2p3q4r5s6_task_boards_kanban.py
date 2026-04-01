"""Task boards + columns (Kanban layout variant A: columns map to task.status).

Revision ID: n1o2p3q4r5s6
Revises: a1b2c3d4e5f7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_boards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="clinic_wide"),
        sa.Column("owner_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_task_boards_clinic_id", "task_boards", ["clinic_id"])
    op.create_index("ix_task_boards_owner_admin_id", "task_boards", ["owner_admin_id"])

    op.create_table(
        "task_board_columns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("board_id", sa.Uuid(), sa.ForeignKey("task_boards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mapped_status", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("board_id", "mapped_status", name="uq_task_board_column_status"),
    )
    op.create_index("ix_task_board_columns_board_id", "task_board_columns", ["board_id"])


def downgrade() -> None:
    op.drop_index("ix_task_board_columns_board_id", table_name="task_board_columns")
    op.drop_table("task_board_columns")
    op.drop_index("ix_task_boards_owner_admin_id", table_name="task_boards")
    op.drop_index("ix_task_boards_clinic_id", table_name="task_boards")
    op.drop_table("task_boards")
