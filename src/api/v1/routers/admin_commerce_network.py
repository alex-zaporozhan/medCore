"""Admin Commerce network read-models (Phase 4-F3): org-wide vitrine, entitlement commerce.store_network."""



from __future__ import annotations



from decimal import Decimal

from uuid import UUID



from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy.ext.asyncio import AsyncSession



from src.api.v1.dependencies import AdminContext, get_session, require_permissions

from src.api.v1.entitlement_dependencies import require_entitlement

from src.api.v1.routers.admin_auth import get_current_admin

from src.application.services.commerce_store_service import get_commerce_network_overview

from src.domain.entities.admin_user import AdminUser

from src.domain.entities.clinic import Clinic



router = APIRouter(

    prefix="/admin/organization/commerce",

    tags=["admin-commerce"],

    dependencies=[Depends(require_entitlement("commerce.store_network"))],

)





async def _resolve_organization_id_for_admin(

    session: AsyncSession,

    admin: AdminUser,

) -> UUID:

    if admin.organization_id is not None:

        return admin.organization_id

    clinic = await session.get(Clinic, admin.clinic_id)

    if clinic is not None and clinic.organization_id is not None:

        return clinic.organization_id

    raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail={

            "code": "organization_required",

            "message": "У администратора нет organization_id",

        },

    )





class CommerceNetworkClinicRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)



    clinic_id: UUID

    clinic_name: str

    stock_locations_count: int = Field(..., ge=0)

    nomenclature_items_count: int = Field(..., ge=0)

    total_on_hand_quantity: Decimal





class CommerceNetworkTotalsRead(BaseModel):

    stock_locations_total: int = Field(..., ge=0)

    nomenclature_items_total: int = Field(..., ge=0)

    total_on_hand_quantity: Decimal





class CommerceNetworkOverviewResponse(BaseModel):

    organization_id: str

    clinics: list[CommerceNetworkClinicRead]

    totals: CommerceNetworkTotalsRead





@router.get(

    "/network-overview",

    response_model=CommerceNetworkOverviewResponse,

)

async def commerce_network_overview(

    session: AsyncSession = Depends(get_session),

    current_admin: AdminUser = Depends(get_current_admin),

    _: AdminContext = Depends(require_permissions("view_inventory")),

) -> CommerceNetworkOverviewResponse:

    """Read-only rollup: all clinics of the admin organization with commerce aggregates."""

    org_id = await _resolve_organization_id_for_admin(session, current_admin)

    data = await get_commerce_network_overview(session, org_id)

    return CommerceNetworkOverviewResponse(

        organization_id=str(org_id),

        clinics=[

            CommerceNetworkClinicRead(

                clinic_id=c.clinic_id,

                clinic_name=c.clinic_name,

                stock_locations_count=c.stock_locations_count,

                nomenclature_items_count=c.nomenclature_items_count,

                total_on_hand_quantity=c.total_on_hand_quantity,

            )

            for c in data.clinics

        ],

        totals=CommerceNetworkTotalsRead(

            stock_locations_total=data.stock_locations_total,

            nomenclature_items_total=data.nomenclature_items_total,

            total_on_hand_quantity=data.total_on_hand_quantity,

        ),

    )


