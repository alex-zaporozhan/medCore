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


class OwnerDashboardReport(BaseModel):
    """Owner dashboard: key metrics for the clinic."""

    clinic_id: str
    dashboard: DashboardReport
    no_show_rate: float
    total_revenue: Decimal
    prepayment_transactions_count: int
    waitlist_entries_count: int
    recall_campaigns_count: int

