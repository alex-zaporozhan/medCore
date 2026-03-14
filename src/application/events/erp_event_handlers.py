import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events.domain_event import DomainEvent
from src.application.events.event_bus import EventBus
from src.application.events.standard_events import BOOKING_COMPLETED, PAYMENT_SUCCESS
from src.application.services.booking_erp_service import (
    BookingErpService,
    ERPConfigurationError,
)
from src.application.services.loyalty_service import (
    LoyaltyService,
    PurchaseSubscriptionInput,
)
from src.core.datetime_utils import utc_now
from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking
from src.domain.entities.payment import Payment
from src.infrastructure.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


async def _run_erp_node_in_transaction(booking_id: UUID) -> None:
    """Run ERP node for booking inside its own DB transaction.

    Any ERPConfigurationError will be propagated to allow caller to handle
    business-level consequences (like attention feed, error codes, etc.).
    """
    async_session: AsyncSession | None = None
    try:
        async_session = AsyncSessionLocal()
        async with async_session.begin():
            erp_service = BookingErpService(async_session)
            await erp_service.process_booking_completed(booking_id)
    finally:
        if async_session is not None:
            await async_session.close()


async def _mark_booking_erp_error(
    booking_id: UUID,
    clinic_id: UUID,
    error_code: str,
) -> None:
    """Persist ERP error on booking without touching its status.

    Runs in a separate short transaction so that business error details are
    saved even though the main ERP transaction is rolled back.
    """
    async_session: AsyncSession | None = None
    try:
        async_session = AsyncSessionLocal()
        async with async_session.begin():
            booking = await async_session.get(Booking, booking_id)
            if not booking or booking.clinic_id != clinic_id:
                return
            booking.erp_error_code = error_code
            booking.erp_processed = False
            booking.updated_at = utc_now()
            async_session.add(booking)
    finally:
        if async_session is not None:
            await async_session.close()


async def handle_erp_on_booking_completed(event: DomainEvent) -> None:
    logger.info(
        "[ERP] BookingCompleted received",
        extra={"event_name": event.name, "payload": event.payload},
    )

    booking_id_raw = event.payload.get("booking_id")
    clinic_id_raw = event.payload.get("clinic_id")
    if not booking_id_raw or not clinic_id_raw:
        logger.warning(
            "[ERP] BookingCompleted payload missing booking_id/clinic_id",
            extra={"payload": event.payload},
        )
        return

    booking_id = UUID(booking_id_raw)
    clinic_id = UUID(clinic_id_raw)

    try:
        await _run_erp_node_in_transaction(booking_id)
    except ERPConfigurationError as erp_exc:
        logger.warning(
            "[ERP] Configuration error while processing booking",
            extra={
                "booking_id": str(booking_id),
                "clinic_id": str(clinic_id),
                "code": erp_exc.code,
            },
        )
        # Persist ERP error details on booking so that UI/AttentionFeed
        # can highlight problematic visits for the owner.
        await _mark_booking_erp_error(
            booking_id=booking_id,
            clinic_id=clinic_id,
            error_code=erp_exc.code,
        )
        # Business error: ERP movements are rolled back, booking status remains as is.
        return
    except Exception as exc:  # pragma: no cover - защитный слой логирования
        logger.exception(
            "[ERP] Unexpected error while handling BookingCompleted",
            extra={
                "booking_id": str(booking_id),
                "clinic_id": str(clinic_id),
                "error": str(exc),
            },
        )


async def handle_erp_on_payment_success(event: DomainEvent) -> None:
    logger.info(
        "[ERP] PaymentSuccess received",
        extra={"event_name": event.name, "payload": event.payload},
    )

    payment_id_raw = event.payload.get("payment_id")
    clinic_id_raw = event.payload.get("clinic_id")
    booking_id_raw = event.payload.get("booking_id")
    if not payment_id_raw or not clinic_id_raw or not booking_id_raw:
        logger.warning(
            "[ERP] PaymentSuccess payload missing ids",
            extra={"payload": event.payload},
        )
        return

    payment_id = UUID(payment_id_raw)

    async_session: AsyncSession | None = None
    try:
        async_session = AsyncSessionLocal()
        async with async_session.begin():
            payment = await async_session.get(Payment, payment_id)
            if not payment:
                logger.warning(
                    "[ERP] PaymentSuccess: payment not found",
                    extra={"payment_id": payment_id_raw},
                )
                return

            booking = await async_session.get(Booking, payment.booking_id)
            if not booking:
                logger.warning(
                    "[ERP] PaymentSuccess: booking not found for payment",
                    extra={"payment_id": payment_id_raw},
                )
                return

            # For Phase 1 we assume dedicated subscription packages are purchased
            # via separate payment flow where service_id encodes package.
            if booking.service_id is None:
                return

            loyalty_service = LoyaltyService(async_session)
            await loyalty_service.purchase_subscription(
                PurchaseSubscriptionInput(
                    clinic_id=booking.clinic_id,
                    patient_id=booking.patient_id,
                    package_id=booking.service_id,
                    payment_id=payment.id,
                    purchased_at=utc_now(),
                )
            )
    finally:
        if async_session is not None:
            await async_session.close()


def register_erp_event_handlers(event_bus: EventBus) -> None:
    event_bus.subscribe(BOOKING_COMPLETED, handle_erp_on_booking_completed)
    event_bus.subscribe(PAYMENT_SUCCESS, handle_erp_on_payment_success)
    
