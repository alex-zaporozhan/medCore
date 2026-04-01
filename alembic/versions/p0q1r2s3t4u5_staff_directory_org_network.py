"""Organizations + staff profession categories + network-scoped staff directory.

Revision ID: p0q1r2s3t4u5
Revises: m1n2o3p4q5r6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p0q1r2s3t4u5"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "clinics",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(op.f("ix_clinics_organization_id"), "clinics", ["organization_id"], unique=False)
    op.create_foreign_key(
        "fk_clinics_organization_id_organizations",
        "clinics",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "admins",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(op.f("ix_admins_organization_id"), "admins", ["organization_id"], unique=False)
    op.create_foreign_key(
        "fk_admins_organization_id_organizations",
        "admins",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        INSERT INTO organizations (id, name)
        SELECT gen_random_uuid(), 'Default organization'
        WHERE NOT EXISTS (SELECT 1 FROM organizations LIMIT 1)
        """
    )
    op.execute(
        """
        UPDATE clinics
        SET organization_id = (SELECT id FROM organizations ORDER BY created_at ASC LIMIT 1)
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE admins
        SET organization_id = (
            SELECT c.organization_id FROM clinics c WHERE c.id = admins.clinic_id LIMIT 1
        )
        WHERE organization_id IS NULL
        """
    )

    op.create_table(
        "staff_profession_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staff_profession_categories_clinic_id"),
        "staff_profession_categories",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_staff_profession_categories_clinic_active_name",
        "staff_profession_categories",
        ["clinic_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.add_column(
        "admins",
        sa.Column("profession_category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(op.f("ix_admins_profession_category_id"), "admins", ["profession_category_id"], unique=False)
    op.create_foreign_key(
        "fk_admins_profession_category_id_staff_profession_categories",
        "admins",
        "staff_profession_categories",
        ["profession_category_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        INSERT INTO permissions (id, code, description)
        VALUES (
            gen_random_uuid(),
            'manage_staff_directory',
            'Каталог персонала: категории профессий, учётные записи сотрудников клиники'
        )
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code = 'manage_staff_directory'
        WHERE r.code IN ('owner', 'manager', 'admin')
          AND (
            r.clinic_id IS NULL
            OR EXISTS (SELECT 1 FROM clinics c WHERE c.id = r.clinic_id)
          )
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'manage_staff_directory')
        """
    )
    op.execute("DELETE FROM permissions WHERE code = 'manage_staff_directory'")

    op.drop_constraint("fk_admins_profession_category_id_staff_profession_categories", "admins", type_="foreignkey")
    op.drop_index(op.f("ix_admins_profession_category_id"), table_name="admins")
    op.drop_column("admins", "profession_category_id")

    op.drop_index("ix_staff_profession_categories_clinic_active_name", table_name="staff_profession_categories")
    op.drop_index(op.f("ix_staff_profession_categories_clinic_id"), table_name="staff_profession_categories")
    op.drop_table("staff_profession_categories")

    op.drop_constraint("fk_admins_organization_id_organizations", "admins", type_="foreignkey")
    op.drop_index(op.f("ix_admins_organization_id"), table_name="admins")
    op.drop_column("admins", "organization_id")

    op.drop_constraint("fk_clinics_organization_id_organizations", "clinics", type_="foreignkey")
    op.drop_index(op.f("ix_clinics_organization_id"), table_name="clinics")
    op.drop_column("clinics", "organization_id")

    op.drop_table("organizations")
