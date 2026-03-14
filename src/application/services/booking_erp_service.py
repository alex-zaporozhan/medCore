"""Transactional ERP node for handling Booking.completed -> finance, payroll, inventory."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.finance_service import (
    CreateFinancialTransactionInput,
    FinanceService,
)
from src.application.services.inventory_service import (
    InsufficientStockError,
    InventoryMovementInput,
    InventoryService,
)
from src.application.services.payroll_service import (
    PayrollService,
    SalaryCalculationContext,
)
from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.service import Service
from src.domain.entities.visit_attribution import VisitAttribution
from src.domain.entities.wallet_transaction import WalletTransaction
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.domain.interfaces.repositories.payment_repository import PaymentRepository
from src.domain.interfaces.repositories.service_repository import ServiceRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.infrastructure.database.payment_repo_impl import PaymentRepositoryImpl
from src.infrastructure.database.service_repo_impl import ServiceRepositoryImpl

logger = logging.getLogger(__name__)


class ERPConfigurationError(RuntimeError):
    """Raised when ERP cannot process booking due to configuration gaps."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class BookingErpContext:
    booking: Booking
    clinic: Clinic
    doctor: Doctor
    service: Service
    services_amount: Decimal
    products_amount: Decimal
    wallet_spent_amount: Decimal
    period_start: date | None
    period_end: date | None


