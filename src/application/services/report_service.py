"""Reporting service for dashboard and analytics endpoints."""

from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.reports_dto import (
    CrmFunnelReport,
    CrmFunnelStageSummary,
    DashboardReport,
    NoShowReport,
    OwnerDashboardReport,
    PatientLtvItem,
    PatientLtvReport,
    RevenuePoint,
    RevenueReport,
)
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.payment import Payment
from src.domain.entities.prepayment_transaction import PrepaymentTransaction
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.waitlist_entry import WaitlistEntry
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.entities.wallet_transaction import WalletTransaction

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

        cancellations = int(counts.get("cancelled", 0))
        new_leads = await self._count_new_leads(day, day, clinic_ids=[clinic.id])
        return DashboardReport(
            date=day,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=cancellations,
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
            new_leads_count=new_leads,
            cancellations_count=cancellations,
            nps_avg=None,
        )

    async def get_dashboard_report_all_clinics(self, day: date) -> DashboardReport:
        """Dashboard metrics for a specific day, aggregated over all clinics."""
        return await self.get_dashboard_report_by_clinic_ids(day, clinic_ids=None)

    async def get_dashboard_report_by_clinic_ids(
        self, day: date, clinic_ids: list[UUID] | None = None
    ) -> DashboardReport:
        """Dashboard metrics for a day, optionally filtered by clinic IDs. None/empty = all clinics."""
        booking_filter = (
            (Booking.appointment_date == day, Booking.deleted_at.is_(None))
            if not clinic_ids
            else (
                Booking.clinic_id.in_(clinic_ids),
                Booking.appointment_date == day,
                Booking.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(
            select(Booking.status, func.count()).where(*booking_filter).group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        start_dt = datetime.combine(day, dtime.min)
        end_dt = start_dt + timedelta(days=1)
        patient_filter = (
            (Patient.created_at >= start_dt, Patient.created_at < end_dt, Patient.deleted_at.is_(None))
            if not clinic_ids
            else (
                Patient.clinic_id.in_(clinic_ids),
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(
            select(func.count()).select_from(Patient).where(*patient_filter)
        )
        new_patients = int(result.scalar() or 0)

        pay_join = (
            Payment.status == "succeeded",
            Booking.appointment_date == day,
            Booking.deleted_at.is_(None),
        )
        if clinic_ids:
            pay_join = (Payment.clinic_id.in_(clinic_ids),) + pay_join
        payment_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(*pay_join)
        )
        payments_sum = Decimal(payment_result.scalar() or 0)

        prepay_filter = (
            Booking.appointment_date == day,
            Booking.status == "completed",
            Booking.payment_id.is_(None),
            Booking.deleted_at.is_(None),
        )
        if clinic_ids:
            prepay_filter = (Booking.clinic_id.in_(clinic_ids),) + prepay_filter
        prepay_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(*prepay_filter)
        )
        prepay_sum = Decimal(prepay_result.scalar() or 0)
        revenue = payments_sum + prepay_sum

        cancellations = int(counts.get("cancelled", 0))
        new_leads = await self._count_new_leads(day, day, clinic_ids=clinic_ids)
        return DashboardReport(
            date=day,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=cancellations,
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
            new_leads_count=new_leads,
            cancellations_count=cancellations,
            nps_avg=None,
        )

    async def _count_new_leads(
        self,
        date_from: date,
        date_to: date,
        clinic_ids: list[UUID] | None,
    ) -> int:
        """Count LeadCard created in [date_from, date_to] for given clinics (or all)."""
        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)
        stmt = select(func.count()).select_from(LeadCard).where(
            LeadCard.created_at >= start_dt,
            LeadCard.created_at < end_dt,
        )
        if clinic_ids:
            stmt = stmt.where(LeadCard.clinic_id.in_(clinic_ids))
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

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

        cancellations = int(counts.get("cancelled", 0))
        new_leads = await self._count_new_leads(date_from, date_to, clinic_ids=[clinic.id])
        return DashboardReport(
            date=date_from,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=cancellations,
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
            new_leads_count=new_leads,
            cancellations_count=cancellations,
            nps_avg=None,
        )

    async def get_dashboard_report_period_all_clinics(
        self, day: date, period: DashboardPeriod = "day"
    ) -> DashboardReport:
        """Dashboard metrics for a period, aggregated over all clinics."""
        date_from, date_to = self._period_bounds(day, period)

        result = await self.session.execute(
            select(Booking.status, func.count())
            .where(
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
            .group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)
        result = await self.session.execute(
            select(func.count())
            .select_from(Patient)
            .where(
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
        )
        new_patients = int(result.scalar() or 0)

        payment_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.status == "succeeded",
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
        )
        payments_sum = Decimal(payment_result.scalar() or 0)
        prepay_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.status == "completed",
                Booking.payment_id.is_(None),
                Booking.deleted_at.is_(None),
            )
        )
        prepay_sum = Decimal(prepay_result.scalar() or 0)
        revenue = payments_sum + prepay_sum

        cancellations = int(counts.get("cancelled", 0))
        new_leads = await self._count_new_leads(date_from, date_to, clinic_ids=None)
        return DashboardReport(
            date=date_from,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=cancellations,
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
            new_leads_count=new_leads,
            cancellations_count=cancellations,
            nps_avg=None,
        )

    async def get_dashboard_report_period_by_clinic_ids(
        self, day: date, period: DashboardPeriod = "day", clinic_ids: list[UUID] | None = None
    ) -> DashboardReport:
        """Dashboard metrics for a period, optionally filtered by clinic IDs. None/empty = all."""
        date_from, date_to = self._period_bounds(day, period)

        booking_filter = (
            (
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
            if not clinic_ids
            else (
                Booking.clinic_id.in_(clinic_ids),
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(
            select(Booking.status, func.count()).where(*booking_filter).group_by(Booking.status)
        )
        counts = {status: count for status, count in result.all()}

        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)
        patient_filter = (
            (
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
            if not clinic_ids
            else (
                Patient.clinic_id.in_(clinic_ids),
                Patient.created_at >= start_dt,
                Patient.created_at < end_dt,
                Patient.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(
            select(func.count()).select_from(Patient).where(*patient_filter)
        )
        new_patients = int(result.scalar() or 0)

        pay_join = (
            Payment.status == "succeeded",
            Booking.appointment_date >= date_from,
            Booking.appointment_date <= date_to,
            Booking.deleted_at.is_(None),
        )
        if clinic_ids:
            pay_join = (Payment.clinic_id.in_(clinic_ids),) + pay_join
        payment_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(*pay_join)
        )
        payments_sum = Decimal(payment_result.scalar() or 0)
        prepay_filter = (
            Booking.appointment_date >= date_from,
            Booking.appointment_date <= date_to,
            Booking.status == "completed",
            Booking.payment_id.is_(None),
            Booking.deleted_at.is_(None),
        )
        if clinic_ids:
            prepay_filter = (Booking.clinic_id.in_(clinic_ids),) + prepay_filter
        prepay_result = await self.session.execute(
            select(func.coalesce(func.sum(Booking.prepayment_amount), 0)).where(*prepay_filter)
        )
        prepay_sum = Decimal(prepay_result.scalar() or 0)
        revenue = payments_sum + prepay_sum

        cancellations = int(counts.get("cancelled", 0))
        new_leads = await self._count_new_leads(date_from, date_to, clinic_ids=clinic_ids)
        return DashboardReport(
            date=date_from,
            bookings_pending=int(counts.get("pending", 0)),
            bookings_confirmed=int(counts.get("confirmed", 0)),
            bookings_completed=int(counts.get("completed", 0)),
            bookings_cancelled=cancellations,
            bookings_no_show=int(counts.get("no_show", 0)),
            new_patients=new_patients,
            revenue=revenue,
            new_leads_count=new_leads,
            cancellations_count=cancellations,
            nps_avg=None,
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
        prepay_count = int(prepay_count_result.scalar() or 0)
        waitlist_result = await self.session.execute(
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

    async def get_crm_funnel_report(
        self,
        clinic_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CrmFunnelReport:
        """Aggregate CRM funnel by stage: leads count and money on each stage."""
        await self._get_clinic(clinic_id)

        stmt = (
            select(
                LeadCard.stage_id,
                func.coalesce(func.count(LeadCard.id), 0),
                func.coalesce(func.sum(LeadCard.estimated_value), 0),
                func.coalesce(func.sum(LeadCard.actual_value), 0),
            )
            .where(LeadCard.clinic_id == clinic_id)
        )
        if date_from is not None:
            stmt = stmt.where(LeadCard.created_at >= datetime.combine(date_from, dtime.min))
        if date_to is not None:
            stmt = stmt.where(
                LeadCard.created_at < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )
        stmt = stmt.group_by(LeadCard.stage_id)

        result = await self.session.execute(stmt)
        rows = result.all()
        stage_ids = [row[0] for row in rows if row[0] is not None]

        stage_names: dict[UUID, str] = {}
        if stage_ids:
            stage_result = await self.session.execute(
                select(LeadStage.id, LeadStage.name).where(
                    LeadStage.id.in_(stage_ids),
                    LeadStage.clinic_id == clinic_id,
                )
            )
            stage_names = {sid: name for sid, name in stage_result.all()}

        stages: list[CrmFunnelStageSummary] = []
        total_estimated = Decimal("0")
        total_actual = Decimal("0")
        for stage_id, count, est_sum, act_sum in rows:
            est = Decimal(est_sum or 0)
            act = Decimal(act_sum or 0)
            total_estimated += est
            total_actual += act
            stages.append(
                CrmFunnelStageSummary(
                    stage_id=str(stage_id),
                    stage_name=stage_names.get(stage_id),
                    leads_count=int(count or 0),
                    estimated_sum=est,
                    actual_sum=act,
                )
            )

        return CrmFunnelReport(
            clinic_id=str(clinic_id),
            date_from=date_from,
            date_to=date_to,
            stages=stages,
            total_estimated=total_estimated,
            total_actual=total_actual,
        )

    async def get_patient_ltv_report(
        self,
        clinic_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        min_ltv: Decimal | None = None,
        limit: int = 200,
    ) -> PatientLtvReport:
        """Compute per-patient LTV based on successful CRM leads.

        LTV here is defined as the sum of LeadCard.actual_value for all successful
        leads per patient. ERP/Finance is responsible for ensuring that actual_value
        already accounts for both one-off payments and subscription/loyalty flows
        without double-counting visits paid from packages or points.
        """
        await self._get_clinic(clinic_id)
        limit = max(1, min(limit, 1000))

        stmt = (
            select(
                Patient.id,
                Patient.full_name,
                Patient.phone,
                func.coalesce(func.sum(LeadCard.actual_value), 0),
                func.count(LeadCard.id),
            )
            .join(LeadCard, LeadCard.patient_id == Patient.id)
            .where(
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
                LeadCard.clinic_id == clinic_id,
                LeadCard.status == "success",
            )
        )
        if date_from is not None:
            stmt = stmt.where(
                LeadCard.closed_at >= datetime.combine(date_from, dtime.min)
            )
        if date_to is not None:
            stmt = stmt.where(
                LeadCard.closed_at
                < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )

        stmt = stmt.group_by(Patient.id, Patient.full_name, Patient.phone)

        if min_ltv is not None:
            stmt = stmt.having(func.coalesce(func.sum(LeadCard.actual_value), 0) >= min_ltv)

        stmt = stmt.order_by(func.coalesce(func.sum(LeadCard.actual_value), 0).desc()).limit(limit)

        result = await self.session.execute(stmt)
        rows = result.all()

        items: list[PatientLtvItem] = []
        total_ltv = Decimal("0")
        for patient_id, full_name, phone, ltv_sum, leads_count in rows:
            ltv = Decimal(ltv_sum or 0)
            total_ltv += ltv
            items.append(
                PatientLtvItem(
                    patient_id=str(patient_id),
                    full_name=full_name,
                    phone=phone,
                    ltv_total=ltv,
                    successful_leads_count=int(leads_count or 0),
                )
            )

        total_patients = len(items)
        average_ltv = total_ltv / total_patients if total_patients > 0 else Decimal("0")

        return PatientLtvReport(
            clinic_id=str(clinic_id),
            date_from=date_from,
            date_to=date_to,
            items=items,
            total_patients=total_patients,
            average_ltv=average_ltv,
        )

    async def get_loyalty_summary(
        self,
        clinic_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Aggregate basic loyalty KPIs for owner/analytics dashboards.

        Metrics (do NOT change ERP revenue, only describe loyalty footprint):
        - total_subscriptions: count of CustomerSubscription in clinic;
        - active_subscriptions: count of active CustomerSubscription;
        - expired_subscriptions: count of subscriptions with non-active status;
        - active_with_balance: subscriptions with remaining_visits/amount > 0;
        - wallet_holders: patients with WalletTransaction history;
        - wallet_positive_balance: wallets with positive balance (approximated via tx sum);
        - subscription_usages_count: count of SubscriptionUsage records in period;
        - subscription_covered_amount: total used_amount from SubscriptionUsage in period;
        - wallet_earn_count / wallet_spend_count: counts of wallet earn/spend tx in period;
        - wallet_spend_amount: total amount of wallet spend tx in period.
        """
        await self._get_clinic(clinic_id)

        subs_stmt = select(
            func.count().label("total"),
            func.sum(
                func.case(
                    (CustomerSubscription.status == "active", 1),
                    else_=0,
                )
            ).label("active"),
            func.sum(
                func.case(
                    (CustomerSubscription.status != "active", 1),
                    else_=0,
                )
            ).label("expired"),
            func.sum(
                func.case(
                    (
                        (
                            (CustomerSubscription.remaining_visits.is_not(None))
                            & (CustomerSubscription.remaining_visits > 0)
                        )
                        | (
                            (CustomerSubscription.remaining_amount.is_not(None))
                            & (CustomerSubscription.remaining_amount > 0)
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("active_with_balance"),
        ).where(CustomerSubscription.clinic_id == clinic_id)
        subs_result = await self.session.execute(subs_stmt)
        subs_row = subs_result.one()

        # Wallet holders and positive balances approximated by tx history
        base_wallet_tx_stmt = select(
            WalletTransaction.wallet_id,
            WalletTransaction.type,
            WalletTransaction.amount,
        ).where(WalletTransaction.clinic_id == clinic_id)
        if date_from is not None:
            base_wallet_tx_stmt = base_wallet_tx_stmt.where(
                WalletTransaction.happened_at >= datetime.combine(date_from, dtime.min)
            )
        if date_to is not None:
            base_wallet_tx_stmt = base_wallet_tx_stmt.where(
                WalletTransaction.happened_at
                < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )
        wallet_tx_result = await self.session.execute(base_wallet_tx_stmt)
        wallet_rows = wallet_tx_result.all()
        wallet_ids = {row[0] for row in wallet_rows}

        positive_balance_wallets: set[UUID] = set()
        balances: dict[UUID, Decimal] = {}
        for wid, tx_type, amount in wallet_rows:
            if wid is None:
                continue
            current = balances.get(wid, Decimal("0"))
            if tx_type == "earn":
                current += Decimal(amount or 0)
            else:
                current -= Decimal(amount or 0)
            balances[wid] = current
        for wid, bal in balances.items():
            if bal > 0:
                positive_balance_wallets.add(wid)

        # Subscription usage and wallet tx counts in period
        usage_stmt = select(
            func.count().label("cnt"),
            func.coalesce(func.sum(SubscriptionUsage.used_amount), 0).label("amount"),
        ).where(SubscriptionUsage.clinic_id == clinic_id)
        if date_from is not None:
            usage_stmt = usage_stmt.where(
                SubscriptionUsage.used_at >= datetime.combine(date_from, dtime.min)
            )
        if date_to is not None:
            usage_stmt = usage_stmt.where(
                SubscriptionUsage.used_at
                < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )
        usage_result = await self.session.execute(usage_stmt)
        usage_row = usage_result.one()
        subscription_usages_count = int(usage_row.cnt or 0)
        subscription_covered_amount = Decimal(usage_row.amount or 0)

        earn_stmt = select(func.count()).select_from(WalletTransaction).where(
            WalletTransaction.clinic_id == clinic_id,
            WalletTransaction.type == "earn",
        )
        spend_stmt = select(
            func.count().label("cnt"),
            func.coalesce(func.sum(WalletTransaction.amount), 0).label("amount"),
        ).where(
            WalletTransaction.clinic_id == clinic_id,
            WalletTransaction.type == "spend",
        )
        if date_from is not None:
            earn_stmt = earn_stmt.where(
                WalletTransaction.happened_at >= datetime.combine(date_from, dtime.min)
            )
            spend_stmt = spend_stmt.where(
                WalletTransaction.happened_at >= datetime.combine(date_from, dtime.min)
            )
        if date_to is not None:
            earn_stmt = earn_stmt.where(
                WalletTransaction.happened_at
                < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )
            spend_stmt = spend_stmt.where(
                WalletTransaction.happened_at
                < datetime.combine(date_to, dtime.min) + timedelta(days=1)
            )
        earn_result = await self.session.execute(earn_stmt)
        spend_result = await self.session.execute(spend_stmt)
        wallet_earn_count = int(earn_result.scalar() or 0)
        spend_row = spend_result.one()
        wallet_spend_count = int(spend_row.cnt or 0)
        wallet_spend_amount = Decimal(spend_row.amount or 0)

        return {
            "total_subscriptions": int(subs_row.total or 0),
            "active_subscriptions": int(subs_row.active or 0),
            "expired_subscriptions": int(subs_row.expired or 0),
            "active_with_balance": int(subs_row.active_with_balance or 0),
            "wallet_holders": len(wallet_ids),
            "wallet_positive_balance": len(positive_balance_wallets),
            "subscription_usages_count": subscription_usages_count,
            "subscription_covered_amount": subscription_covered_amount,
            "wallet_earn_count": wallet_earn_count,
            "wallet_spend_count": wallet_spend_count,
            "wallet_spend_amount": wallet_spend_amount,
        }
