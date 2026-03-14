"""Add marketing attribution fields to lead_cards.

Revision ID: crm_leads_0002_marketing_fields
Revises: crm_leads_0001
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "crm_leads_0002_marketing_fields"
down_revision: Union[str, Sequence[str], None] = "crm_leads_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Upgrade schema."""
  op.add_column(
      "lead_cards",
      sa.Column("visit_attribution_id", postgresql.UUID(as_uuid=True), nullable=True),
  )
  op.add_column(
      "lead_cards",
      sa.Column("utm_source", sa.String(length=128), nullable=True),
  )
  op.add_column(
      "lead_cards",
      sa.Column("utm_medium", sa.String(length=128), nullable=True),
  )
  op.add_column(
      "lead_cards",
      sa.Column("utm_campaign", sa.String(length=128), nullable=True),
  )
  op.add_column(
      "lead_cards",
      sa.Column("utm_content", sa.String(length=128), nullable=True),
  )
  op.add_column(
      "lead_cards",
      sa.Column("utm_term", sa.String(length=128), nullable=True),
  )
  op.create_index(
      "idx_lead_cards_visit_attribution",
      "lead_cards",
      ["visit_attribution_id"],
      unique=False,
  )


def downgrade() -> None:
  """Downgrade schema."""
  op.drop_index("idx_lead_cards_visit_attribution", table_name="lead_cards")
  op.drop_column("lead_cards", "utm_term")
  op.drop_column("lead_cards", "utm_content")
  op.drop_column("lead_cards", "utm_campaign")
  op.drop_column("lead_cards", "utm_medium")
  op.drop_column("lead_cards", "utm_source")
  op.drop_column("lead_cards", "visit_attribution_id")

