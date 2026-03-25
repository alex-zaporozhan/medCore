"""Omni messages: sender_admin_id FK for operator audit.

Revision ID: q4r5s6t7u8
Revises: p3q4r5s6t7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "p3q4r5s6t7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "omni_messages",
        sa.Column(
            "sender_admin_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_omni_messages_sender_admin_id_admins",
        "omni_messages",
        "admins",
        ["sender_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_omni_messages_sender_admin_id",
        "omni_messages",
        ["sender_admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_omni_messages_sender_admin_id", table_name="omni_messages")
    op.drop_constraint(
        "fk_omni_messages_sender_admin_id_admins",
        "omni_messages",
        type_="foreignkey",
    )
    op.drop_column("omni_messages", "sender_admin_id")
