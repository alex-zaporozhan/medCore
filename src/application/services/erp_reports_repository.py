from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.booking import Booking
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.entities.visit_attribution import VisitAttribution


def _normalize_period(date_from: date, date_to: date) -> tuple[date, date]:
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _income_transactions_for_clinic(clinic_id: UUID):
    """Shared filter: ERP income rows for a clinic (same definition as visit-revenue reports)."""
    return and_(
        FinancialTransaction.clinic_id == clinic_id,
        FinancialTransaction.type == "income",
    )


@dataclass
class ErpVisitRevenueView:
    clinic_id: UUID
    visit_date: date
    booking_id: UUID | None
    total_revenue: Decimal


@dataclass
class ErpVisitPayrollView:
    clinic_id: UUID
    doctor_id: UUID
    booking_id: UUID | None
    period_start: date | None
    period_end: date | None
    amount: Decimal


@dataclass
class ErpVisitInventoryView:
    clinic_id: UUID
    product_id: UUID
    booking_id: UUID | None
    total_quantity: Decimal


@dataclass
class ErpVisitInventoryDailyView:
    """Per-day inventory grain for L2 vitrine (sums to period totals)."""

    clinic_id: UUID
    movement_date: date
    product_id: UUID
    booking_id: UUID | None
    quantity_day: Decimal


@dataclass
class ErpLoyaltyObligationsView:
    clinic_id: UUID
    patient_id: UUID | None
    total_obligations_amount: Decimal


@dataclass
class ErpAttributionRevenueView:
    clinic_id: UUID
    visit_date: date
    traffic_source_id: UUID | None
    campaign_id: UUID | None
    total_revenue: Decimal


