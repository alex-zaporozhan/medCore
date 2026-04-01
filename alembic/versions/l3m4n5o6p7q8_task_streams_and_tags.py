"""Task semantic streams (required context) + optional tags M:N.

Revision ID: l3m4n5o6p7q8
Revises: k9j8h7g6f5e4
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l3m4n5o6p7q8"
down_revision: Union[str, Sequence[str], None] = "k9j8h7g6f5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_streams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "theme",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "slug", name="uq_task_streams_clinic_slug"),
    )
    op.create_index("ix_task_streams_clinic_id", "task_streams", ["clinic_id"], unique=False)
    op.create_index("ix_task_streams_clinic_archived", "task_streams", ["clinic_id", "is_archived"], unique=False)

    op.execute(
        """
        INSERT INTO task_streams (id, clinic_id, name, slug, sort_order, is_archived, theme, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, 'Общее', 'general', 0, false, '{}'::jsonb, now(), now()
        FROM clinics c
        """
    )

    op.add_column("tasks", sa.Column("stream_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_stream_id_task_streams",
        "tasks",
        "task_streams",
        ["stream_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_tasks_clinic_stream", "tasks", ["clinic_id", "stream_id"], unique=False)

    op.execute(
        """
        UPDATE tasks t
        SET stream_id = s.id
        FROM task_streams s
        WHERE s.clinic_id = t.clinic_id AND s.slug = 'general'
        """
    )

    op.alter_column("tasks", "stream_id", nullable=False)

    op.create_table(
        "task_tag_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "name", name="uq_task_tag_definitions_clinic_name"),
    )
    op.create_index("ix_task_tag_definitions_clinic_id", "task_tag_definitions", ["clinic_id"], unique=False)

    op.create_table(
        "task_task_tags",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["task_tag_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )
    op.create_index("ix_task_task_tags_tag_id", "task_task_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_task_tags_tag_id", table_name="task_task_tags")
    op.drop_table("task_task_tags")
    op.drop_index("ix_task_tag_definitions_clinic_id", table_name="task_tag_definitions")
    op.drop_table("task_tag_definitions")
    op.drop_index("ix_tasks_clinic_stream", table_name="tasks")
    op.drop_constraint("fk_tasks_stream_id_task_streams", "tasks", type_="foreignkey")
    op.drop_column("tasks", "stream_id")
    op.drop_index("ix_task_streams_clinic_archived", table_name="task_streams")
    op.drop_index("ix_task_streams_clinic_id", table_name="task_streams")
    op.drop_table("task_streams")
