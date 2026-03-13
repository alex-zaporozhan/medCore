"""Update demo omnichannel contact names: human names without channel suffixes.

Revision ID: a1b2c3d4e5f6_omni_names
Revises: z1a2b3c4d5e7
Create Date: 2026-03-05

Data migration: replace 'Анна Телеграм', 'Иван Вотсапп', 'Мария ВКонтакте', 'Елена Почта'
with human names only (Елена Вавилова, Максим Соколов, Валерий Павлов, Мария Кузнецова).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6_omni_names"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import text

    conn = op.get_bind()
    updates = [
        ("Анна Телеграм", "Елена Вавилова"),
        ("Иван Вотсапп", "Максим Соколов"),
        ("Мария ВКонтакте", "Валерий Павлов"),
        ("Елена Почта", "Мария Кузнецова"),
    ]
    for old_name, new_name in updates:
        conn.execute(text("UPDATE omni_contacts SET full_name = :new WHERE full_name = :old"), {"old": old_name, "new": new_name})


def downgrade() -> None:
    from sqlalchemy import text

    conn = op.get_bind()
    rev_updates = [
        ("Елена Вавилова", "Анна Телеграм"),
        ("Максим Соколов", "Иван Вотсапп"),
        ("Валерий Павлов", "Мария ВКонтакте"),
        ("Мария Кузнецова", "Елена Почта"),
    ]
    for new_name, old_name in rev_updates:
        conn.execute(text("UPDATE omni_contacts SET full_name = :old WHERE full_name = :new"), {"old": old_name, "new": new_name})
