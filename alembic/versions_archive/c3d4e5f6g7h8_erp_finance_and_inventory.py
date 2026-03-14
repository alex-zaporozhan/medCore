"""Add ERP finance and inventory tables (cashboxes, financial_transactions, payroll, inventory) and extend bookings for ERP flags.

Revision ID: c3d4e5f6g7h8_erp_finance_inventory
Revises: expand_alembic_ver_64
Create Date: 2026-03-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d4e5f6g7h8_erp_finance_inventory"
down_revision: Union[str, Sequence[str], None] = "expand_alembic_ver_64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with ERP finance and inventory tables."""
    op.create_table(
        "cashboxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
        "idx_cashboxes_clinic_id",
        "cashboxes",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_products_clinic_id",
        "products",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_products_clinic_sku",
        "products",
        ["clinic_id", "sku"],
        unique=False,
    )

    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_warehouses_clinic_id",
        "warehouses",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "payroll_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column(
            "fixed_per_shift",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "percent_from_services",
            sa.Numeric(5, 4),
            nullable=False,
            server_default="0.0000",
        ),
        sa.Column(
            "percent_from_products",
            sa.Numeric(5, 4),
            nullable=False,
            server_default="0.0000",
        ),
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
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_payroll_policies_clinic",
        "payroll_policies",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_payroll_policies_clinic_doctor_role",
        "payroll_policies",
        ["clinic_id", "doctor_id", "role"],
        unique=False,
    )

    op.create_table(
        "financial_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cashbox_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column(
            "happened_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(["cashbox_id"], ["cashboxes.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_fin_tx_clinic_happened_at",
        "financial_transactions",
        ["clinic_id", "happened_at"],
        unique=False,
    )
    op.create_index(
        "idx_fin_tx_clinic_cashbox",
        "financial_transactions",
        ["clinic_id", "cashbox_id"],
        unique=False,
    )

    op.create_table(
        "salary_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_salary_tx_clinic_doctor_period",
        "salary_transactions",
        ["clinic_id", "doctor_id", "period_start", "period_end"],
        unique=False,
    )

    op.create_table(
        "service_consumables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_per_service", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_service_consumables_clinic_service",
        "service_consumables",
        ["clinic_id", "service_id"],
        unique=False,
    )
    op.create_index(
        "idx_service_consumables_clinic_product",
        "service_consumables",
        ["clinic_id", "product_id"],
        unique=False,
    )

    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column(
            "happened_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_inventory_tx_clinic_happened_at",
        "inventory_transactions",
        ["clinic_id", "happened_at"],
        unique=False,
    )
    op.create_index(
        "idx_inventory_tx_clinic_product_warehouse",
        "inventory_transactions",
        ["clinic_id", "product_id", "warehouse_id"],
        unique=False,
    )

    op.add_column(
        "bookings",
        sa.Column(
            "erp_processed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "bookings",
        sa.Column("erp_error_code", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Downgrade ERP finance and inventory schema."""
    op.drop_column("bookings", "erp_error_code")
    op.drop_column("bookings", "erp_processed")

    op.drop_index(
        "idx_inventory_tx_clinic_product_warehouse",
        table_name="inventory_transactions",
    )
    op.drop_index(
        "idx_inventory_tx_clinic_happened_at",
        table_name="inventory_transactions",
    )
    op.drop_table("inventory_transactions")

    op.drop_index(
        "idx_service_consumables_clinic_product",
        table_name="service_consumables",
    )
    op.drop_index(
        "idx_service_consumables_clinic_service",
        table_name="service_consumables",
    )
    op.drop_table("service_consumables")

    op.drop_index(
        "idx_salary_tx_clinic_doctor_period",
        table_name="salary_transactions",
    )
    op.drop_table("salary_transactions")

    op.drop_index(
        "idx_fin_tx_clinic_cashbox",
        table_name="financial_transactions",
    )
    op.drop_index(
        "idx_fin_tx_clinic_happened_at",
        table_name="financial_transactions",
    )
    op.drop_table("financial_transactions")

    op.drop_index(
        "idx_payroll_policies_clinic_doctor_role",
        table_name="payroll_policies",
    )
    op.drop_index(
        "idx_payroll_policies_clinic",
        table_name="payroll_policies",
    )
    op.drop_table("payroll_policies")

    op.drop_index(
        "idx_warehouses_clinic_id",
        table_name="warehouses",
    )
    op.drop_table("warehouses")

    op.drop_index(
        "idx_products_clinic_sku",
        table_name="products",
    )
    op.drop_index(
        "idx_products_clinic_id",
        table_name="products",
    )
    op.drop_table("products")

    op.drop_index(
        "idx_cashboxes_clinic_id",
        table_name="cashboxes",
    )
    op.drop_table("cashboxes")

