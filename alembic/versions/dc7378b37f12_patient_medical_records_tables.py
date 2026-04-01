"""patient medical records tables

Revision ID: dc7378b37f12
Revises: 06094c27c305
Create Date: 2026-03-31 11:30:52.790820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7378b37f12'
down_revision: Union[str, Sequence[str], None] = '06094c27c305'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Medical record tables (metadata only; content stored in S3-compatible storage).
    op.create_table(
        "patient_medical_visits",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("doctors.id"), nullable=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("notes_md", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_patient_medical_visits_clinic_id", "patient_medical_visits", ["clinic_id"])
    op.create_index("ix_patient_medical_visits_patient_id", "patient_medical_visits", ["patient_id"])
    op.create_index("ix_patient_medical_visits_doctor_id", "patient_medical_visits", ["doctor_id"])
    op.create_index("ix_patient_medical_visits_booking_id", "patient_medical_visits", ["booking_id"])
    op.create_index("ix_patient_medical_visits_visit_date", "patient_medical_visits", ["visit_date"])

    op.create_table(
        "patient_diagnoses",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("patient_medical_visits.id"), nullable=True),
        sa.Column("diagnosis_date", sa.Date(), nullable=False),
        sa.Column("icd10_code", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_patient_diagnoses_clinic_id", "patient_diagnoses", ["clinic_id"])
    op.create_index("ix_patient_diagnoses_patient_id", "patient_diagnoses", ["patient_id"])
    op.create_index("ix_patient_diagnoses_visit_id", "patient_diagnoses", ["visit_id"])
    op.create_index("ix_patient_diagnoses_diagnosis_date", "patient_diagnoses", ["diagnosis_date"])

    op.create_table(
        "patient_medical_files",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("clinic_id", sa.Uuid(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("patient_medical_visits.id"), nullable=True),
        sa.Column("s3_key", sa.String(length=900), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("uploaded_by_admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("s3_key", name="ux_patient_medical_files_s3_key"),
    )
    op.create_index("ix_patient_medical_files_clinic_id", "patient_medical_files", ["clinic_id"])
    op.create_index("ix_patient_medical_files_patient_id", "patient_medical_files", ["patient_id"])
    op.create_index("ix_patient_medical_files_visit_id", "patient_medical_files", ["visit_id"])
    op.create_index("ix_patient_medical_files_s3_key", "patient_medical_files", ["s3_key"], unique=True)

    # RBAC permissions: patients.medical.read / patients.medical.write
    op.execute(
        """
        INSERT INTO permissions (id, code, description)
        VALUES
          (gen_random_uuid(), 'patients.medical.read', 'Просмотр медицинской карты пациента (визиты, диагнозы, файлы).'),
          (gen_random_uuid(), 'patients.medical.write', 'Изменение медицинской карты пациента (визиты, диагнозы, файлы).')
        ON CONFLICT (code) DO NOTHING
        """
    )
    # Link to system roles (global roles roles.clinic_id IS NULL and any clinic-copied roles).
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN ('patients.medical.read', 'patients.medical.write')
        WHERE r.code IN ('owner', 'manager', 'admin', 'doctor')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_patient_medical_files_s3_key", table_name="patient_medical_files")
    op.drop_index("ix_patient_medical_files_visit_id", table_name="patient_medical_files")
    op.drop_index("ix_patient_medical_files_patient_id", table_name="patient_medical_files")
    op.drop_index("ix_patient_medical_files_clinic_id", table_name="patient_medical_files")
    op.drop_table("patient_medical_files")

    op.drop_index("ix_patient_diagnoses_diagnosis_date", table_name="patient_diagnoses")
    op.drop_index("ix_patient_diagnoses_visit_id", table_name="patient_diagnoses")
    op.drop_index("ix_patient_diagnoses_patient_id", table_name="patient_diagnoses")
    op.drop_index("ix_patient_diagnoses_clinic_id", table_name="patient_diagnoses")
    op.drop_table("patient_diagnoses")

    op.drop_index("ix_patient_medical_visits_visit_date", table_name="patient_medical_visits")
    op.drop_index("ix_patient_medical_visits_booking_id", table_name="patient_medical_visits")
    op.drop_index("ix_patient_medical_visits_doctor_id", table_name="patient_medical_visits")
    op.drop_index("ix_patient_medical_visits_patient_id", table_name="patient_medical_visits")
    op.drop_index("ix_patient_medical_visits_clinic_id", table_name="patient_medical_visits")
    op.drop_table("patient_medical_visits")
