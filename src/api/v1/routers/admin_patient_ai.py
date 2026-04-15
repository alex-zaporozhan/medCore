"""Admin: AI insight for patient profile."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, get_request_context
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.chat_ai_dto import PatientAiInsight
from src.application.services.chat_ai_service import ChatAiService, ChatAiServiceError
from src.core.context import RequestContext
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/patients", tags=["admin-patient-ai"])


@router.get(
    "/{patient_id}/ai-insight",
    response_model=PatientAiInsight,
)
async def get_patient_ai_insight(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    ctx: RequestContext = Depends(get_request_context),
    rate_limiter=Depends(get_rate_limiter),
) -> PatientAiInsight:
    clinic_id = current_admin.clinic_id
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:ai:patient_insight:clinic:{clinic_id}",
            limit=settings.rate_ai_clinic_limit,
            window=settings.rate_ai_clinic_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов к AI. Попробуйте позже.",
        )
    service = ChatAiService(session, ctx)
    try:
        return await service.analyze_patient(clinic_id, patient_id)
    except ChatAiServiceError as exc:
        if str(exc) == "Patient not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in patient AI insight", extra={"patient_id": str(patient_id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service temporarily unavailable",
        ) from exc

