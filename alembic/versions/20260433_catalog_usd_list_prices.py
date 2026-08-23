"""Public SaaS catalog list prices: USD-denominated $20 / $100 / $200.

Revision ID: 20260433_catalog_usd_list_prices
Revises: 20260432_enterprise_leads_source_status_idx

Column names stay price_*_rub / list_price_rub (additive contract). Amounts are
USD list prices shown on the public site. YooKassa still charges the numeric
amount until a USD/Stripe contour exists.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260433_catalog_usd_list_prices"
down_revision: Union[str, Sequence[str], None] = "20260432_enterprise_leads_source_status_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 20.00, price_annual_rub = 200.00
            WHERE slug = 'start'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 100.00, price_annual_rub = 1000.00
            WHERE slug = 'growth'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 200.00, price_annual_rub = 2000.00
            WHERE slug = 'business_os'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 15.00
            WHERE entitlement_key = 'tasks.kanban'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 29.00
            WHERE entitlement_key = 'crm.pipeline'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 12.00
            WHERE entitlement_key = 'marketing.attribution'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 19.00
            WHERE entitlement_key = 'retention.bundle'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 49.00
            WHERE entitlement_key = 'omni.embed.bundle'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 29.00
            WHERE entitlement_key = 'ai.assistant.chat'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 39.00
            WHERE entitlement_key = 'ai.rag.org_kb'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 19.00
            WHERE entitlement_key = 'import.crm_v1'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 2900.00, price_annual_rub = 29000.00
            WHERE slug = 'start'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 5900.00, price_annual_rub = 59000.00
            WHERE slug = 'growth'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 14900.00, price_annual_rub = 149000.00
            WHERE slug = 'business_os'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 1500.00
            WHERE entitlement_key = 'tasks.kanban'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 2800.00
            WHERE entitlement_key = 'crm.pipeline'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 1200.00
            WHERE entitlement_key = 'marketing.attribution'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 1800.00
            WHERE entitlement_key = 'retention.bundle'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 4900.00
            WHERE entitlement_key = 'omni.embed.bundle'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 2900.00
            WHERE entitlement_key = 'ai.assistant.chat'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 3900.00
            WHERE entitlement_key = 'ai.rag.org_kb'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_options SET list_price_rub = 1990.00
            WHERE entitlement_key = 'import.crm_v1'
            """
        )
    )
