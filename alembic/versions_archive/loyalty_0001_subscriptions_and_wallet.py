"""Add loyalty subscriptions and wallet tables.

Revision ID: loyalty_0001_subscriptions_wallet
Revises: c3d4e5f6g7h8_erp_finance_inventory
Create Date: 2026-03-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "loyalty_0001_subscriptions_wallet"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8_erp_finance_inventory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create loyalty subscription and wallet tables."""
    op.create_table(
        "subscription_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "services_included",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("total_visits", sa.Integer(), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=True),
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
        "idx_subscription_packages_clinic_id",
        "subscription_packages",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_subscription_packages_clinic_code",
        "subscription_packages",
        ["clinic_id", "code"],
        unique=False,
    )

    op.create_table(
        "customer_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "subscription_package_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("remaining_visits", sa.Integer(), nullable=True),
        sa.Column("remaining_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(
            ["subscription_package_id"],
            ["subscription_packages.id"],
        ),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_customer_subscriptions_clinic_id",
        "customer_subscriptions",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_customer_subscriptions_patient_id",
        "customer_subscriptions",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        "idx_customer_subscriptions_status",
        "customer_subscriptions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_customer_subscriptions_expires_at",
        "customer_subscriptions",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "subscription_usages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "customer_subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_visits", sa.Integer(), nullable=True),
        sa.Column("used_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(
            ["customer_subscription_id"],
            ["customer_subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_subscription_usages_clinic_id",
        "subscription_usages",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "idx_subscription_usages_subscription_booking",
        "subscription_usages",
        ["customer_subscription_id", "booking_id"],
        unique=False,
    )

    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "balance",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "currency",
            sa.String(length=16),
            nullable=False,
            server_default="POINTS",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "patient_id",
            name="ux_wallets_clinic_patient",
        ),
    )
    op.create_index(
        "idx_wallets_clinic_id",
        "wallets",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "happened_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["customer_subscriptions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_wallet_tx_clinic_happened_at",
        "wallet_transactions",
        ["clinic_id", "happened_at"],
        unique=False,
    )
    op.create_index(
        "idx_wallet_tx_clinic_wallet",
        "wallet_transactions",
        ["clinic_id", "wallet_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop loyalty subscription and wallet tables."""
    op.drop_index(
        "idx_wallet_tx_clinic_wallet",
        table_name="wallet_transactions",
    )
    op.drop_index(
        "idx_wallet_tx_clinic_happened_at",
        table_name="wallet_transactions",
    )
    op.drop_table("wallet_transactions")

    op.drop_index(
        "idx_wallets_clinic_id",
        table_name="wallets",
    )
    op.drop_table("wallets")

    op.drop_index(
        "idx_subscription_usages_subscription_booking",
        table_name="subscription_usages",
    )
    op.drop_index(
        "idx_subscription_usages_clinic_id",
        table_name="subscription_usages",
    )
    op.drop_table("subscription_usages")

    op.drop_index(
        "idx_customer_subscriptions_expires_at",
        table_name="customer_subscriptions",
    )
    op.drop_index(
        "idx_customer_subscriptions_status",
        table_name="customer_subscriptions",
    )
    op.drop_index(
        "idx_customer_subscriptions_patient_id",
        table_name="customer_subscriptions",
    )
    op.drop_index(
        "idx_customer_subscriptions_clinic_id",
        table_name="customer_subscriptions",
    )
    op.drop_table("customer_subscriptions")

    op.drop_index(
        "idx_subscription_packages_clinic_code",
        table_name="subscription_packages",
    )
    op.drop_index(
        "idx_subscription_packages_clinic_id",
        table_name="subscription_packages",
    )
    op.drop_table("subscription_packages")

