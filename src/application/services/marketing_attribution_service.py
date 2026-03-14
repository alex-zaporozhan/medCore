"""Marketing attribution service: aggregate ROI/reporting by channel and campaign."""

from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.marketing_attribution_dto import (
    AttributionDrillDownItem,
    AttributionDrillDownResponse,
    MarketingAttributionSummary,
    MarketingCampaignRead,
    MarketingChannelSummaryItem,
)
from src.domain.entities.booking import Booking
from src.domain.entities.campaign import Campaign
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.clinic import Clinic
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.traffic_source import TrafficSource
from src.domain.entities.visit_attribution import VisitAttribution


class MarketingAttributionService:
    """Service providing marketing attribution aggregates per traffic source / campaign."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_clinic(self, clinic_id: UUID) -> Clinic:
        result = await self.session.execute(
            select(Clinic).where(Clinic.id == clinic_id).limit(1)
        )
        clinic = result.scalar_one_or_none()
        if clinic is None:
            raise RuntimeError("Clinic not found")
        return clinic

    async def get_channel_summary(
        self,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        traffic_source_id: UUID | None = None,
        campaign_id: UUID | None = None,
    ) -> MarketingAttributionSummary:
        """Aggregate leads/bookings/revenue per traffic source/campaign for a period."""
        await self._get_clinic(clinic_id)

        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)

        # Join VisitAttribution with FinancialTransaction (income in period), Booking for completed count.
        va = VisitAttribution
        ft = FinancialTransaction
        ts = TrafficSource
        cmp = Campaign
        bk = Booking

        completed_booking_id = case(
            (bk.status == "completed", ft.booking_id),
            else_=None,
        )

        stmt = (
            select(
                va.traffic_source_id,
                va.campaign_id,
                func.count(func.distinct(va.lead_id)).label("leads_count"),
                func.count(func.distinct(ft.booking_id)).label("bookings_count"),
                func.count(func.distinct(completed_booking_id)).label(
                    "completed_bookings_count"
                ),
                func.count(func.distinct(va.patient_id)).label("unique_patients_count"),
                func.coalesce(func.sum(ft.amount), 0).label("revenue_sum"),
                func.min(ts.code).label("ts_code"),
                func.min(ts.name).label("ts_name"),
                func.min(cmp.code).label("cmp_code"),
                func.min(cmp.name).label("cmp_name"),
                func.min(cmp.budget_planned).label("budget_planned"),
                func.min(cmp.budget_actual).label("budget_actual"),
                func.min(va.utm_source).label("utm_source"),
            )
            .select_from(va)
            .join(
                ft,
                (ft.clinic_id == clinic_id)
                & (ft.visit_attribution_id == va.id)
                & (ft.type == "income")
                & (ft.happened_at >= start_dt)
                & (ft.happened_at < end_dt),
                isouter=True,
            )
            .join(bk, (ft.booking_id == bk.id), isouter=True)
            .join(
                cmp,
                (cmp.id == va.campaign_id) & (cmp.clinic_id == clinic_id),
                isouter=True,
            )
            .join(
                ts,
                (ts.id == va.traffic_source_id) & (ts.clinic_id == clinic_id),
                isouter=True,
            )
            .where(va.clinic_id == clinic_id)
        )
        if traffic_source_id is not None:
            stmt = stmt.where(va.traffic_source_id == traffic_source_id)
        if campaign_id is not None:
            stmt = stmt.where(va.campaign_id == campaign_id)

        stmt = stmt.group_by(va.traffic_source_id, va.campaign_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        items: list[MarketingChannelSummaryItem] = []
        for (
            ts_id,
            cmp_id,
            leads_count,
            bookings_count,
            completed_bookings_count,
            unique_patients_count,
            revenue_sum,
            ts_code,
            ts_name,
            cmp_code,
            cmp_name,
            budget_planned,
            budget_actual,
            utm_source,
        ) in rows:
            revenue = Decimal(revenue_sum or 0)
            completed = int(completed_bookings_count or 0)
            avg_check = revenue / completed if completed > 0 else Decimal("0")

            ad_spend_raw = budget_actual if budget_actual is not None else budget_planned
            ad_spend = Decimal(ad_spend_raw or 0) if ad_spend_raw is not None else None
            roi: float | None = None
            if ad_spend is not None and ad_spend > 0:
                roi = float(revenue / ad_spend)

            leads = int(leads_count or 0)
            cac: float | None = None
            if ad_spend is not None and ad_spend > 0 and leads > 0:
                cac = float(ad_spend / leads)

            items.append(
                MarketingChannelSummaryItem(
                    traffic_source_id=ts_id,
                    campaign_id=cmp_id,
                    traffic_source_code=ts_code,
                    traffic_source_name=ts_name,
                    campaign_code=cmp_code,
                    campaign_name=cmp_name,
                    utm_source=utm_source,
                    leads_count=leads,
                    bookings_count=int(bookings_count or 0),
                    completed_bookings_count=completed,
                    unique_patients_count=int(unique_patients_count or 0),
                    revenue_sum=revenue,
                    avg_check=avg_check,
                    ad_spend=ad_spend,
                    roi=roi,
                    cac=cac,
                )
            )

        return MarketingAttributionSummary(
            clinic_id=clinic_id,
            date_from=date_from,
            date_to=date_to,
            items=items,
        )

    async def list_campaigns(self, clinic_id: UUID) -> list[MarketingCampaignRead]:
        """List campaigns for admin UI."""
        await self._get_clinic(clinic_id)
        result = await self.session.execute(
            select(Campaign).where(Campaign.clinic_id == clinic_id).order_by(Campaign.name)
        )
        campaigns = result.scalars().all()
        return [MarketingCampaignRead.model_validate(c) for c in campaigns]

    async def upsert_campaign(
        self,
        clinic_id: UUID,
        payload: dict,
    ) -> Campaign:
        """Create or update a campaign with budgets."""
        await self._get_clinic(clinic_id)

        campaign_id: UUID | None = payload.get("id")
        if campaign_id:
            result = await self.session.execute(
                select(Campaign).where(
                    Campaign.id == campaign_id,
                    Campaign.clinic_id == clinic_id,
                )
            )
            campaign = result.scalar_one_or_none()
            if campaign is None:
                raise RuntimeError("Campaign not found")
        else:
            campaign = Campaign(clinic_id=clinic_id)
            self.session.add(campaign)

        if "traffic_source_id" in payload:
            campaign.traffic_source_id = payload["traffic_source_id"]
        if "code" in payload and payload["code"] is not None:
            campaign.code = payload["code"]
        if "name" in payload and payload["name"] is not None:
            campaign.name = payload["name"]
        if "external_id" in payload:
            campaign.external_id = payload["external_id"]
        if "budget_planned" in payload:
            campaign.budget_planned = payload["budget_planned"]
        if "budget_actual" in payload:
            campaign.budget_actual = payload["budget_actual"]
        if "is_active" in payload and payload["is_active"] is not None:
            campaign.is_active = payload["is_active"]

        await self.session.flush()
        return campaign

    async def get_drill_down(
        self,
        clinic_id: UUID,
        date_from: date,
        date_to: date,
        drill_type: str,
        traffic_source_id: UUID | None = None,
        campaign_id: UUID | None = None,
    ) -> AttributionDrillDownResponse:
        """Return list of leads, bookings or transactions for the given channel/period."""
        await self._get_clinic(clinic_id)
        start_dt = datetime.combine(date_from, dtime.min)
        end_dt = datetime.combine(date_to, dtime.min) + timedelta(days=1)
        va = VisitAttribution
        items: list[AttributionDrillDownItem] = []

        if drill_type == "leads":
            stmt = (
                select(LeadCard.id, LeadCard.title, LeadCard.created_at)
                .select_from(va)
                .join(LeadCard, (LeadCard.visit_attribution_id == va.id) & (LeadCard.clinic_id == clinic_id))
                .where(
                    va.clinic_id == clinic_id,
                    va.lead_id.isnot(None),
                    va.created_at >= start_dt,
                    va.created_at < end_dt,
                )
            )
            if traffic_source_id is not None:
                stmt = stmt.where(va.traffic_source_id == traffic_source_id)
            if campaign_id is not None:
                stmt = stmt.where(va.campaign_id == campaign_id)
            result = await self.session.execute(stmt)
            for row in result.all():
                items.append(
                    AttributionDrillDownItem(
                        id=row[0],
                        type="lead",
                        display_label=row[1] if row[1] else None,
                        happened_at=row[2].date() if row[2] else None,
                    )
                )
        elif drill_type == "bookings":
            ft = FinancialTransaction
            bk = Booking
            stmt = (
                select(bk.id, bk.appointment_date, bk.status)
                .select_from(va)
                .join(
                    ft,
                    (ft.visit_attribution_id == va.id)
                    & (ft.clinic_id == clinic_id)
                    & (ft.booking_id.isnot(None))
                    & (ft.happened_at >= start_dt)
                    & (ft.happened_at < end_dt),
                )
                .join(bk, (bk.id == ft.booking_id) & (bk.clinic_id == clinic_id))
                .where(va.clinic_id == clinic_id)
            )
            if traffic_source_id is not None:
                stmt = stmt.where(va.traffic_source_id == traffic_source_id)
            if campaign_id is not None:
                stmt = stmt.where(va.campaign_id == campaign_id)
            result = await self.session.execute(stmt)
            for row in result.all():
                items.append(
                    AttributionDrillDownItem(
                        id=row[0],
                        type="booking",
                        display_label=f"{row[1]} · {row[2]}" if row[1] else row[2],
                        happened_at=row[1],
                    )
                )
        elif drill_type == "transactions":
            ft = FinancialTransaction
            stmt = (
                select(ft.id, ft.amount, ft.happened_at)
                .select_from(va)
                .join(
                    ft,
                    (ft.visit_attribution_id == va.id)
                    & (ft.clinic_id == clinic_id)
                    & (ft.type == "income")
                    & (ft.happened_at >= start_dt)
                    & (ft.happened_at < end_dt),
                )
                .where(va.clinic_id == clinic_id)
            )
            if traffic_source_id is not None:
                stmt = stmt.where(va.traffic_source_id == traffic_source_id)
            if campaign_id is not None:
                stmt = stmt.where(va.campaign_id == campaign_id)
            result = await self.session.execute(stmt)
            for row in result.all():
                items.append(
                    AttributionDrillDownItem(
                        id=row[0],
                        type="transaction",
                        display_label=f"{row[1]} ₽" if row[1] is not None else None,
                        happened_at=row[2].date() if row[2] else None,
                    )
                )
        else:
            return AttributionDrillDownResponse(items=[], total=0)

        return AttributionDrillDownResponse(items=items, total=len(items))

