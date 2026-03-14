import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .event_bus import EventBus
from .standard_events import BOOKING_COMPLETED
from .domain_event import DomainEvent
from src.application.services.wallet_service import EarnPointsInput, WalletService
from src.core.datetime_utils import utc_now
from src.domain.entities.loyalty_policy import LoyaltyPolicy
from src.infrastructure.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


def _uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    from uuid import UUID as _UUID

    try:
        return _UUID(value)
    except Exception:
        return None


async def handle_loyalty_on_booking_completed(event: DomainEvent) -> None:
    """Accrue loyalty points on successful booking completion.

    Phase 1: simplified policy – fixed percent from visit (stubbed to 5%).
    Real policy will be driven from clinic settings / LoyaltyPolicy.
    """
    clinic_id = _uuid(event.payload.get("clinic_id"))
    patient_id = _uuid(event.payload.get("patient_id"))

    if not clinic_id or not patient_id:
        logger.warning(
            "[Loyalty] BookingCompleted payload missing clinic_id/patient_id",
            extra={"payload": event.payload},
        )
        return

    async_session: AsyncSession | None = None
    try:
        async_session = AsyncSessionLocal()
        async with async_session.begin():
            wallet_service = WalletService(async_session)

            # Use amount_paid from event payload (computed by ERP/Finance node),
            # skip earning if amount is not provided.
            amount_str = event.payload.get("amount_paid")
            if not amount_str:
                logger.info(
                    "[Loyalty] BookingCompleted without amount_paid - skipping cashback",
                    extra={"payload": event.payload},
                )
                return
            try:
                amount_paid = Decimal(str(amount_str))
            except Exception:
                logger.warning(
                    "[Loyalty] Invalid amount_paid in BookingCompleted",
                    extra={"payload": event.payload},
                )
                return

            # Load clinic loyalty policy; default to 0% if not configured.
            policy_result = await async_session.execute(
                select(LoyaltyPolicy).where(LoyaltyPolicy.clinic_id == clinic_id)
            )
            policy: LoyaltyPolicy | None = policy_result.scalar_one_or_none()
            cashback_percent = (
                policy.cashback_percent if policy is not None else Decimal("0.00")
            )

            if cashback_percent <= Decimal("0"):
                return

            points = (amount_paid * cashback_percent).quantize(Decimal("0.01"))
            if points <= Decimal("0.00"):
                return

            data = EarnPointsInput(
                clinic_id=clinic_id,
                patient_id=patient_id,
                amount=points,
                happened_at=utc_now(),
                booking_id=_uuid(event.payload.get("booking_id")),
                description="Cashback for completed booking",
            )
            await wallet_service.earn_points(data)
    except Exception as exc:  # pragma: no cover - защитный слой логирования
        logger.exception(
            "[Loyalty] Unexpected error while handling BookingCompleted",
            extra={"error": str(exc), "payload": event.payload},
        )
    finally:
        if async_session is not None:
            await async_session.close()


def register_loyalty_event_handlers(event_bus: EventBus) -> None:
    event_bus.subscribe(BOOKING_COMPLETED, handle_loyalty_on_booking_completed)

