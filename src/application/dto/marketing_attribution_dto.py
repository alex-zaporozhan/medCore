"""DTOs for marketing attribution: landing leads and admin reports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class LandingLeadRequest(BaseModel):
  """Public landing lead payload with optional UTM/session attribution."""

  full_name: str | None = None
  phone: str
  comment: str | None = None

  session_id: str | None = None
  utm_source: str | None = None
  utm_medium: str | None = None
  utm_campaign: str | None = None
  utm_content: str | None = None
  utm_term: str | None = None
  landing_page: str | None = None
  anchor: str | None = None


class LandingLeadResponse(BaseModel):
  """Minimal response for landing lead creation."""

  lead_id: UUID
  visit_attribution_id: UUID


class MarketingChannelSummaryItem(BaseModel):
  """Single row in marketing attribution summary per channel/campaign."""

  traffic_source_id: UUID | None = None
  campaign_id: UUID | None = None
  traffic_source_code: str | None = None
  traffic_source_name: str | None = None
  campaign_code: str | None = None
  campaign_name: str | None = None
  utm_source: str | None = None  # raw from VisitAttribution when no TrafficSource

  leads_count: int
  bookings_count: int
  completed_bookings_count: int
  unique_patients_count: int
  revenue_sum: Decimal
  avg_check: Decimal
  ad_spend: Decimal | None = None
  roi: float | None = None
  cac: float | None = None  # cost per acquired lead (ad_spend / leads_count)


class MarketingAttributionSummary(BaseModel):
  """Aggregated marketing attribution metrics for a period."""

  clinic_id: UUID
  date_from: date
  date_to: date
  items: list[MarketingChannelSummaryItem]


class MarketingCampaignRead(BaseModel):
  """DTO for listing campaigns with base metrics/budgets."""

  id: UUID
  clinic_id: UUID
  traffic_source_id: UUID | None = None
  code: str
  name: str
  external_id: str | None = None
  budget_planned: Decimal | None = None
  budget_actual: Decimal | None = None
  is_active: bool


class AttributionDrillDownItem(BaseModel):
  """Single item in drill-down (lead, booking or transaction)."""

  id: UUID
  type: str  # lead | booking | transaction
  display_label: str | None = None  # e.g. phone mask, date, amount
  happened_at: date | None = None


class AttributionDrillDownResponse(BaseModel):
  """Drill-down list for a channel/campaign in period."""

  items: list[AttributionDrillDownItem]
  total: int