class BookingErpService:
    """High-level ERP orchestrator for booking completion."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.booking_repository: BookingRepository = BookingRepositoryImpl(session)
        self.payment_repository: PaymentRepository = PaymentRepositoryImpl(session)
        self.service_repository: ServiceRepository = ServiceRepositoryImpl(session)
        self.finance_service = FinanceService(session)
        self.payroll_service = PayrollService(session)
        self.inventory_service = InventoryService(session)

    async def _load_context(self, booking_id: UUID) -> BookingErpContext:
        booking = await self.booking_repository.get_by_id(booking_id)
        if not booking:
            raise LookupError("Booking not found")

        clinic_result = await self.session.execute(
            select(Clinic).where(Clinic.id == booking.clinic_id).limit(1)
        )
        clinic = clinic_result.scalar_one_or_none()
        if not clinic:
            raise RuntimeError("Clinic not found for booking")

        doctor_result = await self.session.execute(
            select(Doctor).where(Doctor.id == booking.doctor_id).limit(1)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise RuntimeError("Doctor not found for booking")

        service = await self.service_repository.get_by_id(booking.service_id)
        if not service:
            raise RuntimeError("Service not found for booking")

        services_amount = getattr(service, "price", None) or Decimal("0")
        products_amount = Decimal("0")

        # Sum of wallet points spent specifically for this booking in this clinic.
        wallet_spent_amount = Decimal("0")
        wallet_tx_result = await self.session.execute(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
                WalletTransaction.clinic_id == booking.clinic_id,
                WalletTransaction.booking_id == booking.id,
                WalletTransaction.type == "spend",
            )
        )
        wallet_spent_amount = Decimal(wallet_tx_result.scalar() or 0)

        return BookingErpContext(
            booking=booking,
            clinic=clinic,
            doctor=doctor,
            service=service,
            services_amount=services_amount,
            products_amount=products_amount,
            wallet_spent_amount=wallet_spent_amount,
            period_start=booking.appointment_date,
            period_end=booking.appointment_date,
        )

    async def process_booking_completed(self, booking_id: UUID) -> None:
        """Main ERP entrypoint: create finance, salary, inventory movements or raise ERPConfigurationError."""
        ctx = await self._load_context(booking_id)

        if ctx.booking.erp_processed:
            logger.info(
                "Booking already processed by ERP, skipping",
                extra={"booking_id": str(booking_id)},
            )
            return

        cashbox = await self.finance_service.get_default_cashbox(ctx.booking.clinic_id)
        if not cashbox:
            raise ERPConfigurationError(
                code="missing_cashbox",
                message="No default cashbox configured for clinic",
            )

        role = getattr(ctx.doctor, "specialist_role", None)
        try:
            await self.payroll_service.calculate_and_create_salary_transaction(
                SalaryCalculationContext(
                    clinic_id=ctx.booking.clinic_id,
                    doctor_id=ctx.booking.doctor_id,
                    role=role,
                    services_amount=ctx.services_amount,
                    products_amount=ctx.products_amount,
                    period_start=ctx.period_start,
                    period_end=ctx.period_end,
                    booking_id=ctx.booking.id,
                )
            )
        except LookupError as exc:
            raise ERPConfigurationError(
                code="missing_payroll_policy",
                message=str(exc),
            ) from exc

        default_warehouse = await self.inventory_service.get_default_warehouse(
            ctx.booking.clinic_id
        )
        if default_warehouse is None:
            raise ERPConfigurationError(
                code="missing_warehouse",
                message="No default warehouse configured for clinic",
            )

        consumables = await self.inventory_service.list_service_consumables(
            clinic_id=ctx.booking.clinic_id,
            service_id=ctx.booking.service_id,
        )
        now = utc_now()
        for item in consumables:
            try:
                await self.inventory_service.register_movement(
                    InventoryMovementInput(
                        clinic_id=ctx.booking.clinic_id,
                        warehouse_id=default_warehouse.id,
                        product_id=item.product_id,
                        type="outgoing",
                        quantity=item.quantity_per_service,
                        happened_at=now,
                        description=f"Booking {ctx.booking.id} service consumable",
                        booking_id=ctx.booking.id,
                    )
                )
            except InsufficientStockError as exc:
                raise ERPConfigurationError(
                    code="insufficient_stock",
                    message=str(exc),
                ) from exc

        payment = None
        if ctx.booking.payment_id is not None:
            payment = await self.payment_repository.get_by_id(ctx.booking.payment_id)

        # Base amount for ERP:
        # - если есть внешний платёж, считаем выручку по нему;
        # - иначе используем цену услуги с учётом скидки от баллов кошелька.
        if payment is not None:
            amount = payment.amount
        else:
            effective_services = ctx.services_amount
            if ctx.wallet_spent_amount > 0:
                effective_services = max(
                    Decimal("0"),
                    ctx.services_amount - ctx.wallet_spent_amount,
                )
            amount = effective_services

        # Resolve marketing attribution (first-touch) for this booking based on patient/lead.
        visit_attr_id: UUID | None = None
        lead_id: UUID | None = None
        if ctx.booking.patient_id is not None:
            visit_stmt = (
                select(VisitAttribution)
                .where(
                    VisitAttribution.clinic_id == ctx.booking.clinic_id,
                    VisitAttribution.patient_id == ctx.booking.patient_id,
                )
                .order_by(VisitAttribution.created_at.asc())
                .limit(1)
            )
            visit_result = await self.session.execute(visit_stmt)
            visit = visit_result.scalar_one_or_none()
            if visit is not None:
                visit_attr_id = visit.id
                if visit.lead_id is not None:
                    lead_id = visit.lead_id

            if lead_id is None:
                lead_stmt = (
                    select(LeadCard)
                    .where(
                        LeadCard.clinic_id == ctx.booking.clinic_id,
                        LeadCard.patient_id == ctx.booking.patient_id,
                    )
                    .order_by(LeadCard.created_at.asc())
                    .limit(1)
                )
                lead_result = await self.session.execute(lead_stmt)
                lead = lead_result.scalar_one_or_none()
                if lead is not None:
                    lead_id = lead.id
                    if visit_attr_id is None and lead.visit_attribution_id is not None:
                        visit_attr_id = lead.visit_attribution_id

        await self.finance_service.create_transaction(
            CreateFinancialTransactionInput(
                clinic_id=ctx.booking.clinic_id,
                cashbox_id=cashbox.id,
                type="income",
                amount=amount,
                currency="RUB",
                happened_at=now,
                description=f"Income for completed booking {ctx.booking.id}",
                booking_id=ctx.booking.id,
                payment_id=payment.id if payment else None,
                lead_id=lead_id,
                visit_attribution_id=visit_attr_id,
                source="booking_completed",
            )
        )

        ctx.booking.erp_processed = True
        ctx.booking.erp_error_code = None
        await self.booking_repository.update(ctx.booking)

