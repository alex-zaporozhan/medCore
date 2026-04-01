"""medical file audit log

Revision ID: f3a4b5c6d7e8
Revises: dc7378b37f12
Create Date: 2026-03-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "dc7378b37f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medical_file_audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", sa.Uuid(), sa.ForeignKey("patient_medical_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("meta", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_medical_file_audit_log_clinic_id", "medical_file_audit_log", ["clinic_id"])
    op.create_index("ix_medical_file_audit_log_patient_id", "medical_file_audit_log", ["patient_id"])
    op.create_index("ix_medical_file_audit_log_file_id", "medical_file_audit_log", ["file_id"])
    op.create_index(
        "ix_medical_file_audit_clinic_created",
        "medical_file_audit_log",
        ["clinic_id", "created_at"],
    )
    op.create_index(
        "ix_medical_file_audit_patient_created",
        "medical_file_audit_log",
        ["patient_id", "created_at"],
    )
    op.create_index(
        "ix_medical_file_audit_file_created",
        "medical_file_audit_log",
        ["file_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_medical_file_audit_file_created", table_name="medical_file_audit_log")
    op.drop_index("ix_medical_file_audit_patient_created", table_name="medical_file_audit_log")
    op.drop_index("ix_medical_file_audit_clinic_created", table_name="medical_file_audit_log")
    op.drop_index("ix_medical_file_audit_log_file_id", table_name="medical_file_audit_log")
    op.drop_index("ix_medical_file_audit_log_patient_id", table_name="medical_file_audit_log")
    op.drop_index("ix_medical_file_audit_log_clinic_id", table_name="medical_file_audit_log")
    op.drop_table("medical_file_audit_log")

