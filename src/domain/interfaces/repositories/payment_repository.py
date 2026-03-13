"""Payment repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.payment import Payment


class PaymentRepository(ABC):
    """Repository interface for Payment entity."""

    @abstractmethod
    async def create(self, payment: Payment) -> Payment:
        """Create a new payment."""
        ...

    @abstractmethod
    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Get payment by ID."""
        ...

    @abstractmethod
    async def get_by_provider_id(
        self,
        provider: str,
        provider_payment_id: str,
    ) -> Payment | None:
        """Get payment by provider and provider_payment_id."""
        ...

    @abstractmethod
    async def update(self, payment: Payment) -> Payment:
        """Update payment."""
        ...
