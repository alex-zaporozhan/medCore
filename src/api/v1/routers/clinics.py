"""Clinics API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_current_admin_optional, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.clinic_dto import ClinicCreate, ClinicRead, ClinicUpdate
from src.application.services.clinic_service import ClinicService
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clinics", tags=["clinics"])


@router.get("", response_model=list[ClinicRead])
async def get_clinics(
    request: Request,
    include_deleted: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser | None = Depends(get_current_admin_optional),
    rate_limiter=Depends(get_rate_limiter),
) -> list[ClinicRead]:
    """
    List clinics. Admin: full rows, optional include_deleted. Anonymous (U-011): rate-limited by IP;
    only clinics with non-empty clinic_slug, except legacy single-clinic DB (one row may lack slug);
    PII and yookassa_shop_id stripped.
    """
    service = ClinicService(session)
    if current_admin is not None:
        return await service.get_clinics(include_deleted=include_deleted)
    client_ip = request.client.host if request.client else "unknown"
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:public_clinics_list:ip:{client_ip}",
            limit=settings.rate_public_clinics_list_ip_limit,
            window=settings.rate_public_clinics_list_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Попробуйте позже.",
        )
    except Exception as exc:  # noqa: BLE001
        # Public discovery must not become 500 because Redis/rate-limiter is temporarily unavailable.
        logger.warning(
            "public_clinics_rate_limit_unavailable",
            extra={"client_ip": client_ip, "error": str(exc)},
        )
    return await service.get_clinics_for_unauthenticated_discovery()


@router.get("/{clinic_id}", response_model=ClinicRead)
async def get_clinic(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser | None = Depends(get_current_admin_optional),
) -> ClinicRead:
    """
    Get clinic by ID. Unauthenticated callers receive 404 to avoid UUID enumeration/metadata leak (U-011).
    """
    if current_admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = ClinicService(session)
    clinic = await service.get_clinic(clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic


@router.post("", response_model=ClinicRead, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    data: ClinicCreate,
    session: AsyncSession = Depends(get_session),
    _current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> ClinicRead:
    """Create a new clinic."""
    service = ClinicService(session)
    try:
        clinic = await service.create_clinic(data)
    except ValueError as e:
        if str(e) == "invalid_clinic_slug":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый slug клиники") from e
        raise
    logger.info("Clinic created via API", extra={"clinic_id": str(clinic.id)})
    return clinic


@router.put("/{clinic_id}", response_model=ClinicRead)
async def update_clinic(
    clinic_id: UUID,
    data: ClinicUpdate,
    session: AsyncSession = Depends(get_session),
    _current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> ClinicRead:
    """Update clinic."""
    service = ClinicService(session)
    try:
        clinic = await service.update_clinic(clinic_id, data)
    except ValueError as e:
        if str(e) == "invalid_clinic_slug":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый slug клиники") from e
        raise
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    logger.info("Clinic updated via API", extra={"clinic_id": str(clinic_id)})
    return clinic


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_clinic(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> None:
    """Soft delete clinic."""
    service = ClinicService(session)
    deleted = await service.delete_clinic(clinic_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    logger.info("Clinic deleted via API", extra={"clinic_id": str(clinic_id)})

