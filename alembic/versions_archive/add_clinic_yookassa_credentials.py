"""Add per-clinic YooKassa credentials (shop_id + encrypted secret).

Revision ID: k2l3m4n5o6p7
Revises: p1q2r3s4t5u6
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("yookassa_shop_id", sa.String(100), nullable=True))
    op.add_column("clinics", sa.Column("yookassa_secret_key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "yookassa_secret_key_encrypted")
    op.drop_column("clinics", "yookassa_shop_id")
