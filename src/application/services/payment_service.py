"""Payment service for YooKassa and booking status sync."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.payment_dto import CreatePaymentResponse
from src.core.config import settings
from src.core.patient_messages import (
    PAYMENT_ALREADY_CONFIRMED,
    PAYMENT_BOOKING_NOT_FOUND,
    PAYMENT_CANCELLED_BOOKING,
)
from src.application.services.pricing_service import PricingService
from src.core.encryption import decrypt_ciphertext
from src.domain.entities.clinic import Clinic
from src.domain.entities.payment import Payment
from src.domain.entities.prepayment_policy import PrepaymentPolicy
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.domain.interfaces.repositories.payment_repository import PaymentRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.infrastructure.database.payment_repo_impl import PaymentRepositoryImpl
from src.infrastructure.external_apis.yookassa_client import (
    YooKassaClient,
    YooKassaClientError,
)
from src.application.events.event_bus import get_event_bus
from src.application.events.standard_events import make_payment_success_event

logger = logging.getLogger(__name__)

PROVIDER_NAME = "yookassa"


def _yookassa_client_for_clinic(clinic: Clinic | None) -> YooKassaClient:
    """Return YooKassa client: per-clinic credentials if set, else global settings."""
    if clinic and clinic.yookassa_shop_id and clinic.yookassa_secret_key_encrypted:
        secret = decrypt_ciphertext(clinic.yookassa_secret_key_encrypted)
        if secret:
            return YooKassaClient(shop_id=clinic.yookassa_shop_id, secret_key=secret)
    return YooKassaClient()
class PaymentService:
    """Application service for creating payments and handling payment webhooks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session
        self.booking_repository: BookingRepository = BookingRepositoryImpl(session)
        self.payment_repository: PaymentRepository = PaymentRepositoryImpl(session)

    async def create_payment(
        self,
        booking_id: UUID,
        return_url: str | None = None,
        gateway_id: str | None = None,
    ) -> CreatePaymentResponse:
        """
        Create payment in YooKassa for booking. Amount from clinic prepayment_amount
        or booking.prepayment_amount if already set. Returns payment_url and provider_payment_id.
        If gateway_id is provided, it must match clinic's active gateway (for future multi-gateway).
        """
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise LookupError(PAYMENT_BOOKING_NOT_FOUND)
        if booking.status == "cancelled":
            raise ValueError(PAYMENT_CANCELLED_BOOKING)
        if booking.status == "confirmed":
            raise ValueError(PAYMENT_ALREADY_CONFIRMED)

        # Global prepayment switch: if clinic has prepayment disabled, confirm without payment
        clinic_result = await self.session.execute(
            select(Clinic).where(Clinic.id == booking.clinic_id).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        if gateway_id and clinic and getattr(clinic, "payment_gateway", None) != gateway_id:
            raise ValueError("Selected payment gateway is not available for this clinic")
        if clinic and getattr(clinic, "prepayment_enabled", False) is False:
            logger.info(
                "Prepayment disabled for clinic",
                extra={"booking_id": str(booking_id), "clinic_id": str(booking.clinic_id)},
            )
            if booking.status == "pending":
                booking.status = "confirmed"
                await self.booking_repository.update(booking)
            return CreatePaymentResponse(
                payment_url="",
                provider_payment_id="",
                prepayment_required=False,
            )

        # Check prepayment policies: if matching policy has mode "none", no payment required
        policies_result = await self.session.execute(
            select(PrepaymentPolicy)
            .where(
                PrepaymentPolicy.clinic_id == booking.clinic_id,
                PrepaymentPolicy.enabled.is_(True),
            )
            .order_by(PrepaymentPolicy.priority.desc())
        )
        policies = list(policies_result.scalars().all())
        for p in policies:
            if p.mode == "none":
                match = False
                if p.scope_type == "service" and (
                    p.scope_service_id is None or p.scope_service_id == booking.service_id
                ):
                    match = True
                elif p.scope_type == "doctor" and (
                    p.scope_doctor_id is None or p.scope_doctor_id == booking.doctor_id
                ):
                    match = True
                elif p.scope_type == "doctor_service" and (
                    (p.scope_service_id is None or p.scope_service_id == booking.service_id)
                    and (p.scope_doctor_id is None or p.scope_doctor_id == booking.doctor_id)
                ):
                    match = True
                if match:
                    logger.info(
                        "Prepayment not required (policy mode=none)",
                        extra={"booking_id": str(booking_id), "policy_id": str(p.id)},
                    )
                    if booking.status == "pending":
                        booking.status = "confirmed"
                        await self.booking_repository.update(booking)
                    return CreatePaymentResponse(
                        payment_url="",
                        provider_payment_id="",
                        prepayment_required=False,
                    )

        # Amount: prefer booking.prepayment_amount, else clinic default
        amount = booking.prepayment_amount
        if amount <= 0:
            clinic_result = await self.session.execute(
                select(Clinic).where(Clinic.id == booking.clinic_id).limit(1)
            )
            clinic = clinic_result.scalar_one_or_none()
            amount = (clinic and clinic.prepayment_amount) or Decimal("500.00")

        original_amount = amount
        discount_amount = Decimal("0")

        pricing_svc = PricingService(self.session)
        pricing_result = await pricing_svc.compute_effective_price(
            clinic_id=booking.clinic_id,
            service_id=booking.service_id,
            doctor_id=booking.doctor_id,
            patient_id=booking.patient_id,
            on_date=booking.appointment_date,
            base_price=amount,
        )
        discount_amount = pricing_result.discount_amount
        amount = pricing_result.effective_price

        url = return_url or settings.yookassa_return_url
        description = f"Предоплата записи {booking_id}"

        clinic_result = await self.session.execute(
            select(Clinic).where(Clinic.id == booking.clinic_id).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        yookassa = _yookassa_client_for_clinic(clinic)

        try:
            provider_id, confirmation_url = yookassa.create_payment(
                amount=amount,
                return_url=url,
                description=description,
                booking_id=booking_id,
            )
        except YooKassaClientError as exc:
            logger.exception(
                "YooKassa create payment failed", extra={"booking_id": str(booking_id)}
            )
            raise ValueError(str(exc)) from exc

        payment = Payment(
            clinic_id=booking.clinic_id,
            booking_id=booking_id,
            provider=PROVIDER_NAME,
            provider_payment_id=provider_id,
            amount=amount,
            currency="RUB",
            status="pending",
            provider_metadata=None,
        )
        payment = await self.payment_repository.create(payment)

        # Optionally link booking to payment (for awaiting_payment flow)
        booking.payment_id = payment.id
        if booking.prepayment_amount <= 0:
            booking.prepayment_amount = amount
        await self.booking_repository.update(booking)

        logger.info(
            "Payment created for booking",
            extra={"booking_id": str(booking_id), "payment_id": str(payment.id)},
        )
        return CreatePaymentResponse(
            payment_url=confirmation_url,
            provider_payment_id=provider_id,
            original_amount=str(original_amount) if discount_amount > 0 else None,
            discount_amount=str(discount_amount) if discount_amount > 0 else None,
            final_amount=str(amount) if discount_amount > 0 else None,
        )

    async def handle_webhook(self, payload: dict) -> None:
        """
            Handle YooKassa webhook: verify payment status via API, update Payment and Booking.
            Payload may be { "type": "notification", "event": "payment.succeeded", "object": { "id": "..." } }
            or we accept payment id in payload and fetch status from API.
            """
        obj = payload.get("object") or payload
        payment_id = obj.get("id") if isinstance(obj, dict) else None
        if not payment_id:
            logger.warning(
                "Webhook payload missing payment id",
                extra={"payload_keys": list(payload.keys())},
            )
            return

        payment_record = await self.payment_repository.get_by_provider_id(
            PROVIDER_NAME,
            payment_id,
        )
        if not payment_record:
            logger.warning(
                "Webhook: unknown provider_payment_id",
                extra={"provider_payment_id": payment_id},
            )
            return

        clinic_result = await self.session.execute(
            select(Clinic).where(Clinic.id == payment_record.clinic_id).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        yookassa = _yookassa_client_for_clinic(clinic)
        try:
            data = yookassa.get_payment(payment_id)
        except YooKassaClientError:
            logger.exception(
                "Webhook: failed to fetch payment from YooKassa",
                extra={"payment_id": payment_id},
            )
            return

        status = (data.get("status") or "").lower()
        if status not in (
            "succeeded",
            "canceled",
            "cancelled",
            "refunded",
            "pending",
            "waiting_for_capture",
        ):
            logger.info(
                "Webhook: ignoring status",
                extra={"payment_id": payment_id, "status": status},
            )
            return

        # Map YooKassa status to our status
        if status == "succeeded":
            our_status = "succeeded"
        elif status in ("canceled", "cancelled"):
            our_status = "canceled"
        elif status == "refunded":
            our_status = "refunded"
        else:
            our_status = payment_record.status

        payment_record.status = our_status
        if data:
            payment_record.provider_metadata = data
        payment_record = await self.payment_repository.update(payment_record)

        booking = await self.booking_repository.get_by_id(payment_record.booking_id)
        if not booking:
            return

        event_bus = get_event_bus()

        if our_status == "succeeded":
            if booking.status in ("pending", "awaiting_payment"):
                booking.status = "confirmed"
                await self.booking_repository.update(booking)
                try:
                    await event_bus.publish(make_payment_success_event(payment_record))
                except Exception:
                    logger.exception(
                        "Failed to publish PaymentSuccess event",
                        extra={
                            "booking_id": str(booking.id),
                            "payment_id": str(payment_record.id),
                        },
                    )
                logger.info(
                    "Booking confirmed after payment",
                    extra={
                        "booking_id": str(booking.id),
                        "payment_id": str(payment_record.id),
                    },
                )
        elif our_status in ("canceled", "refunded"):
            if booking.status == "pending":
                booking.status = "cancelled"
                await self.booking_repository.update(booking)
                logger.info(
                    "Booking cancelled after payment cancel/refund",
                    extra={"booking_id": str(booking.id)},
                )
