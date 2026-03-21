"""Add ERP loyalty obligations tables and initialize snapshot from existing subscriptions.

Revision ID: 2ac77a14a1f8
Revises: e6f7g8h9i0j1_owner_integration_settings
Create Date: 2026-03-17 17:19:45.378240

This migration creates the `erp_loyalty_obligations` and
`erp_loyalty_obligation_movements` tables based on the ORM models in
`src.domain.entities.erp_loyalty_obligation` and performs a minimal
snapshot initialization for existing active customer subscriptions.

Snapshot assumptions:
- Only subscriptions with positive `remaining_amount` are initialized.
- For such subscriptions, an obligation is created with
  `initial_amount == remaining_amount` and status `active`.
- A corresponding movement with type `INIT_SNAPSHOT` is recorded.
- Historical ERP obligation movements cannot be reconstructed; this is
  explicitly a best-effort point-in-time snapshot.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2ac77a14a1f8"
down_revision: Union[str, Sequence[str], None] = "e6f7g8h9i0j1_owner_integration_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with ERP loyalty obligations tables and snapshot."""

    op.create_table(
        "erp_loyalty_obligations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initial_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["customer_subscription_id"], ["customer_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_erp_loyalty_obligations_clinic_patient",
        "erp_loyalty_obligations",
        ["clinic_id", "patient_id"],
        unique=False,
    )
    op.create_index(
        "idx_erp_loyalty_obligations_subscription",
        "erp_loyalty_obligations",
        ["customer_subscription_id"],
        unique=False,
    )

    op.create_table(
        "erp_loyalty_obligation_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subscription_usage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("amount_delta", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["obligation_id"], ["erp_loyalty_obligations.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["subscription_usage_id"], ["subscription_usages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_erp_loyalty_obligation_movements_clinic_booking",
        "erp_loyalty_obligation_movements",
        ["clinic_id", "booking_id"],
        unique=False,
    )

    # Minimal snapshot initialization for existing subscriptions.
    # We only initialize obligations for subscriptions that:
    # - are active / not fully used up;
    # - have a positive remaining_amount.
    conn = op.get_bind()

    customer_subscriptions = sa.table(
        "customer_subscriptions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("clinic_id", postgresql.UUID(as_uuid=True)),
        sa.column("patient_id", postgresql.UUID(as_uuid=True)),
        sa.column("status", sa.String(length=32)),
        sa.column("remaining_amount", sa.Numeric(12, 2)),
    )

    obligations = sa.table(
        "erp_loyalty_obligations",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("clinic_id", postgresql.UUID(as_uuid=True)),
        sa.column("patient_id", postgresql.UUID(as_uuid=True)),
        sa.column("customer_subscription_id", postgresql.UUID(as_uuid=True)),
        sa.column("initial_amount", sa.Numeric(12, 2)),
        sa.column("remaining_amount", sa.Numeric(12, 2)),
        sa.column("status", sa.String(length=32)),
        sa.column("created_at", sa.TIMESTAMP(timezone=True)),
        sa.column("updated_at", sa.TIMESTAMP(timezone=True)),
    )

    movements = sa.table(
        "erp_loyalty_obligation_movements",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("obligation_id", postgresql.UUID(as_uuid=True)),
        sa.column("clinic_id", postgresql.UUID(as_uuid=True)),
        sa.column("booking_id", postgresql.UUID(as_uuid=True)),
        sa.column("subscription_usage_id", postgresql.UUID(as_uuid=True)),
        sa.column("movement_type", sa.String(length=32)),
        sa.column("amount_delta", sa.Numeric(12, 2)),
        sa.column("created_at", sa.TIMESTAMP(timezone=True)),
    )

    # Note: using database-side uuid_generate_v4() if available; if not,
    # this snapshot block can be adapted manually where migrations are applied.
    now = sa.func.now()

    active_subs = conn.execute(
        sa.select(
            customer_subscriptions.c.id,
            customer_subscriptions.c.clinic_id,
            customer_subscriptions.c.patient_id,
            customer_subscriptions.c.remaining_amount,
        ).where(
            customer_subscriptions.c.status == "active",
            customer_subscriptions.c.remaining_amount.isnot(None),
            customer_subscriptions.c.remaining_amount > 0,
        )
    ).mappings()

    for row in active_subs:
        obligation_id_expr = sa.text("uuid_generate_v4()")
        movement_id_expr = sa.text("uuid_generate_v4()")

        conn.execute(
            obligations.insert().values(
                id=obligation_id_expr,
                clinic_id=row["clinic_id"],
                patient_id=row["patient_id"],
                customer_subscription_id=row["id"],
                initial_amount=row["remaining_amount"],
                remaining_amount=row["remaining_amount"],
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            movements.insert().values(
                id=movement_id_expr,
                obligation_id=obligation_id_expr,
                clinic_id=row["clinic_id"],
                booking_id=None,
                subscription_usage_id=None,
                movement_type="INIT_SNAPSHOT",
                amount_delta=row["remaining_amount"],
                created_at=now,
            )
        )


def downgrade() -> None:
    """Drop ERP loyalty obligations tables."""
    op.drop_index(
        "idx_erp_loyalty_obligation_movements_clinic_booking",
        table_name="erp_loyalty_obligation_movements",
    )
    op.drop_table("erp_loyalty_obligation_movements")

    op.drop_index(
        "idx_erp_loyalty_obligations_subscription",
        table_name="erp_loyalty_obligations",
    )
    op.drop_index(
        "idx_erp_loyalty_obligations_clinic_patient",
        table_name="erp_loyalty_obligations",
    )
    op.drop_table("erp_loyalty_obligations")

