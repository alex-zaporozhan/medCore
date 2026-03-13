"""Add Story.media_type, PromoPost.video_url and additional_image_urls.

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("media_type", sa.String(16), nullable=False, server_default="image"),
    )
    op.add_column(
        "promo_posts",
        sa.Column("video_url", sa.String(1000), nullable=True),
    )
    op.add_column(
        "promo_posts",
        sa.Column("additional_image_urls", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("promo_posts", "additional_image_urls")
    op.drop_column("promo_posts", "video_url")
    op.drop_column("stories", "media_type")
