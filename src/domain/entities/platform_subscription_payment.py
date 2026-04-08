"""Platform subscription payment row (contour B) — separate from patient payments table."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PlatformSubscriptionPayment(Base):
    """Payment for platform SaaS subscription linked to signup intent."""

    __tablename__ = "platform_subscription_payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    signup_intent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_signup_intents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="RUB")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    webhook_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="ux_platform_sub_payments_provider_id",
        ),
    )
