"""Add clinic theme columns, patient consent fields, agreement settings.

Revision ID: a1b2c3d4e5f6
Revises: c9d0e1f2a3b4
Create Date: 2026-02-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("theme_primary_color", sa.String(50), nullable=True))
    op.add_column("clinics", sa.Column("theme_logo_url", sa.String(500), nullable=True))
    op.add_column("clinics", sa.Column("theme_font_family", sa.String(100), nullable=True))

    op.add_column("patients", sa.Column("consent_pd_at", sa.DateTime(), nullable=True))
    op.add_column("patients", sa.Column("consent_mailing", sa.Boolean(), server_default="false", nullable=False))

    op.create_table(
        "agreement_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pd_agreement_text", sa.Text(), nullable=True),
        sa.Column("allow_registration_without_mailing_consent", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agreement_settings_clinic_id", "agreement_settings", ["clinic_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agreement_settings_clinic_id", "agreement_settings")
    op.drop_table("agreement_settings")
    op.drop_column("patients", "consent_mailing")
    op.drop_column("patients", "consent_pd_at")
    op.drop_column("clinics", "theme_font_family")
    op.drop_column("clinics", "theme_logo_url")
    op.drop_column("clinics", "theme_primary_color")
