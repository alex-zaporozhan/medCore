"""Reporting service for dashboard and analytics endpoints."""

from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.reports_dto import (
    DashboardReport,
    NoShowReport,
    OwnerDashboardReport,
    RevenuePoint,
    RevenueReport,
)
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.domain.entities.payment import Payment
from src.domain.entities.prepayment_transaction import PrepaymentTransaction
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.waitlist_entry import WaitlistEntry

DashboardPeriod = str  # "day" | "week" | "month"


class ReportsService:
    """Service providing aggregated reports over bookings and payments."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session

    async def _get_default_clinic(self) -> Clinic:
        """Get default clinic (single-clinic instance)."""
        result = await self.session.execute(select(Clinic).limit(1))
        clinic = result.scalar_one_or_none()
        if clinic is None:
            raise RuntimeError("No clinic configured for reports")
        return clinic

    async def _get_clinic(self, clinic_id: UUID | None) -> Clinic:
        """Resolve clinic by id or default."""
        if clinic_id is not None:
            result = await self.session.execute(select(Clinic).where(Clinic.id == clinic_id))
            clinic = result.scalar_one_or_none()
            if clinic is None:
                raise RuntimeError("Clinic not found")
            return clinic
        return await self._get_default_clinic()

    async def get_dashboard_report(self, day: date, clinic_id: UUID | None = None) -> DashboardReport:
        """Get dashboard metrics for a specific day."""
        clinic = await self._get_clinic(clinic_id)

        # Bookings by status for the day.
        result = await self.session.execute(
            select(Booking.status, func.count())
            .where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date == day,
                Booking.deleted_at.is_(None),
            )
            .group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        # New patients created that day.
        start_dt = datetime.combine(day, dtime.min)
        end_dt = start_dt + timedelta(days=1)
        result = await self.session.execute(
            select(func.count())
            .select_from(Patient)
            .where(
                Patient.clinic_id == clinic.id,
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
        )
        new_patients = int(result.scalar() or 0)

        # Revenue for the day:
        # - successful payments linked to bookings on that date
        # - plus prepayment_amount for completed bookings without external payment.
        payment_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.clinic_id == clinic.id,
                Payment.status == "succeeded",
                Booking.appointment_date == day,
                Booking.deleted_at.is_(None),
            )
        )
        payments_sum = Decimal(payment_result.scalar() or 0)

        prepay_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date == day,
                Booking.status == "completed",
                Booking.payment_id.is_(None),
                Booking.deleted_at.is_(None),
            )
        )
        prepay_sum = Decimal(prepay_result.scalar() or 0)

        revenue = payments_sum + prepay_sum

        return DashboardReport(
            date=day,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=int(counts.get("cancelled", 0)),
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
        )

    def _period_bounds(self, day: date, period: DashboardPeriod) -> tuple[date, date]:
        """Return (date_from, date_to) for the given period anchored on day."""
        if period == "day":
            return (day, day)
        if period == "week":
            # Week: 7 days starting on day
            return (day, day + timedelta(days=6))
        if period == "month":
            # Calendar month containing day
            first = date(day.year, day.month, 1)
            if day.month == 12:
                last = date(day.year, 12, 31)
            else:
                last = date(day.year, day.month + 1, 1) - timedelta(days=1)
            return (first, last)
        return (day, day)

    async def get_dashboard_report_period(
        self, day: date, period: DashboardPeriod = "day", clinic_id: UUID | None = None
    ) -> DashboardReport:
        """Get dashboard metrics for a day, week, or month (aggregated)."""
        date_from, date_to = self._period_bounds(day, period)
        clinic = await self._get_clinic(clinic_id)

        # Bookings by status in range
        result = await self.session.execute(
            select(Booking.status, func.count())
            .where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
            .group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        # New patients in range
        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)
        result = await self.session.execute(
            select(func.count())
            .select_from(Patient)
            .where(
                Patient.clinic_id == clinic.id,
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
        )
        new_patients = int(result.scalar() or 0)

        # Revenue in range
        payment_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.clinic_id == clinic.id,
                Payment.status == "succeeded",
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
        )
        payments_sum = Decimal(payment_result.scalar() or 0)
        prepay_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.status == "completed",
                Booking.payment_id.is_(None),
                Booking.deleted_at.is_(None),
            )
        )
        prepay_sum = Decimal(prepay_result.scalar() or 0)
        revenue = payments_sum + prepay_sum

        return DashboardReport(
            date=date_from,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=int(counts.get("cancelled", 0)),
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
        )

    async def get_no_show_report(
        self,
        date_from: date,
        date_to: date,
        clinic_id: UUID | None = None,
    ) -> NoShowReport:
        """Get no-show statistics for a period."""
        clinic = await self._get_clinic(clinic_id)

        # Consider bookings that reached a terminal state in the period.
        result = await self.session.execute(
            select(
                Booking.status,
                func.count(),
            ).where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
                Booking.status.in_(("completed", "cancelled", "no_show")),
            )
            .group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        total = int(sum(counts.values()))
        no_show_count = int(counts.get("no_show", 0))
        no_show_rate = float(no_show_count / total) if total > 0 else 0.0

        return NoShowReport(
            date_from=date_from,
            date_to=date_to,
            total=total,
            no_show_count=no_show_count,
            no_show_rate=no_show_rate,
        )

    async def get_revenue_report(
        self,
        date_from: date,
        date_to: date,
        clinic_id: UUID | None = None,
    ) -> RevenueReport:
        """Get revenue statistics and daily breakdown for a period."""
        clinic = await self._get_clinic(clinic_id)

        # Total from successful payments.
        payment_total_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.clinic_id == clinic.id,
                Payment.status == "succeeded",
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
        )
        payments_total = Decimal(payment_total_result.scalar() or 0)

        # Total from completed bookings without external payments.
        prepay_total_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.status == "completed",
                Booking.payment_id.is_(None),
                Booking.deleted_at.is_(None),
            )
        )
        prepay_total = Decimal(prepay_total_result.scalar() or 0)

        total_revenue = payments_total + prepay_total

        # Daily breakdown from payments.
        payment_daily_result = await self.session.execute(
            select(
                Booking.appointment_date,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.clinic_id == clinic.id,
                Payment.status == "succeeded",
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
            .group_by(Booking.appointment_date)
        )
        payment_daily = {
            day: Decimal(amount) for day, amount in payment_daily_result.all()
        }

        # Daily breakdown from completed bookings without external payments.
        prepay_daily_result = await self.session.execute(
            select(
                Booking.appointment_date,
                func.coalesce(func.sum(Booking.prepayment_amount), 0),
            )
            .where(
                Booking.clinic_id == clinic.id,
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.status == "completed",
                Booking.payment_id.is_(None),
                Booking.deleted_at.is_(None),
            )
            .group_by(Booking.appointment_date)
        )
        prepay_daily = {
            day: Decimal(amount) for day, amount in prepay_daily_result.all()
        }

        # Merge daily series.
        all_days: set[date] = set(payment_daily.keys()) | set(prepay_daily.keys())
        points: list[RevenuePoint] = []
        for day in sorted(all_days):
            amount = payment_daily.get(day, Decimal("0")) + prepay_daily.get(
                day, Decimal("0")
            )
            points.append(RevenuePoint(date=day, amount=amount))

        return RevenueReport(
            date_from=date_from,
            date_to=date_to,
            total_revenue=total_revenue,
            points=points,
        )

    async def get_owner_dashboard(
        self,
        clinic_id: UUID,
        day: date,
        date_from: date,
        date_to: date,
    ) -> OwnerDashboardReport:
        """Aggregated owner dashboard: dashboard, no_show rate, revenue, prepay/waitlist/recall counts."""
        clinic = await self._get_clinic(clinic_id)
        dashboard = await self.get_dashboard_report(day, clinic_id=clinic_id)
        no_show = await self.get_no_show_report(date_from, date_to, clinic_id=clinic_id)
        revenue_report = await self.get_revenue_report(date_from, date_to, clinic_id=clinic_id)

        prepay_count_result = await self.session.execute(
            select(func.count())
            .select_from(PrepaymentTransaction)
            .join(Booking, Booking.id == PrepaymentTransaction.booking_id)
            .where(
                Booking.clinic_id == clinic_id,
                PrepaymentTransaction.created_at >= datetime.combine(date_from, dtime.min),
                PrepaymentTransaction.created_at < datetime.combine(date_to, dtime.min) + timedelta(days=1),
            )
        )
        prepay_count = int(prepay_count_result.scalar() or 0)        waitlist_result = await self.session.execute(
            select(func.count()).select_from(WaitlistEntry).where(
                WaitlistEntry.clinic_id == clinic_id,
            )
        )
        waitlist_count = int(waitlist_result.scalar() or 0)
        recall_result = await self.session.execute(
            select(func.count()).select_from(RecallCampaign).where(
                RecallCampaign.clinic_id == clinic_id,
            )
        )
        recall_count = int(recall_result.scalar() or 0)

        return OwnerDashboardReport(
            clinic_id=str(clinic_id),
            dashboard=dashboard,
            no_show_rate=no_show.no_show_rate,
            total_revenue=revenue_report.total_revenue,
            prepayment_transactions_count=prepay_count,
            waitlist_entries_count=waitlist_count,
            recall_campaigns_count=recall_count,
        )
