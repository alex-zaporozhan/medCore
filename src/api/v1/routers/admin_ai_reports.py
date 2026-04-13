"""Admin API: AI-based conflict and conversation analysis reports."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, get_request_context, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.conversation_analysis_service import ConversationAnalysisService
from src.core.context import RequestContext
from src.core.config import settings
from src.domain.entities.conversation_ai_analysis import ConversationAiAnalysis
from src.application.services.ai_client_factory import build_safe_ai_client
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter


router = APIRouter(prefix="/admin/ai-reports", tags=["admin-ai-reports"])
logger = logging.getLogger(__name__)

_DEFAULT_AI_CONFLICTS_LIMIT = 2000
_MAX_AI_CONFLICTS_LIMIT = 5000


class ConflictItem(BaseModel):
    conversation_id: UUID
    sentiment: str
    issue_category: str
    is_conflict: bool
    is_resolved: bool
    admin_mistakes: list[str]
    business_root_causes: list[str]
    suggested_playbook: list[str]
    created_at: str


class ConflictSummary(BaseModel):
    total: int
    unresolved_conflicts: int
    top_issue_categories: list[str]


class ConflictReportResponse(BaseModel):
    summary: ConflictSummary
    items: list[ConflictItem]
    ai_status: str | None = None
    items_skip: int = 0
    items_limit: int = _DEFAULT_AI_CONFLICTS_LIMIT


class ReanalyzeRequest(BaseModel):
    date_from: date
    date_to: date


@router.get(
    "/conflicts",
    response_model=ConflictReportResponse,
    dependencies=[Depends(require_permissions("view_ai_settings"))],
)
async def get_conflict_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_AI_CONFLICTS_LIMIT, ge=1, le=_MAX_AI_CONFLICTS_LIMIT),
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
    ctx: RequestContext = Depends(get_request_context),
    rate_limiter=Depends(get_rate_limiter),
) -> ConflictReportResponse:
    clinic_id: UUID = current_admin.clinic_id
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:ai:conflicts_report:clinic:{clinic_id}",
            limit=settings.rate_ai_heavy_clinic_limit,
            window=settings.rate_ai_heavy_clinic_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов к AI-отчётам. Попробуйте позже.",
        )
    base_filter = (
        ConversationAiAnalysis.clinic_id == clinic_id,
        ConversationAiAnalysis.analysis_date >= date_from,
        ConversationAiAnalysis.analysis_date <= date_to,
    )

    total = int(
        await session.scalar(
            select(func.count()).select_from(ConversationAiAnalysis).where(*base_filter)
        )
        or 0
    )
    unresolved_conflicts = int(
        await session.scalar(
            select(func.count())
            .select_from(ConversationAiAnalysis)
            .where(
                *base_filter,
                ConversationAiAnalysis.is_conflict.is_(True),
                ConversationAiAnalysis.is_resolved.is_(False),
            )
        )
        or 0
    )

    cat_rows = (
        await session.execute(
            select(ConversationAiAnalysis.issue_category, func.count().label("n"))
            .where(*base_filter)
            .group_by(ConversationAiAnalysis.issue_category)
            .order_by(func.count().desc())
            .limit(3)
        )
    ).all()
    top_issue_categories = [str(r[0]) for r in cat_rows if r[0] is not None]

    stmt_page = (
        select(ConversationAiAnalysis)
        .where(*base_filter)
        .order_by(ConversationAiAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt_page)
    rows: list[ConversationAiAnalysis] = list(result.scalars().all())

    # Use centralized AI config to indicate whether conflict reports can rely on external AI.
    safe_client, ctx_client = await build_safe_ai_client(clinic_id=clinic_id, session=session)
    logger.info(
        "build_safe_ai_client used for admin_ai_reports",
        extra={
            "source": "admin_ai_reports",
            "clinic_id": str(clinic_id),
            "provider_type": ctx_client.provider_type,
            "allow_personal_data": ctx_client.allow_personal_data,
        },
    )
    ai_configured = safe_client.is_configured()

    items = [
        ConflictItem(
            conversation_id=r.conversation_id,
            sentiment=r.sentiment,
            issue_category=r.issue_category,
            is_conflict=r.is_conflict,
            is_resolved=r.is_resolved,
            admin_mistakes=r.admin_mistakes or [],
            business_root_causes=r.business_root_causes or [],
            suggested_playbook=r.suggested_playbook or [],
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    summary = ConflictSummary(
        total=total,
        unresolved_conflicts=unresolved_conflicts,
        top_issue_categories=top_issue_categories,
    )

    if total == 0 and not ai_configured:
        ai_status = "fallback_local"
    else:
        ai_status = "external_active"

    return ConflictReportResponse(
        summary=summary,
        items=items,
        ai_status=ai_status,
        items_skip=skip,
        items_limit=limit,
    )


@router.post(
    "/conflicts/reanalyze",
    dependencies=[Depends(require_permissions("view_ai_settings"))],
)
async def reanalyze_conflicts(
    body: ReanalyzeRequest,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
    ctx: RequestContext = Depends(get_request_context),
    rate_limiter=Depends(get_rate_limiter),
) -> dict:
    clinic_id: UUID = current_admin.clinic_id
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:ai:conflicts_reanalyze:clinic:{clinic_id}",
            limit=settings.rate_ai_heavy_clinic_limit,
            window=settings.rate_ai_heavy_clinic_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов к AI-отчётам. Попробуйте позже.",
        )
    svc = ConversationAnalysisService(session, ctx)
    await svc.analyze_range(clinic_id, body.date_from, body.date_to)
    return {"status": "ok"}

