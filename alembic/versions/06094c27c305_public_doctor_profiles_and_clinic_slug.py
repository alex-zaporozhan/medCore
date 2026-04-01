"""public doctor profiles and clinic slug

Revision ID: 06094c27c305
Revises: l3m4n5o6p7q8
Create Date: 2026-03-31 11:09:07.773650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06094c27c305'
down_revision: Union[str, Sequence[str], None] = 'l3m4n5o6p7q8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # clinics.clinic_slug (public SEO slug)
    op.add_column("clinics", sa.Column("clinic_slug", sa.String(length=120), nullable=True))
    op.create_index("ix_clinics_clinic_slug", "clinics", ["clinic_slug"], unique=True)
    # Backfill for existing rows to keep public URLs functional even before manual customization.
    op.execute(
        "UPDATE clinics SET clinic_slug = 'clinic-' || left(CAST(id AS text), 8) "
        "WHERE clinic_slug IS NULL"
    )

    # public_doctor_profiles table
    op.create_table(
        "public_doctor_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("doctor_slug", sa.String(length=120), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("public_photo_url", sa.String(length=500), nullable=True),
        sa.Column("short_bio", sa.String(length=500), nullable=True),
        sa.Column("about_md", sa.Text(), nullable=True),
        sa.Column("languages", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("education", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("certifications", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("clinic_id", "doctor_id", name="ux_public_doctor_profile_clinic_doctor"),
        sa.UniqueConstraint("clinic_id", "doctor_slug", name="ux_public_doctor_profile_clinic_slug"),
    )
    op.create_index(
        "ix_public_doctor_profiles_clinic_id",
        "public_doctor_profiles",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_public_doctor_profiles_doctor_id",
        "public_doctor_profiles",
        ["doctor_id"],
        unique=False,
    )
    op.create_index(
        "ix_public_doctor_profiles_is_published",
        "public_doctor_profiles",
        ["is_published"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_public_doctor_profiles_is_published", table_name="public_doctor_profiles")
    op.drop_index("ix_public_doctor_profiles_doctor_id", table_name="public_doctor_profiles")
    op.drop_index("ix_public_doctor_profiles_clinic_id", table_name="public_doctor_profiles")
    op.drop_table("public_doctor_profiles")

    op.drop_index("ix_clinics_clinic_slug", table_name="clinics")
    op.drop_column("clinics", "clinic_slug")
