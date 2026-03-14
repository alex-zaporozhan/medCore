"""Add OAuth identifier fields to patients.

Revision ID: add_patient_oauth_ids
Revises: y1z2a3b4c5d6
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_patient_oauth_ids"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("vk_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("yandex_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("vk_screen_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("yandex_login", sa.String(length=255), nullable=True),
    )

    op.create_index("idx_patients_vk_id", "patients", ["vk_id"])
    op.create_index("idx_patients_yandex_id", "patients", ["yandex_id"])

    op.create_unique_constraint(
        "ux_patients_clinic_vk_id",
        "patients",
        ["clinic_id", "vk_id"],
    )
    op.create_unique_constraint(
        "ux_patients_clinic_yandex_id",
        "patients",
        ["clinic_id", "yandex_id"],
    )


def downgrade() -> None:
    op.drop_constraint("ux_patients_clinic_yandex_id", "patients", type_="unique")
    op.drop_constraint("ux_patients_clinic_vk_id", "patients", type_="unique")

    op.drop_index("idx_patients_yandex_id", table_name="patients")
    op.drop_index("idx_patients_vk_id", table_name="patients")

    op.drop_column("patients", "yandex_login")
    op.drop_column("patients", "vk_screen_name")
    op.drop_column("patients", "yandex_id")
    op.drop_column("patients", "vk_id")

