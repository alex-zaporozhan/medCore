"""Public catalog: Start / Growth / Business OS tiers (LEAD pricing alignment).

Revision ID: 20260426_public_catalog_business_os_tiers
Revises: 20260425_rag_kb_audit_fts
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_public_catalog_business_os_tiers"
down_revision: Union[str, Sequence[str], None] = "20260425_rag_kb_audit_fts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET is_active = false
            WHERE slug = 'starter_rf'
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_plans (
              id, slug, display_name, description, option_keys,
              is_active, sort_order, price_monthly_rub, price_annual_rub
            )
            VALUES
              (
                'b0000001-0000-4000-8000-000000000010'::uuid,
                'start',
                'Start',
                'База для моно-бизнеса: 1 филиал, до 5 сотрудников.',
                '["core.base", "crm.pipeline", "tasks.kanban"]'::jsonb,
                true,
                0,
                2900.00,
                29000.00
              ),
              (
                'b0000001-0000-4000-8000-000000000011'::uuid,
                'growth',
                'Growth',
                'До 3 филиалов, до 20 сотрудников. AI в чатах, финансы, лояльность.',
                '["core.base", "crm.pipeline", "tasks.kanban", "ai.assistant.chat", "marketing.attribution", "retention.bundle"]'::jsonb,
                true,
                1,
                5900.00,
                59000.00
              ),
              (
                'b0000001-0000-4000-8000-000000000012'::uuid,
                'business_os',
                'Business OS',
                'Сеть до 10 филиалов: RAG, задачи, склад, ROI, зарплаты.',
                '["core.base", "crm.pipeline", "tasks.kanban", "ai.assistant.chat", "marketing.attribution", "retention.bundle", "omni.embed.bundle", "ai.rag.org_kb"]'::jsonb,
                true,
                2,
                14900.00,
                149000.00
              )
            ON CONFLICT (slug) DO UPDATE SET
              display_name = EXCLUDED.display_name,
              description = EXCLUDED.description,
              option_keys = EXCLUDED.option_keys,
              is_active = EXCLUDED.is_active,
              sort_order = EXCLUDED.sort_order,
              price_monthly_rub = EXCLUDED.price_monthly_rub,
              price_annual_rub = EXCLUDED.price_annual_rub
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM platform_catalog_plans
            WHERE slug IN ('start', 'growth', 'business_os')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET is_active = true
            WHERE slug = 'starter_rf'
            """
        )
    )
