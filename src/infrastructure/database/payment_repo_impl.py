"""Payment repository implementation."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.payment import Payment
from src.domain.interfaces.repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)


class PaymentRepositoryImpl(PaymentRepository):
    """SQLAlchemy implementation of PaymentRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        """Create a new payment."""
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        logger.info(
            "Payment created",
            extra={
                "payment_id": str(payment.id),
                "booking_id": str(payment.booking_id),
                "provider_payment_id": payment.provider_payment_id,
            },
        )
        return payment

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Get payment by ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_id(
        self,
        provider: str,
        provider_payment_id: str,
    ) -> Payment | None:
        """Get payment by provider and provider_payment_id."""
        result = await self.session.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_payment_id == provider_payment_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, payment: Payment) -> Payment:
        """Update payment."""
        await self.session.flush()
        await self.session.refresh(payment)
        logger.info(
            "Payment updated",
            extra={"payment_id": str(payment.id), "status": payment.status},
        )
        return payment
