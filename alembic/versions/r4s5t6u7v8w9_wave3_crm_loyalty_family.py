"""Wave3: lead_secondary_bookings, loyalty_groups, family_links.group_id, crm lead estimated audit.

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loyalty_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loyalty_groups_clinic", "loyalty_groups", ["clinic_id"], unique=False)

    op.add_column(
        "family_links",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_family_links_loyalty_group",
        "family_links",
        "loyalty_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_family_links_group_id", "family_links", ["group_id"], unique=False)

    op.create_table(
        "lead_secondary_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["lead_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id", "booking_id", name="uq_lead_secondary_booking"),
    )
    op.create_index(
        "ix_lead_secondary_bookings_clinic_booking",
        "lead_secondary_bookings",
        ["clinic_id", "booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_lead_secondary_bookings_lead",
        "lead_secondary_bookings",
        ["lead_id"],
        unique=False,
    )

    op.create_table(
        "crm_lead_estimated_value_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_estimated_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_estimated_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["lead_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_lead_est_audit_clinic",
        "crm_lead_estimated_value_audit",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_crm_lead_est_audit_lead",
        "crm_lead_estimated_value_audit",
        ["lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_crm_lead_est_audit_lead", table_name="crm_lead_estimated_value_audit")
    op.drop_index("ix_crm_lead_est_audit_clinic", table_name="crm_lead_estimated_value_audit")
    op.drop_table("crm_lead_estimated_value_audit")

    op.drop_index("ix_lead_secondary_bookings_lead", table_name="lead_secondary_bookings")
    op.drop_index("ix_lead_secondary_bookings_clinic_booking", table_name="lead_secondary_bookings")
    op.drop_table("lead_secondary_bookings")

    op.drop_index("ix_family_links_group_id", table_name="family_links")
    op.drop_constraint("fk_family_links_loyalty_group", "family_links", type_="foreignkey")
    op.drop_column("family_links", "group_id")

    op.drop_index("ix_loyalty_groups_clinic", table_name="loyalty_groups")
    op.drop_table("loyalty_groups")