class ErpReportsRepository:
    """ORM-based repository for ERP reporting views.

    This repository aggregates data from ERP registries (finance, payroll,
    inventory, loyalty, attribution) without reimplementing business logic
    of the ERP node. It is a thin read-only layer, intended to be swapped
    to SQL views/materialized views in future iterations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_visit_revenue_by_period(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitRevenueView]:
        """Aggregate revenue per visit date using FinancialTransaction.

        v1 approximation: sum of income-type financial_transactions linked to bookings
        for the given clinic in [date_from, date_to].
        """
        date_from, date_to = _normalize_period(date_from, date_to)

        # We approximate "visit date" by Booking.appointment_date when booking_id is present,
        # and by financial_transaction.happened_at.date when not.
        tx_stmt: Select = (
            select(
                FinancialTransaction.clinic_id,
                func.coalesce(Booking.appointment_date, func.date(FinancialTransaction.happened_at)).label(
                    "visit_date"
                ),
                FinancialTransaction.booking_id,
                func.coalesce(func.sum(FinancialTransaction.amount), 0).label("total_amount"),
            )
            .join(
                Booking,
                Booking.id == FinancialTransaction.booking_id,
                isouter=True,
            )
            .where(
                _income_transactions_for_clinic(clinic_id),
                FinancialTransaction.happened_at >= datetime.combine(date_from, datetime.min.time()),
                FinancialTransaction.happened_at
                < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(
                FinancialTransaction.clinic_id,
                "visit_date",
                FinancialTransaction.booking_id,
            )
            .order_by("visit_date")
        )

        result = await self.session.execute(tx_stmt)
        rows: Iterable[tuple[UUID, date, UUID | None, Decimal]] = result.all()

        return [
            ErpVisitRevenueView(
                clinic_id=row[0],
                visit_date=row[1],
                booking_id=row[2],
                total_revenue=Decimal(row[3] or 0),
            )
            for row in rows
        ]

    async def sum_income_revenue_for_crm_lead(
        self,
        *,
        clinic_id: UUID,
        lead_id: UUID,
        booking_ids: list[UUID],
    ) -> Decimal:
        """Sum ERP income linked to a CRM lead (source of truth for ``LeadCard.actual_value``).

        Uses the same income-row definition as ``get_visit_revenue_by_period`` (``type == income``),
        without a date window — all matching rows for the lead/booking keys.

        Aggregates where either ``lead_id`` matches (multi-visit / ERP-posted rows) or
        ``booking_id`` is in ``booking_ids`` (primary visit and event-scoped bookings).
        """
        or_parts = [FinancialTransaction.lead_id == lead_id]
        if booking_ids:
            or_parts.append(FinancialTransaction.booking_id.in_(booking_ids))
        stmt = select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(
            and_(
                _income_transactions_for_clinic(clinic_id),
                or_(*or_parts),
            )
        )
        result = await self.session.execute(stmt)
        raw = result.scalar_one()
        return Decimal(str(raw or 0))

    async def get_visit_payroll_by_period(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitPayrollView]:
        """Aggregate salary movements for visits in period.

        v1: group by doctor and booking within requested period, based on
        salary_transactions.period_start/period_end and booking link.
        """
        date_from, date_to = _normalize_period(date_from, date_to)

        stmt: Select = (
            select(
                SalaryTransaction.clinic_id,
                SalaryTransaction.doctor_id,
                SalaryTransaction.booking_id,
                SalaryTransaction.period_start,
                SalaryTransaction.period_end,
                func.coalesce(func.sum(SalaryTransaction.amount), 0).label("total_amount"),
            )
            .where(
                SalaryTransaction.clinic_id == clinic_id,
                # Simple overlap check with [date_from, date_to]
                SalaryTransaction.period_start <= date_to,
                SalaryTransaction.period_end >= date_from,
            )
            .group_by(
                SalaryTransaction.clinic_id,
                SalaryTransaction.doctor_id,
                SalaryTransaction.booking_id,
                SalaryTransaction.period_start,
                SalaryTransaction.period_end,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            ErpVisitPayrollView(
                clinic_id=row[0],
                doctor_id=row[1],
                booking_id=row[2],
                period_start=row[3],
                period_end=row[4],
                amount=Decimal(row[5] or 0),
            )
            for row in rows
        ]

    async def get_visit_inventory_by_period(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitInventoryView]:
        """Aggregate inventory movements per product and optionally booking."""
        date_from, date_to = _normalize_period(date_from, date_to)

        stmt: Select = (
            select(
                InventoryTransaction.clinic_id,
                InventoryTransaction.product_id,
                InventoryTransaction.booking_id,
                func.coalesce(func.sum(InventoryTransaction.quantity), 0).label("total_quantity"),
            )
            .where(
                InventoryTransaction.clinic_id == clinic_id,
                InventoryTransaction.happened_at
                >= datetime.combine(date_from, datetime.min.time()),
                InventoryTransaction.happened_at
                < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(
                InventoryTransaction.clinic_id,
                InventoryTransaction.product_id,
                InventoryTransaction.booking_id,
            )
            .order_by(
                InventoryTransaction.product_id.asc(),
                InventoryTransaction.booking_id.asc().nulls_last(),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            ErpVisitInventoryView(
                clinic_id=row[0],
                product_id=row[1],
                booking_id=row[2],
                total_quantity=Decimal(row[3] or 0),
            )
            for row in rows
        ]

    async def get_visit_inventory_daily_by_period(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpVisitInventoryDailyView]:
        """Aggregate inventory by calendar day (same filters as ``get_visit_inventory_by_period``)."""
        date_from, date_to = _normalize_period(date_from, date_to)

        stmt: Select = (
            select(
                InventoryTransaction.clinic_id,
                func.date(InventoryTransaction.happened_at).label("movement_date"),
                InventoryTransaction.product_id,
                InventoryTransaction.booking_id,
                func.coalesce(func.sum(InventoryTransaction.quantity), 0).label("total_quantity"),
            )
            .where(
                InventoryTransaction.clinic_id == clinic_id,
                InventoryTransaction.happened_at
                >= datetime.combine(date_from, datetime.min.time()),
                InventoryTransaction.happened_at
                < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(
                InventoryTransaction.clinic_id,
                "movement_date",
                InventoryTransaction.product_id,
                InventoryTransaction.booking_id,
            )
            .order_by(
                "movement_date",
                InventoryTransaction.product_id.asc(),
                InventoryTransaction.booking_id.asc().nulls_last(),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            ErpVisitInventoryDailyView(
                clinic_id=row[0],
                movement_date=row[1],
                product_id=row[2],
                booking_id=row[3],
                quantity_day=Decimal(row[4] or 0),
            )
            for row in rows
        ]

    async def get_loyalty_obligations_snapshot(
        self,
        *,
        clinic_id: UUID,
        as_of: date | None = None,
    ) -> list[ErpLoyaltyObligationsView]:
        """Current snapshot of loyalty obligations per patient for clinic.

        v1: simple aggregation over ErpLoyaltyObligation by clinic_id and patient_id.
        """
        from src.domain.entities.erp_loyalty_obligation import ErpLoyaltyObligation

        stmt: Select = (
            select(
                ErpLoyaltyObligation.clinic_id,
                ErpLoyaltyObligation.patient_id,
                func.coalesce(func.sum(ErpLoyaltyObligation.remaining_amount), 0).label(
                    "remaining_total"
                ),
            )
            .where(ErpLoyaltyObligation.clinic_id == clinic_id)
            .group_by(
                ErpLoyaltyObligation.clinic_id,
                ErpLoyaltyObligation.patient_id,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            ErpLoyaltyObligationsView(
                clinic_id=row[0],
                patient_id=row[1],
                total_obligations_amount=Decimal(row[2] or 0),
            )
            for row in rows
        ]

    async def get_attribution_revenue_by_period(
        self,
        *,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[ErpAttributionRevenueView]:
        """Aggregate revenue by traffic source/campaign for period.

        v1: use FinancialTransaction linked to VisitAttribution via visit_attribution_id.
        """
        date_from, date_to = _normalize_period(date_from, date_to)

        stmt: Select = (
            select(
                FinancialTransaction.clinic_id,
                func.date(FinancialTransaction.happened_at).label("visit_date"),
                VisitAttribution.traffic_source_id,
                VisitAttribution.campaign_id,
                func.coalesce(func.sum(FinancialTransaction.amount), 0).label("total_amount"),
            )
            .join(
                VisitAttribution,
                VisitAttribution.id == FinancialTransaction.visit_attribution_id,
                isouter=True,
            )
            .where(
                FinancialTransaction.clinic_id == clinic_id,
                FinancialTransaction.type == "income",
                FinancialTransaction.happened_at
                >= datetime.combine(date_from, datetime.min.time()),
                FinancialTransaction.happened_at
                < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(
                FinancialTransaction.clinic_id,
                "visit_date",
                VisitAttribution.traffic_source_id,
                VisitAttribution.campaign_id,
            )
            .order_by(
                "visit_date",
                VisitAttribution.traffic_source_id.asc().nulls_last(),
                VisitAttribution.campaign_id.asc().nulls_last(),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            ErpAttributionRevenueView(
                clinic_id=row[0],
                visit_date=row[1],
                traffic_source_id=row[2],
                campaign_id=row[3],
                total_revenue=Decimal(row[4] or 0),
            )
            for row in rows
        ]

