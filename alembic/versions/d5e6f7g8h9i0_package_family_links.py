"""Add package_family_links table for FamilyLink (B6.1).

Revision ID: d5e6f7g8h9i0
Revises: a1b2c3d4e5f6_form_link_tokens
Create Date: 2026-03-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7g8h9i0_package_family_links"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6_form_link_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "package_family_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "customer_subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_subscription_id"],
            ["customer_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_subscription_id",
            "patient_id",
            name="uq_package_family_link_sub_patient",
        ),
    )
    op.create_index(
        "ix_package_family_links_customer_subscription_id",
        "package_family_links",
        ["customer_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_package_family_links_patient_id",
        "package_family_links",
        ["patient_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_package_family_links_patient_id",
        table_name="package_family_links",
    )
    op.drop_index(
        "ix_package_family_links_customer_subscription_id",
        table_name="package_family_links",
    )
    op.drop_table("package_family_links")
