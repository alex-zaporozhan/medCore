"""FamilyLink table and beneficiary columns for loyalty usage / ERP / wallet.

Revision ID: d3e4f5a6b7c8
Revises: c9d0e1f2a3b4
Create Date: 2026-03-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("primary_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("can_spend_from_owner_loyalty", sa.Boolean(), nullable=False),
        sa.Column("can_view_owner_history", sa.Boolean(), nullable=False),
        sa.Column("spending_limit_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("spending_limit_periodic", sa.Numeric(12, 2), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["primary_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["related_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "primary_patient_id",
            "related_patient_id",
            name="uq_family_links_clinic_primary_related",
        ),
    )
    op.create_index(
        "ix_family_links_clinic_id", "family_links", ["clinic_id"], unique=False
    )
    op.create_index(
        "ix_family_links_primary_patient_id",
        "family_links",
        ["primary_patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_family_links_related_patient_id",
        "family_links",
        ["related_patient_id"],
        unique=False,
    )
    op.create_index(
        "idx_family_links_clinic_primary",
        "family_links",
        ["clinic_id", "primary_patient_id"],
        unique=False,
    )
    op.create_index(
        "idx_family_links_clinic_related",
        "family_links",
        ["clinic_id", "related_patient_id"],
        unique=False,
    )

    op.add_column(
        "subscription_usages",
        sa.Column("beneficiary_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "subscription_usages",
        sa.Column("family_link_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_subscription_usages_beneficiary_patient_id_patients",
        "subscription_usages",
        "patients",
        ["beneficiary_patient_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_subscription_usages_family_link_id_family_links",
        "subscription_usages",
        "family_links",
        ["family_link_id"],
        ["id"],
    )
    op.create_index(
        "ix_subscription_usages_beneficiary_patient_id",
        "subscription_usages",
        ["beneficiary_patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_usages_family_link_id",
        "subscription_usages",
        ["family_link_id"],
        unique=False,
    )

    op.add_column(
        "wallet_transactions",
        sa.Column("beneficiary_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "wallet_transactions",
        sa.Column("family_link_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_wallet_transactions_beneficiary_patient_id_patients",
        "wallet_transactions",
        "patients",
        ["beneficiary_patient_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_wallet_transactions_family_link_id_family_links",
        "wallet_transactions",
        "family_links",
        ["family_link_id"],
        ["id"],
    )
    op.create_index(
        "ix_wallet_transactions_beneficiary_patient_id",
        "wallet_transactions",
        ["beneficiary_patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_family_link_id",
        "wallet_transactions",
        ["family_link_id"],
        unique=False,
    )

    op.add_column(
        "erp_loyalty_obligation_movements",
        sa.Column("beneficiary_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "erp_loyalty_obligation_movements",
        sa.Column("family_link_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_erp_loy_mov_beneficiary_patient_id_patients",
        "erp_loyalty_obligation_movements",
        "patients",
        ["beneficiary_patient_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_erp_loy_mov_family_link_id_family_links",
        "erp_loyalty_obligation_movements",
        "family_links",
        ["family_link_id"],
        ["id"],
    )
    op.create_index(
        "ix_erp_loyalty_obligation_movements_beneficiary_patient_id",
        "erp_loyalty_obligation_movements",
        ["beneficiary_patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_erp_loyalty_obligation_movements_family_link_id",
        "erp_loyalty_obligation_movements",
        ["family_link_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_erp_loyalty_obligation_movements_family_link_id",
        table_name="erp_loyalty_obligation_movements",
    )
    op.drop_index(
        "ix_erp_loyalty_obligation_movements_beneficiary_patient_id",
        table_name="erp_loyalty_obligation_movements",
    )
    op.drop_constraint(
        "fk_erp_loy_mov_family_link_id_family_links",
        "erp_loyalty_obligation_movements",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_erp_loy_mov_beneficiary_patient_id_patients",
        "erp_loyalty_obligation_movements",
        type_="foreignkey",
    )
    op.drop_column("erp_loyalty_obligation_movements", "family_link_id")
    op.drop_column("erp_loyalty_obligation_movements", "beneficiary_patient_id")

    op.drop_index("ix_wallet_transactions_family_link_id", table_name="wallet_transactions")
    op.drop_index(
        "ix_wallet_transactions_beneficiary_patient_id", table_name="wallet_transactions"
    )
    op.drop_constraint(
        "fk_wallet_transactions_family_link_id_family_links",
        "wallet_transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_wallet_transactions_beneficiary_patient_id_patients",
        "wallet_transactions",
        type_="foreignkey",
    )
    op.drop_column("wallet_transactions", "family_link_id")
    op.drop_column("wallet_transactions", "beneficiary_patient_id")

    op.drop_index("ix_subscription_usages_family_link_id", table_name="subscription_usages")
    op.drop_index(
        "ix_subscription_usages_beneficiary_patient_id", table_name="subscription_usages"
    )
    op.drop_constraint(
        "fk_subscription_usages_family_link_id_family_links",
        "subscription_usages",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_subscription_usages_beneficiary_patient_id_patients",
        "subscription_usages",
        type_="foreignkey",
    )
    op.drop_column("subscription_usages", "family_link_id")
    op.drop_column("subscription_usages", "beneficiary_patient_id")

    op.drop_index("idx_family_links_clinic_related", table_name="family_links")
    op.drop_index("idx_family_links_clinic_primary", table_name="family_links")
    op.drop_index("ix_family_links_related_patient_id", table_name="family_links")
    op.drop_index("ix_family_links_primary_patient_id", table_name="family_links")
    op.drop_index("ix_family_links_clinic_id", table_name="family_links")
    op.drop_table("family_links")
