from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.erp_loyalty_dto import (
    CreateObligationFromSaleInput,
    ErpLoyaltyObligationSnapshot,
    ErpLoyaltyWriteOffSummary,
    RegisterWriteOffForVisitInput,
)
from src.core.metrics import (
    erp_loyalty_obligations_created_total,
    erp_loyalty_write_off_amount_total,
    erp_loyalty_sync_errors_total,
)
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.erp_loyalty_obligation import (
    ErpLoyaltyObligation,
    ErpLoyaltyObligationMovement,
)


logger = logging.getLogger(__name__)


class ErpLoyaltyError(RuntimeError):
    """Base class for ERP loyalty obligation errors."""


@dataclass
class ErpLoyaltyService:
    """Service managing ERP-side obligations for loyalty subscriptions."""

    session: AsyncSession

    async def create_obligation_from_sale(
        self,
        data: CreateObligationFromSaleInput,
    ) -> ErpLoyaltyObligationSnapshot:
        """Create ERP loyalty obligation when subscription is purchased."""

        obligation_amount = self._compute_obligation_amount(
            kind=data.kind,
            price=data.package_price,
            total_visits=data.total_visits,
            total_amount=data.total_amount,
        )

        now = data.created_at

        obligation = ErpLoyaltyObligation(
            clinic_id=data.clinic_id,
            patient_id=data.patient_id,
            customer_subscription_id=data.customer_subscription_id,
            initial_amount=obligation_amount,
            remaining_amount=obligation_amount,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.session.add(obligation)
        await self.session.flush()

        # Metrics: count created obligations per clinic after successful flush.
        erp_loyalty_obligations_created_total.labels(
            clinic_bucket=clinic_bucket_label(obligation.clinic_id),
        ).inc()

        movement = ErpLoyaltyObligationMovement(
            obligation_id=obligation.id,
            clinic_id=data.clinic_id,
            booking_id=None,
            subscription_usage_id=None,
            movement_type="CREATE_FROM_SALE",
            amount_delta=obligation_amount,
            created_at=now,
        )
        self.session.add(movement)
        await self.session.flush()

        logger.info(
            "[ERP_LOYALTY] obligation created from sale",
            extra={
                "clinic_id": str(obligation.clinic_id),
                "patient_id": str(obligation.patient_id),
                "customer_subscription_id": str(obligation.customer_subscription_id),
                "obligation_id": str(obligation.id),
                "initial_amount": str(obligation.initial_amount),
            },
        )

        return ErpLoyaltyObligationSnapshot(
            id=obligation.id,
            clinic_id=obligation.clinic_id,
            patient_id=obligation.patient_id,
            customer_subscription_id=obligation.customer_subscription_id,
            initial_amount=obligation.initial_amount,
            remaining_amount=obligation.remaining_amount,
            status=obligation.status,
        )

    async def register_write_off_for_visit(
        self,
        data: RegisterWriteOffForVisitInput,
    ) -> ErpLoyaltyWriteOffSummary:
        """Register write-off on visit for existing obligation."""

        obligation = await self._load_obligation_for_subscription(
            clinic_id=data.clinic_id,
            subscription_id=data.customer_subscription_id,
        )
        if obligation is None:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(data.clinic_id),
                error_type="obligation_not_found",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] obligation not found for write-off",
                extra={
                    "clinic_id": str(data.clinic_id),
                    "customer_subscription_id": str(data.customer_subscription_id),
                    "booking_id": str(data.booking_id),
                },
            )
            raise ErpLoyaltyError("ERP loyalty obligation not found for subscription")

        if obligation.clinic_id != data.clinic_id:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(data.clinic_id),
                error_type="clinic_mismatch",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] clinic_id mismatch between obligation and write-off",
                extra={
                    "clinic_id": str(data.clinic_id),
                    "obligation_clinic_id": str(obligation.clinic_id),
                    "obligation_id": str(obligation.id),
                    "booking_id": str(data.booking_id),
                },
            )
            raise ErpLoyaltyError("clinic_id mismatch between obligation and write-off")

        write_off_amount = await self._compute_write_off_amount(
            subscription_id=data.customer_subscription_id,
            used_visits=data.used_visits,
            used_amount=data.used_amount,
        )

        if write_off_amount <= Decimal("0"):
            logger.info(
                "[ERP_LOYALTY] zero write-off amount",
                extra={
                    "clinic_id": str(data.clinic_id),
                    "booking_id": str(data.booking_id),
                    "customer_subscription_id": str(data.customer_subscription_id),
                    "obligation_id": str(obligation.id),
                },
            )
            return ErpLoyaltyWriteOffSummary(
                booking_id=data.booking_id,
                clinic_id=data.clinic_id,
                total_write_off_amount=Decimal("0"),
                obligation_ids=[obligation.id],
                remaining_amounts={obligation.id: obligation.remaining_amount},
                warnings=["zero_write_off_amount"],
            )

        if write_off_amount > obligation.remaining_amount:
            # Clamp to remaining amount but add warning about overspend attempt.
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(data.clinic_id),
                error_type="overspend_attempt",
            ).inc()
            logger.warning(
                "[ERP_LOYALTY] attempt to write off more than remaining amount",
                extra={
                    "clinic_id": str(data.clinic_id),
                    "booking_id": str(data.booking_id),
                    "customer_subscription_id": str(data.customer_subscription_id),
                    "obligation_id": str(obligation.id),
                    "requested_write_off": str(write_off_amount),
                    "remaining_amount": str(obligation.remaining_amount),
                },
            )
            write_off_amount = obligation.remaining_amount
            warning = "attempt_write_off_more_than_remaining"
        else:
            warning = ""

        obligation.remaining_amount -= write_off_amount
        if obligation.remaining_amount <= Decimal("0"):
            obligation.remaining_amount = Decimal("0")
            obligation.status = "settled"
        obligation.updated_at = data.happened_at
        await self.session.flush()

        movement = ErpLoyaltyObligationMovement(
            obligation_id=obligation.id,
            clinic_id=data.clinic_id,
            booking_id=data.booking_id,
            subscription_usage_id=data.subscription_usage_id,
            movement_type="WRITE_OFF_ON_VISIT",
            amount_delta=-write_off_amount,
            created_at=data.happened_at,
            beneficiary_patient_id=data.beneficiary_patient_id,
            family_link_id=data.family_link_id,
        )
        self.session.add(movement)
        await self.session.flush()

        # Metrics: total monetary write-off amount per clinic for successful movements.
        erp_loyalty_write_off_amount_total.labels(
            clinic_bucket=clinic_bucket_label(data.clinic_id),
        ).inc(float(write_off_amount))

        logger.info(
            "[ERP_LOYALTY] write-off on visit registered",
            extra={
                "clinic_id": str(data.clinic_id),
                "booking_id": str(data.booking_id),
                "customer_subscription_id": str(data.customer_subscription_id),
                "obligation_id": str(obligation.id),
                "write_off_amount": str(write_off_amount),
                "remaining_amount": str(obligation.remaining_amount),
                "beneficiary_patient_id": str(data.beneficiary_patient_id)
                if data.beneficiary_patient_id
                else None,
                "family_link_id": str(data.family_link_id)
                if data.family_link_id
                else None,
            },
        )

        warnings: list[str] = []
        if warning:
            warnings.append(warning)

        return ErpLoyaltyWriteOffSummary(
            booking_id=data.booking_id,
            clinic_id=data.clinic_id,
            total_write_off_amount=write_off_amount,
            obligation_ids=[obligation.id],
            remaining_amounts={obligation.id: obligation.remaining_amount},
            warnings=warnings,
        )

    async def register_refund(
        self,
        *,
        clinic_id: UUID,
        subscription_id: UUID,
        amount: Decimal,
        happened_at: datetime,
        booking_id: UUID | None = None,
        subscription_usage_id: UUID | None = None,
    ) -> ErpLoyaltyObligationSnapshot:
        """Register refund increasing remaining obligation amount."""

        if amount <= Decimal("0"):
            raise ErpLoyaltyError("refund amount must be positive")

        obligation = await self._load_obligation_for_subscription(
            clinic_id=clinic_id,
            subscription_id=subscription_id,
        )
        if obligation is None:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                error_type="obligation_not_found",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] obligation not found for refund",
                extra={
                    "clinic_id": str(clinic_id),
                    "subscription_id": str(subscription_id),
                    "booking_id": str(booking_id) if booking_id else None,
                },
            )
            raise ErpLoyaltyError("ERP loyalty obligation not found for subscription")
        if obligation.clinic_id != clinic_id:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                error_type="clinic_mismatch",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] clinic_id mismatch between obligation and refund",
                extra={
                    "clinic_id": str(clinic_id),
                    "obligation_clinic_id": str(obligation.clinic_id),
                    "obligation_id": str(obligation.id),
                },
            )
            raise ErpLoyaltyError("clinic_id mismatch between obligation and refund")

        obligation.remaining_amount += amount
        if obligation.remaining_amount > Decimal("0") and obligation.status == "settled":
            obligation.status = "active"
        obligation.updated_at = happened_at
        await self.session.flush()

        movement = ErpLoyaltyObligationMovement(
            obligation_id=obligation.id,
            clinic_id=clinic_id,
            booking_id=booking_id,
            subscription_usage_id=subscription_usage_id,
            movement_type="REFUND",
            amount_delta=amount,
            created_at=happened_at,
        )
        self.session.add(movement)
        await self.session.flush()

        logger.info(
            "[ERP_LOYALTY] refund registered",
            extra={
                "clinic_id": str(clinic_id),
                "subscription_id": str(subscription_id),
                "obligation_id": str(obligation.id),
                "amount": str(amount),
                "remaining_amount": str(obligation.remaining_amount),
            },
        )

        return ErpLoyaltyObligationSnapshot(
            id=obligation.id,
            clinic_id=obligation.clinic_id,
            patient_id=obligation.patient_id,
            customer_subscription_id=obligation.customer_subscription_id,
            initial_amount=obligation.initial_amount,
            remaining_amount=obligation.remaining_amount,
            status=obligation.status,
        )

    async def register_adjustment(
        self,
        *,
        clinic_id: UUID,
        subscription_id: UUID,
        amount_delta: Decimal,
        happened_at: datetime,
        booking_id: UUID | None = None,
        subscription_usage_id: UUID | None = None,
    ) -> ErpLoyaltyObligationSnapshot:
        """Register manual adjustment on obligation remaining amount."""

        if amount_delta == Decimal("0"):
            return await self._snapshot_for_subscription(
                clinic_id=clinic_id,
                subscription_id=subscription_id,
            )

        obligation = await self._load_obligation_for_subscription(
            clinic_id=clinic_id,
            subscription_id=subscription_id,
        )
        if obligation is None:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                error_type="obligation_not_found",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] obligation not found for adjustment",
                extra={
                    "clinic_id": str(clinic_id),
                    "subscription_id": str(subscription_id),
                },
            )
            raise ErpLoyaltyError("ERP loyalty obligation not found for subscription")
        if obligation.clinic_id != clinic_id:
            erp_loyalty_sync_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                error_type="clinic_mismatch",
            ).inc()
            logger.error(
                "[ERP_LOYALTY] clinic_id mismatch between obligation and adjustment",
                extra={
                    "clinic_id": str(clinic_id),
                    "obligation_clinic_id": str(obligation.clinic_id),
                    "obligation_id": str(obligation.id),
                },
            )
            raise ErpLoyaltyError("clinic_id mismatch between obligation and adjustment")

        new_remaining = obligation.remaining_amount + amount_delta
        if new_remaining < Decimal("0"):
            new_remaining = Decimal("0")

        obligation.remaining_amount = new_remaining
        obligation.status = "settled" if obligation.remaining_amount == Decimal("0") else "active"
        obligation.updated_at = happened_at
        await self.session.flush()

        movement = ErpLoyaltyObligationMovement(
            obligation_id=obligation.id,
            clinic_id=clinic_id,
            booking_id=booking_id,
            subscription_usage_id=subscription_usage_id,
            movement_type="ADJUSTMENT",
            amount_delta=amount_delta,
            created_at=happened_at,
        )
        self.session.add(movement)
        await self.session.flush()

        logger.info(
            "[ERP_LOYALTY] adjustment registered",
            extra={
                "clinic_id": str(clinic_id),
                "subscription_id": str(subscription_id),
                "obligation_id": str(obligation.id),
                "amount_delta": str(amount_delta),
                "remaining_amount": str(obligation.remaining_amount),
            },
        )

        return ErpLoyaltyObligationSnapshot(
            id=obligation.id,
            clinic_id=obligation.clinic_id,
            patient_id=obligation.patient_id,
            customer_subscription_id=obligation.customer_subscription_id,
            initial_amount=obligation.initial_amount,
            remaining_amount=obligation.remaining_amount,
            status=obligation.status,
        )

    def _compute_obligation_amount(
        self,
        *,
        kind: str,
        price: Decimal,
        total_visits: int | None,
        total_amount: Decimal | None,
    ) -> Decimal:
        """Derive monetary obligation from subscription package parameters."""

        if kind in ("COUNT_BASED", "visits"):
            if not total_visits or total_visits <= 0:
                raise ErpLoyaltyError(
                    "total_visits must be positive for COUNT_BASED subscription"
                )
            return price

        if kind in ("BALANCE_BASED", "balance"):
            if total_amount is None or total_amount <= Decimal("0"):
                raise ErpLoyaltyError(
                    "total_amount must be positive for BALANCE_BASED subscription"
                )
            return total_amount

        # Fallback for mixed/other kinds: use price as obligation.
        return price

    async def _load_obligation_for_subscription(
        self,
        *,
        clinic_id: UUID,
        subscription_id: UUID,
    ) -> ErpLoyaltyObligation | None:
        stmt = select(ErpLoyaltyObligation).where(
            ErpLoyaltyObligation.clinic_id == clinic_id,
            ErpLoyaltyObligation.customer_subscription_id == subscription_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _snapshot_for_subscription(
        self,
        *,
        clinic_id: UUID,
        subscription_id: UUID,
    ) -> ErpLoyaltyObligationSnapshot:
        obligation = await self._load_obligation_for_subscription(
            clinic_id=clinic_id,
            subscription_id=subscription_id,
        )
        if obligation is None:
            raise ErpLoyaltyError("ERP loyalty obligation not found for subscription")
        return ErpLoyaltyObligationSnapshot(
            id=obligation.id,
            clinic_id=obligation.clinic_id,
            patient_id=obligation.patient_id,
            customer_subscription_id=obligation.customer_subscription_id,
            initial_amount=obligation.initial_amount,
            remaining_amount=obligation.remaining_amount,
            status=obligation.status,
        )

    async def _compute_write_off_amount(
        self,
        *,
        subscription_id: UUID,
        used_visits: int | None,
        used_amount: Decimal | None,
    ) -> Decimal:
        """Convert Loyalty usage (visits/amount) into ERP monetary write-off."""

        if used_amount is not None:
            return used_amount

        if used_visits is None or used_visits <= 0:
            return Decimal("0")

        # Fallback: approximate 1 visit price based on subscription package price/total_visits.
        stmt = select(CustomerSubscription).where(
            CustomerSubscription.id == subscription_id
        )
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub is None:
            return Decimal("0")

        # We only have remaining_visits/remaining_amount; approximate from remaining_amount when present.
        if sub.remaining_visits and sub.remaining_visits > 0 and sub.remaining_amount:
            per_visit = sub.remaining_amount / Decimal(sub.remaining_visits)
            return per_visit * Decimal(used_visits)

        return Decimal("0")

