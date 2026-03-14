"""Seed initial UserRole records for existing admins.

Revision ID: rbac_tasks_0002_seed_user_roles_from_admins
Revises: rbac_tasks_0001_init
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rbac_tasks_0002_seed_user_roles_from_admins"
down_revision: Union[str, Sequence[str], None] = "rbac_tasks_0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Map existing admins to default roles via UserRole."""
    conn = op.get_bind()

    # Load global base roles (clinic_id IS NULL)
    roles_result = conn.execute(sa.text("SELECT id, code FROM roles WHERE clinic_id IS NULL"))
    role_by_code = {row.code: row.id for row in roles_result}

    # Decide default role for existing admins.
    # For Phase 1: map all existing admins to `manager` if exists, otherwise to `owner`,
    # as они обычно владельцы/управляющие инсталляции.
    default_role_id = role_by_code.get("manager") or role_by_code.get("owner")
    if not default_role_id:
        # Nothing to do if roles were not seeded for some reason.
        return

    # Insert UserRole per admin/clinic pair if missing.
    admins_result = conn.execute(
        sa.text(
            "SELECT id AS admin_id, clinic_id "
            "FROM admins "
            "WHERE deleted_at IS NULL"
        )
    )

    for row in admins_result:
        conn.execute(
            sa.text(
                "INSERT INTO user_roles (id, user_id, role_id, clinic_id, created_at) "
                "VALUES (gen_random_uuid(), :user_id, :role_id, :clinic_id, now()) "
                "ON CONFLICT (user_id, role_id, clinic_id) DO NOTHING"
            ),
            {
                "user_id": row.admin_id,
                "role_id": default_role_id,
                "clinic_id": row.clinic_id,
            },
        )


def downgrade() -> None:
    """Remove UserRole records created for existing admins."""
    conn = op.get_bind()

    roles_result = conn.execute(sa.text("SELECT id, code FROM roles WHERE clinic_id IS NULL"))
    role_by_code = {row.code: row.id for row in roles_result}
    default_role_id = role_by_code.get("manager") or role_by_code.get("owner")

    if not default_role_id:
        return

    conn.execute(
        sa.text(
            "DELETE FROM user_roles WHERE role_id = :role_id"
        ),
        {"role_id": default_role_id},
    )

