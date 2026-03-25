"""DTOs for reporting endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardReport(BaseModel):
    """Dashboard metrics for a specific day (or period)."""

    date: date
    bookings_pending: int
    bookings_confirmed: int
    bookings_completed: int
    bookings_cancelled: int
    bookings_no_show: int
    new_patients: int
    revenue: Decimal
    new_leads_count: int = 0
    chat_writers_count: int = Field(
        default=0,
        description="Unique patients who wrote to admins today (chat_messages: sender_type='patient').",
    )
    cancellations_count: int = 0
    nps_avg: float | None = Field(
        default=None,
        description="Optional NPS average; null until reviews module exists; frontend hides NPS widget when null.",
    )
    empty_slot_hours: float = Field(
        default=0.0,
        description="Approx. sum of free schedule slot hours for the day (day scope); 0 when period≠day or unavailable.",
    )
    day_pulse_score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="0–100 «как прошёл день» по коэффициенту занятых часов к пустым слотам (occupancy).",
    )


class NoShowReport(BaseModel):
    """No-show statistics for a period."""

    date_from: date
    date_to: date
    total: int
    no_show_count: int
    no_show_rate: float  # 0.0–1.0 fraction of no_show over total


class RevenuePoint(BaseModel):
    """Single point for revenue time series."""

    date: date
    amount: Decimal


class RevenueReport(BaseModel):
    """Revenue statistics for a period."""

    date_from: date
    date_to: date
    total_revenue: Decimal
    points: list[RevenuePoint]


class CrmFunnelStageSummary(BaseModel):
    """Summary per CRM funnel stage for owner reports."""

    stage_id: str
    stage_name: str | None
    leads_count: int
    estimated_sum: Decimal
    actual_sum: Decimal


class CrmFunnelReport(BaseModel):
    """CRM funnel report: money on each stage."""

    clinic_id: str
    date_from: date | None = None
    date_to: date | None = None
    stages: list[CrmFunnelStageSummary]
    total_estimated: Decimal
    total_actual: Decimal


class PatientLtvItem(BaseModel):
    """LTV for a single patient."""

    patient_id: str
    full_name: str | None
    phone: str
    ltv_total: Decimal
    successful_leads_count: int


class PatientLtvReport(BaseModel):
    """Per-patient LTV and aggregates for owner."""

    clinic_id: str
    date_from: date | None = None
    date_to: date | None = None
    items: list[PatientLtvItem]
    total_patients: int
    average_ltv: Decimal

class OwnerDashboardReport(BaseModel):
    """Owner dashboard: key metrics for the clinic."""

    clinic_id: str
    dashboard: DashboardReport
    no_show_rate: float
    total_revenue: Decimal
    prepayment_transactions_count: int
    waitlist_entries_count: int
    recall_campaigns_count: int


class VisitRevenueItem(BaseModel):
    """ERP-based revenue per visit date."""

    date: date
    booking_id: str | None = None
    amount: Decimal


class VisitRevenueByPeriodReport(BaseModel):
    """ERP-based revenue report grouped by visit date."""

    clinic_id: str
    date_from: date
    date_to: date
    total_revenue: Decimal
    items: list[VisitRevenueItem]
    data_source: str | None = Field(
        default=None,
        description="aggregate | raw — источник строк (при включённом чтении из витрины).",
    )
    aggregate_max_updated_at: datetime | None = Field(
        default=None,
        description="Максимум updated_at по строкам витрины в запрошенном диапазоне дат визита.",
    )
    aggregate_stale: bool | None = Field(
        default=None,
        description="True если ответ собран из raw-запроса из‑за устаревшей витрины по диапазону.",
    )


class PayrollByPeriodItem(BaseModel):
    """Aggregated salary movements for doctor/booking in period."""

    doctor_id: str
    booking_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    amount: Decimal


class PayrollByPeriodReport(BaseModel):
    """ERP-based payroll movements for a clinic in period."""

    clinic_id: str
    date_from: date
    date_to: date
    items: list[PayrollByPeriodItem]
    data_source: str | None = Field(
        default=None,
        description="aggregate | raw — источник строк (при включённом чтении из витрины).",
    )
    aggregate_max_updated_at: datetime | None = Field(default=None)
    aggregate_stale: bool | None = Field(default=None)


class MaterialsByPeriodItem(BaseModel):
    """Inventory movements per product/booking in period."""

    product_id: str
    booking_id: str | None = None
    total_quantity: Decimal


class MaterialsByPeriodReport(BaseModel):
    """ERP-based inventory movements for a clinic in period."""

    clinic_id: str
    date_from: date
    date_to: date
    items: list[MaterialsByPeriodItem] = Field(
        ...,
        description=(
            "Rows ordered by product_id ascending, then booking_id (NULL last), "
            "matching Engine L2 vitrine read path."
        ),
    )
    data_source: str | None = Field(default=None)
    aggregate_max_updated_at: datetime | None = Field(default=None)
    aggregate_stale: bool | None = Field(default=None)


class LoyaltyObligationItem(BaseModel):
    """Current loyalty obligations for a patient in clinic."""

    patient_id: str | None = None
    total_obligations_amount: Decimal


class LoyaltyObligationsReport(BaseModel):
    """Snapshot of loyalty obligations for clinic."""

    clinic_id: str
    as_of: date | None = None
    items: list[LoyaltyObligationItem]


class RoiBySourceItem(BaseModel):
    """ERP-based revenue aggregated by traffic source / campaign."""

    date: date
    traffic_source_id: str | None = None
    campaign_id: str | None = None
    revenue: Decimal


class RoiBySourceReport(BaseModel):
    """ERP-based revenue by marketing source for period."""

    clinic_id: str
    date_from: date
    date_to: date
    items: list[RoiBySourceItem] = Field(
        ...,
        description=(
            "Rows ordered by visit date, then traffic_source_id (NULL last), then campaign_id (NULL last); "
            "aligned with ``ErpAggregateService.fetch_attribution_revenue_aggregate``."
        ),
    )
    data_source: str | None = Field(default=None)
    aggregate_max_updated_at: datetime | None = Field(default=None)
    aggregate_stale: bool | None = Field(default=None)

