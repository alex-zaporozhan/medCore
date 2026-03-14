"""Admin ERP inventory API: products, warehouses, service consumables and stock."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.erp_inventory_dto import (
    InventoryStockItem,
    InventoryTransactionRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ServiceConsumableRead,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)
from src.application.services.inventory_service import (
    InsufficientStockError,
    InventoryMovementInput,
    InventoryService,
)
from src.core.datetime_utils import utc_now
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-inventory"],
    dependencies=[Depends(require_permissions("view_inventory"))],
)


@router.get(
    "/{clinic_id}/inventory/products",
    response_model=list[ProductRead],
)
async def list_products(
    clinic_id: UUID,
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[ProductRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    items = await service.list_products(clinic_id, is_active=is_active)
    return [ProductRead.model_validate(p) for p in items]


@router.post(
    "/{clinic_id}/inventory/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    clinic_id: UUID,
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> ProductRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    product = await service.create_product(
        clinic_id=clinic_id,
        name=data.name,
        unit=data.unit,
        sku=data.sku,
        is_active=data.is_active,
    )
    await session.commit()
    return ProductRead.model_validate(product)


@router.patch(
    "/{clinic_id}/inventory/products/{product_id}",
    response_model=ProductRead,
)
async def update_product(
    clinic_id: UUID,
    product_id: UUID,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> ProductRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    product = await service.get_product(product_id)
    if not product or product.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if data.sku is not None:
        product.sku = data.sku
    if data.name is not None:
        product.name = data.name
    if data.unit is not None:
        product.unit = data.unit
    if data.is_active is not None:
        product.is_active = data.is_active
    product = await service.update_product(product)
    await session.commit()
    return ProductRead.model_validate(product)


@router.delete(
    "/{clinic_id}/inventory/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_product(
    clinic_id: UUID,
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> None:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    product = await service.get_product(product_id)
    if not product or product.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    await service.delete_product(product_id)
    await session.commit()


@router.get(
    "/{clinic_id}/inventory/warehouses",
    response_model=list[WarehouseRead],
)
async def list_warehouses(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[WarehouseRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    items = await service.list_warehouses(clinic_id)
    return [WarehouseRead.model_validate(w) for w in items]


@router.post(
    "/{clinic_id}/inventory/warehouses",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse(
    clinic_id: UUID,
    data: WarehouseCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> WarehouseRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    warehouse = await service.create_warehouse(
        clinic_id=clinic_id,
        name=data.name,
        is_default=data.is_default,
    )
    await session.commit()
    return WarehouseRead.model_validate(warehouse)


@router.patch(
    "/{clinic_id}/inventory/warehouses/{warehouse_id}",
    response_model=WarehouseRead,
)
async def update_warehouse(
    clinic_id: UUID,
    warehouse_id: UUID,
    data: WarehouseUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> WarehouseRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    warehouse = await service.get_warehouse(warehouse_id)
    if not warehouse or warehouse.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if data.name is not None:
        warehouse.name = data.name
    if data.is_default is not None:
        warehouse.is_default = data.is_default
    warehouse = await service.update_warehouse(warehouse)
    await session.commit()
    return WarehouseRead.model_validate(warehouse)


@router.delete(
    "/{clinic_id}/inventory/warehouses/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_warehouse(
    clinic_id: UUID,
    warehouse_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    warehouse = await service.get_warehouse(warehouse_id)
    if not warehouse or warehouse.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    await service.delete_warehouse(warehouse_id)
    await session.commit()


@router.get(
    "/{clinic_id}/inventory/services/{service_id}/consumables",
    response_model=list[ServiceConsumableRead],
)
async def list_service_consumables(
    clinic_id: UUID,
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[ServiceConsumableRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    items = await service.list_service_consumables(clinic_id=clinic_id, service_id=service_id)
    return [ServiceConsumableRead.model_validate(c) for c in items]


@router.put(
    "/{clinic_id}/inventory/services/{service_id}/consumables",
    response_model=list[ServiceConsumableRead],
)
async def upsert_service_consumables(
    clinic_id: UUID,
    service_id: UUID,
    items: list[ServiceConsumableRead],
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[ServiceConsumableRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    tuples = [
        (item.product_id, item.quantity_per_service, item.unit)
        for item in items
    ]
    created = await service.upsert_service_consumables(
        clinic_id=clinic_id,
        service_id=service_id,
        items=tuples,
    )
    await session.commit()
    return [ServiceConsumableRead.model_validate(c) for c in created]


@router.get(
    "/{clinic_id}/inventory/transactions",
    response_model=list[InventoryTransactionRead],
)
async def list_inventory_transactions(
    clinic_id: UUID,
    product_id: UUID | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[InventoryTransactionRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    items = await service.list_transactions(
        clinic_id=clinic_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [InventoryTransactionRead.model_validate(tx) for tx in items]


@router.get(
    "/{clinic_id}/inventory/stock",
    response_model=InventoryStockItem,
)
async def get_inventory_stock(
    clinic_id: UUID,
    product_id: UUID,
    warehouse_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> InventoryStockItem:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    quantity = await service.get_stock(
        clinic_id=clinic_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )
    return InventoryStockItem(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
    )


@router.post(
    "/{clinic_id}/inventory/transactions",
    response_model=InventoryTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_inventory_movement(
    clinic_id: UUID,
    product_id: UUID,
    warehouse_id: UUID,
    type: str,
    quantity: float,
    description: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> InventoryTransactionRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = InventoryService(session)
    try:
        tx = await service.register_movement(
            InventoryMovementInput(
                clinic_id=clinic_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                type=type,
                quantity=quantity,
                happened_at=utc_now(),
                description=description,
                booking_id=None,
            )
        )
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    await session.commit()
    return InventoryTransactionRead.model_validate(tx)


