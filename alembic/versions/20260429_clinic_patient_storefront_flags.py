"""Patient PWA commerce vitrine flags on clinics (ADR-013 storefront).

Revision ID: 20260429_storefront
Revises: (head chain — set down_revision to latest commerce-related if needed)
"""

from alembic import op
import sqlalchemy as sa


revision = "20260429_storefront"
down_revision = "20260428_enterprise_leads_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column(
            "patient_store_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "clinics",
        sa.Column("patient_store_title", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "clinics",
        sa.Column("patient_store_subtitle", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clinics", "patient_store_subtitle")
    op.drop_column("clinics", "patient_store_title")
    op.drop_column("clinics", "patient_store_visible")
