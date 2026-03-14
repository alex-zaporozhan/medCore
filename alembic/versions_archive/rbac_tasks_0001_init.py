"""Add RBAC (roles, permissions) and Tasks tables.

Revision ID: rbac_tasks_0001_init
Revises: c3d4e5f6g7h8_erp_finance_inventory
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "rbac_tasks_0001_init"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8_erp_finance_inventory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create RBAC and tasks tables and seed base data."""
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_roles_clinic_code",
        "roles",
        ["clinic_id", "code"],
        unique=True,
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="ux_permissions_code"),
    )
    op.create_index(
        "ix_permissions_code",
        "permissions",
        ["code"],
        unique=True,
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_role_permissions_role_perm",
        "role_permissions",
        ["role_id", "permission_id"],
        unique=True,
    )

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_user_roles_user_role_clinic",
        "user_roles",
        ["user_id", "role_id", "clinic_id"],
        unique=True,
    )
    op.create_index(
        "idx_user_roles_clinic_id",
        "user_roles",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role_assignee", sa.String(length=64), nullable=True),
        sa.Column("due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inventory_product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("source_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assignee_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["creator_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["inventory_product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["lead_cards.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tasks_clinic_status",
        "tasks",
        ["clinic_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_tasks_clinic_assignee",
        "tasks",
        ["clinic_id", "assignee_id"],
        unique=False,
    )
    op.create_index(
        "idx_tasks_clinic_role_assignee",
        "tasks",
        ["clinic_id", "role_assignee"],
        unique=False,
    )
    op.create_index(
        "idx_tasks_clinic_due_at",
        "tasks",
        ["clinic_id", "due_at"],
        unique=False,
    )

    op.create_table(
        "task_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed base roles and permissions (Owner, Manager, Admin, Doctor).
    conn = op.get_bind()

    permissions = [
        ("view_dashboard", "Просмотр дашборда"),
        ("view_reports", "Просмотр отчётов"),
        ("view_finance", "Просмотр финансовых данных"),
        ("manage_finance", "Управление финансовыми настройками и операциями"),
        ("view_payroll", "Просмотр данных по зарплате"),
        ("manage_payroll", "Управление зарплатными политиками и выплатами"),
        ("view_inventory", "Просмотр склада и остатков"),
        ("manage_inventory", "Управление складом и остатками"),
        ("view_crm", "Просмотр CRM и лидов"),
        ("manage_crm", "Управление стадиями и данными CRM"),
        ("view_tasks", "Просмотр задач"),
        ("manage_tasks", "Создание и изменение задач"),
        ("assign_tasks", "Назначение задач другим пользователям"),
        ("view_loyalty", "Просмотр модулей лояльности"),
        ("manage_loyalty", "Управление программами лояльности"),
        ("view_forms", "Просмотр форм и подписей"),
        ("manage_forms", "Управление шаблонами форм"),
        ("export_forms", "Экспорт форм и подписей пациента"),
        ("view_marketing_analytics", "Просмотр маркетинговой аналитики"),
        ("manage_marketing_campaigns", "Управление маркетинговыми кампаниями"),
        ("view_ai_settings", "Просмотр AI-настроек"),
        ("manage_ai_settings", "Управление AI-настройками"),
    ]

    permission_rows = [
        {
            "id": sa.text("gen_random_uuid()"),
            "code": code,
            "description": desc,
        }
        for code, desc in permissions
    ]

    # Insert permissions
    for row in permission_rows:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description) "
                "VALUES (:id, :code, :description) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": row["id"], "code": row["code"], "description": row["description"]},
        )

    # Map permission codes to ids for role seeding
    result = conn.execute(sa.text("SELECT id, code FROM permissions"))
    perm_by_code = {row.code: row.id for row in result}

    role_codes = [
        "owner",
        "manager",
        "admin",
        "doctor",
    ]

    for code in role_codes:
        conn.execute(
            sa.text(
                "INSERT INTO roles (id, clinic_id, code, name, description) "
                "VALUES (gen_random_uuid(), NULL, :code, :name, :description) "
                "ON CONFLICT (clinic_id, code) DO NOTHING"
            ),
            {
                "code": code,
                "name": code.capitalize(),
                "description": f"Base role {code}",
            },
        )

    # Reload roles with ids
    roles_result = conn.execute(sa.text("SELECT id, code FROM roles WHERE clinic_id IS NULL"))
    role_by_code = {row.code: row.id for row in roles_result}

    def link(role: str, perm_codes: list[str]) -> None:
        role_id = role_by_code.get(role)
        if not role_id:
            return
        for p_code in perm_codes:
            perm_id = perm_by_code.get(p_code)
            if not perm_id:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id, created_at) "
                    "VALUES (gen_random_uuid(), :role_id, :perm_id, now()) "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            )

    # Owner: all permissions
    link("owner", list(perm_by_code.keys()))

    # Manager: все, кроме критичных глобальных/финансовых настроек AI/ERP
    manager_perms = [
        "view_dashboard",
        "view_reports",
        "view_finance",
        "view_payroll",
        "view_inventory",
        "view_crm",
        "view_tasks",
        "manage_tasks",
        "assign_tasks",
        "view_loyalty",
        "manage_loyalty",
        "view_forms",
        "manage_forms",
        "export_forms",
        "view_marketing_analytics",
        "manage_marketing_campaigns",
        "view_ai_settings",
    ]
    link("manager", manager_perms)

    # Admin: без финансов и глобальных настроек
    admin_perms = [
        "view_dashboard",
        "view_crm",
        "manage_crm",
        "view_tasks",
        "manage_tasks",
        "assign_tasks",
        "view_inventory",
        "view_loyalty",
        "view_forms",
        "view_marketing_analytics",
    ]
    link("admin", admin_perms)

    # Doctor: только свои данные и задачи (минимальный набор)
    doctor_perms = [
        "view_tasks",
    ]
    link("doctor", doctor_perms)


def downgrade() -> None:
    """Drop Tasks and RBAC tables."""
    op.drop_table("task_comments")
    op.drop_index("idx_tasks_clinic_due_at", table_name="tasks")
    op.drop_index("idx_tasks_clinic_role_assignee", table_name="tasks")
    op.drop_index("idx_tasks_clinic_assignee", table_name="tasks")
    op.drop_index("idx_tasks_clinic_status", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("idx_user_roles_clinic_id", table_name="user_roles")
    op.drop_index("ux_user_roles_user_role_clinic", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ux_role_permissions_role_perm", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("idx_roles_clinic_code", table_name="roles")
    op.drop_table("roles")

