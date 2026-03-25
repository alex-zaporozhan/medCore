"""Admin discounts CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.discount_dto import DiscountCreate, DiscountRead, DiscountUpdate
from src.application.services.discount_service import DiscountService
from src.domain.entities.admin_user import AdminUser

router = APIRouter(prefix="/admin/clinics", tags=["admin-discounts"])


@router.get("/{clinic_id}/discounts", response_model=list[DiscountRead])
async def list_discounts(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
) -> list[DiscountRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    svc = DiscountService(session)
    items = await svc.list_by_clinic(clinic_id)
    return [DiscountRead.model_validate(d) for d in items]


@router.post(
    "/{clinic_id}/discounts",
    response_model=DiscountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_discount(
    clinic_id: UUID,
    data: DiscountCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> DiscountRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if data.discount_type == "first_visit" and (data.service_id or data.doctor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="first_visit discount must not have service_id or doctor_id",
        )
    svc = DiscountService(session)
    discount = await svc.create(clinic_id, data)
    await session.commit()
    return DiscountRead.model_validate(discount)


@router.get("/{clinic_id}/discounts/{discount_id}", response_model=DiscountRead)
async def get_discount(
    clinic_id: UUID,
    discount_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("view_marketing_analytics")),
) -> DiscountRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    svc = DiscountService(session)
    discount = await svc.get_by_id(discount_id, clinic_id)
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    return DiscountRead.model_validate(discount)


@router.put("/{clinic_id}/discounts/{discount_id}", response_model=DiscountRead)
async def update_discount(
    clinic_id: UUID,
    discount_id: UUID,
    data: DiscountUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> DiscountRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    svc = DiscountService(session)
    discount = await svc.update(discount_id, clinic_id, data)
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    await session.commit()
    return DiscountRead.model_validate(discount)


@router.delete("/{clinic_id}/discounts/{discount_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_discount(
    clinic_id: UUID,
    discount_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _perm_ctx: AdminContext = Depends(require_permissions("manage_marketing_campaigns")),
) -> None:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    svc = DiscountService(session)
    ok = await svc.delete(discount_id, clinic_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    await session.commit()
