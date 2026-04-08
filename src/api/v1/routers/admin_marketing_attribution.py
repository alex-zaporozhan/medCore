"""Admin API for marketing attribution reports and campaign management."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.entitlement_dependencies import require_entitlement
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.dto.marketing_attribution_dto import (
    AttributionDrillDownResponse,
    MarketingAttributionSummary,
    MarketingCampaignRead,
)
from src.application.services.marketing_attribution_service import (
    MarketingAttributionService,
)

router = APIRouter(
    prefix="/admin/attribution",
    tags=["admin-marketing-attribution"],
    dependencies=[Depends(require_entitlement("marketing.attribution"))],
)


@router.get(
    "/summary",
    response_model=MarketingAttributionSummary,
    dependencies=[Depends(require_permissions("view_marketing_analytics"))],
)
async def get_marketing_attribution_summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    traffic_source_id: UUID | None = Query(None),
    campaign_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_marketing_analytics")),
) -> MarketingAttributionSummary:
    """Aggregated marketing attribution metrics for owner: leads, bookings, revenue, ROI, CAC."""
    if admin.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    service = MarketingAttributionService(session)
    try:
        return await service.get_channel_summary(
            clinic_id=admin.clinic_id,
            date_from=date_from,
            date_to=date_to,
            traffic_source_id=traffic_source_id,
            campaign_id=campaign_id,
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/campaigns",
    response_model=list[MarketingCampaignRead],
    dependencies=[Depends(require_permissions("view_marketing_analytics"))],
)
async def list_marketing_campaigns(
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_marketing_analytics")),
) -> list[MarketingCampaignRead]:
    """List marketing campaigns for current clinic with basic metrics and budgets."""
    if admin.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = MarketingAttributionService(session)
    try:
        return await service.list_campaigns(admin.clinic_id)
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/campaigns",
    response_model=MarketingCampaignRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_marketing_campaign(
    body: dict,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> MarketingCampaignRead:
    """Create or update marketing campaign and its planned/actual budgets."""
    if admin.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    service = MarketingAttributionService(session)
    try:
        campaign = await service.upsert_campaign(
            clinic_id=admin.clinic_id,
            payload=body,
        )
        await session.commit()
        return MarketingCampaignRead.model_validate(campaign)
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/drill-down",
    response_model=AttributionDrillDownResponse,
    dependencies=[Depends(require_permissions("view_marketing_analytics"))],
)
async def get_attribution_drill_down(
    date_from: date = Query(...),
    date_to: date = Query(...),
    drill_type: str = Query(..., description="leads | bookings | transactions"),
    traffic_source_id: UUID | None = Query(None),
    campaign_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_marketing_analytics")),
) -> AttributionDrillDownResponse:
    """Drill-down: list of leads, bookings or transactions for channel/period."""
    if admin.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be <= date_to",
        )
    if drill_type not in ("leads", "bookings", "transactions"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="drill_type must be leads, bookings or transactions",
        )
    service = MarketingAttributionService(session)
    try:
        return await service.get_drill_down(
            clinic_id=admin.clinic_id,
            date_from=date_from,
            date_to=date_to,
            drill_type=drill_type,
            traffic_source_id=traffic_source_id,
            campaign_id=campaign_id,
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
