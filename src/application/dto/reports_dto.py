"""DTOs for reporting endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardReport(BaseModel):
    """Dashboard metrics for a specific day."""

    date: date
    bookings_pending: int
    bookings_confirmed: int
    bookings_completed: int
    bookings_cancelled: int
    bookings_no_show: int
    new_patients: int
    revenue: Decimal


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

