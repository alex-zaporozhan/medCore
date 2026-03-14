"""Add ai_tasks_enabled to clinic_ai_settings for AI Task Generator.

Revision ID: ai_tasks_enabled_0001
Revises: rbac_tasks_0002_seed_user_roles_from_admins
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ai_tasks_enabled_0001"
down_revision: Union[str, Sequence[str], None] = "rbac_tasks_0002_seed_user_roles_from_admins"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinic_ai_settings",
        sa.Column("ai_tasks_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("clinic_ai_settings", "ai_tasks_enabled")
