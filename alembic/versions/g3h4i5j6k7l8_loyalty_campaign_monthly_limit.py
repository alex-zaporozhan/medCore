"""Monthly per-patient cap for loyalty campaign tasks.

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loyalty_campaign_settings",
        sa.Column(
            "max_campaign_touches_per_patient_month",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("12"),
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "loyalty_campaign_settings",
        "max_campaign_touches_per_patient_month",
    )
