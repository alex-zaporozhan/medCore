"""Phase 4 (optional Commerce): catalog placeholder for commerce.store_network (inactive).

Revision ID: 20260416_phase4_commerce_catalog_placeholder
Revises: 20260415_phase3_industry_profile_crm_import
Create Date: 2026-04-06

ADR-013 / МП §26: register SKU in platform catalog without selling until product go.
No commerce_* tables yet.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_phase4_commerce_catalog_placeholder"
down_revision: Union[str, Sequence[str], None] = "20260415_phase3_industry_profile_crm_import"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_options (id, entitlement_key, display_name, description, list_price_rub, is_active, sort_order)
            VALUES
              (
                'a0000001-0000-4000-8000-000000000010'::uuid,
                'commerce.store_network',
                'Магазин / продажи по сети точек (Фаза 4)',
                'Опция неактивна до go ARCH+LEAD и реализации ADR-013; см. docs/architecture/domains/commerce_bounded_context.md',
                0.00,
                false,
                100
              )
            ON CONFLICT (entitlement_key) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM platform_catalog_options WHERE entitlement_key = 'commerce.store_network'
            """
        )
    )
