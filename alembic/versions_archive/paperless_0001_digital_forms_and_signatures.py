"""Add digital form templates, submissions and e-signatures tables.

Revision ID: paperless_0001_digital_forms_and_signatures
Revises: c3d4e5f6g7h8_erp_finance_inventory
Create Date: 2026-03-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "paperless_0001_digital_forms_and_signatures"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8_erp_finance_inventory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with paperless office tables."""
    op.create_table(
        "digital_form_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema", sa.JSON(), nullable=False),
        sa.Column(
            "requires_signature",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "active",
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
        sa.UniqueConstraint(
            "clinic_id",
            "code",
            "version",
            name="ux_digital_form_templates_clinic_code_version",
        ),
    )
    op.create_index(
        "idx_digital_form_templates_clinic_code_active",
        "digital_form_templates",
        ["clinic_id", "code", "active"],
        unique=False,
    )

    op.create_table(
        "digital_form_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "submitted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("submitted_by", sa.String(length=32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("signature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["digital_form_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_digital_form_submissions_clinic_patient",
        "digital_form_submissions",
        ["clinic_id", "patient_id"],
        unique=False,
    )
    op.create_index(
        "idx_digital_form_submissions_clinic_booking",
        "digital_form_submissions",
        ["clinic_id", "booking_id"],
        unique=False,
    )

    op.create_table(
        "e_signatures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "digital_form_submission_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "signed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("signer_name", sa.String(length=255), nullable=True),
        sa.Column("signer_role", sa.String(length=64), nullable=False),
        sa.Column("signature_type", sa.String(length=32), nullable=False),
        sa.Column("signature_payload", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(
            ["digital_form_submission_id"],
            ["digital_form_submissions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_e_signatures_clinic_patient",
        "e_signatures",
        ["clinic_id", "patient_id"],
        unique=False,
    )

    # Link submissions to signatures (optional one-to-one backref).
    op.create_foreign_key(
        "fk_digital_form_submissions_signature",
        "digital_form_submissions",
        "e_signatures",
        ["signature_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade paperless office schema."""
    op.drop_constraint(
        "fk_digital_form_submissions_signature",
        "digital_form_submissions",
        type_="foreignkey",
    )

    op.drop_index(
        "idx_e_signatures_clinic_patient",
        table_name="e_signatures",
    )
    op.drop_table("e_signatures")

    op.drop_index(
        "idx_digital_form_submissions_clinic_booking",
        table_name="digital_form_submissions",
    )
    op.drop_index(
        "idx_digital_form_submissions_clinic_patient",
        table_name="digital_form_submissions",
    )
    op.drop_table("digital_form_submissions")

    op.drop_index(
        "idx_digital_form_templates_clinic_code_active",
        table_name="digital_form_templates",
    )
    op.drop_table("digital_form_templates")

