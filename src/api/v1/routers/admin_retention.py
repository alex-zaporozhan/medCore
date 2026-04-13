"""Admin Retention API: segments, generate-offers, campaign ROI. B5.4."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.entitlement_dependencies import require_entitlement
from pydantic import BaseModel

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.payment import Payment
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.recall_log import RecallLog
from src.domain.entities.recall_segment import RecallSegment
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.recall_service import get_segment_patient_count
router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-retention"],
    dependencies=[Depends(require_entitlement("retention.bundle"))],
)


class RetentionSegmentItem(BaseModel):
    id: UUID
    name: str
    patient_count: int


class RetentionSegmentsResponse(BaseModel):
    segments: list[RetentionSegmentItem]


class GenerateOffersRequest(BaseModel):
    segment_id: UUID | None = None
    cohort: str | None = None


class OfferItem(BaseModel):
    patient_id: UUID
    offer_text: str


class GenerateOffersResponse(BaseModel):
    offers: list[OfferItem]


class CampaignRoiStage(BaseModel):
    stage: str
    count: int
    conversion_pct: float | None = None


class CampaignRoiResponse(BaseModel):
    campaign_id: UUID
    stages: list[CampaignRoiStage]
    paid_count: int = 0


class RetentionCampaignRoiSummaryRow(BaseModel):
    """Flat funnel row for admin UI tables (same permission as retention segments)."""

    campaign_id: UUID
    campaign_name: str
    sent: int
    read: int
    clicked: int
    booked: int
    paid: int


async def _compute_campaign_roi(
    session: AsyncSession,
    clinic_id: UUID,
    campaign: RecallCampaign,
) -> CampaignRoiResponse:
    campaign_id = campaign.id
    sent_result = await session.execute(
        select(func.count()).select_from(RecallLog).where(
            RecallLog.campaign_id == campaign_id,
            RecallLog.clinic_id == clinic_id,
        )
    )
    sent_count = int(sent_result.scalar() or 0)

    patients_result = await session.execute(
        select(RecallLog.patient_id)
        .where(
            RecallLog.campaign_id == campaign_id,
            RecallLog.clinic_id == clinic_id,
        )
        .distinct()
    )
    patient_ids = [row[0] for row in patients_result.all()]

    booked_count = 0
    paid_count = 0
    if patient_ids:
        campaign_start = campaign.started_at or campaign.created_at
        booking_filter = [
            Booking.clinic_id == clinic_id,
            Booking.patient_id.in_(patient_ids),
            Booking.deleted_at.is_(None),
        ]
        if campaign_start:
            booking_filter.append(Booking.created_at >= campaign_start)
        bookings_result = await session.execute(select(Booking.id).where(*booking_filter))
        booking_ids = [row[0] for row in bookings_result.all()]
        booked_count = len(booking_ids)

        if booking_ids:
            paid_result = await session.execute(
                select(func.count()).select_from(Payment).where(
                    Payment.booking_id.in_(booking_ids),
                    Payment.status == "succeeded",
                )
            )
            paid_count = int(paid_result.scalar() or 0)

    stages = [
        CampaignRoiStage(stage="sent", count=sent_count, conversion_pct=None),
        CampaignRoiStage(stage="read", count=0, conversion_pct=None),
        CampaignRoiStage(stage="clicked", count=0, conversion_pct=None),
        CampaignRoiStage(
            stage="booked",
            count=booked_count,
            conversion_pct=(booked_count / sent_count * 100) if sent_count else None,
        ),
        CampaignRoiStage(
            stage="paid",
            count=paid_count,
            conversion_pct=(paid_count / sent_count * 100) if sent_count else None,
        ),
    ]
    return CampaignRoiResponse(
        campaign_id=campaign_id,
        stages=stages,
        paid_count=paid_count,
    )


@router.get("/{clinic_id}/retention/segments", response_model=RetentionSegmentsResponse)
async def list_retention_segments(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("erp.owner_reports.read")),
) -> RetentionSegmentsResponse:
    """Retention segments with patient count (reuses recall segments; predefined labels can be added)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    result = await session.execute(
        select(RecallSegment).where(RecallSegment.clinic_id == clinic_id)
    )
    segments = result.scalars().all()
    out = []
    for seg in segments:
        count = await get_segment_patient_count(session, clinic_id, seg.id)
        out.append(
            RetentionSegmentItem(
                id=seg.id,
                name=seg.name,
                patient_count=count,
            )
        )
    return RetentionSegmentsResponse(segments=out)


@router.get(
    "/{clinic_id}/retention/campaigns/roi-summary",
    response_model=list[RetentionCampaignRoiSummaryRow],
)
async def list_retention_campaigns_roi_summary(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("erp.owner_reports.read")),
) -> list[RetentionCampaignRoiSummaryRow]:
    """All recall campaigns for the clinic with funnel counts (retention entitlement; no recall-router permission)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    r = await session.execute(
        select(RecallCampaign).where(RecallCampaign.clinic_id == clinic_id).order_by(
            RecallCampaign.created_at.desc()
        )
    )
    campaigns = r.scalars().all()
    rows: list[RetentionCampaignRoiSummaryRow] = []
    for c in campaigns:
        roi = await _compute_campaign_roi(session, clinic_id, c)
        by_stage = {s.stage: s.count for s in roi.stages}
        rows.append(
            RetentionCampaignRoiSummaryRow(
                campaign_id=c.id,
                campaign_name=c.name,
                sent=by_stage.get("sent", 0),
                read=by_stage.get("read", 0),
                clicked=by_stage.get("clicked", 0),
                booked=by_stage.get("booked", 0),
                paid=by_stage.get("paid", 0),
            )
        )
    return rows


@router.get("/{clinic_id}/retention/campaigns/{campaign_id}/roi", response_model=CampaignRoiResponse)
async def get_campaign_roi(
    clinic_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("erp.owner_reports.read")),
) -> CampaignRoiResponse:
    """Campaign ROI: funnel stages (sent → read → clicked → booked → paid) and paid_count from real data."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    r = await session.execute(
        select(RecallCampaign).where(
            RecallCampaign.id == campaign_id,
            RecallCampaign.clinic_id == clinic_id,
        )
    )
    campaign = r.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return await _compute_campaign_roi(session, clinic_id, campaign)


# --- B5.5 Media (Omni-Vault) ---
class MediaItem(BaseModel):
    id: UUID
    patient_id: UUID | None = None
    booking_id: UUID | None = None
    message_id: UUID | None = None
    type: str
    url: str


class MediaListResponse(BaseModel):
    items: list[MediaItem]


@router.get("/{clinic_id}/media", response_model=MediaListResponse)
async def list_media(
    clinic_id: UUID,
    type_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("erp.owner_reports.read")),
) -> MediaListResponse:
    """Media with polymorphic link to patient_id, booking_id, message_id. Stub: empty list until storage wired."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return MediaListResponse(items=[])
