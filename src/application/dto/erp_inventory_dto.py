"""DTOs for ERP inventory (products, warehouses, consumables, stock and movements)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ProductRead(BaseModel):
    id: UUID
    clinic_id: UUID
    sku: str | None
    name: str
    unit: str
    is_active: bool


class ProductCreate(BaseModel):
    sku: str | None = None
    name: str
    unit: str
    is_active: bool = True


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    unit: str | None = None
    is_active: bool | None = None


class WarehouseRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    is_default: bool


class WarehouseCreate(BaseModel):
    name: str
    is_default: bool = False


class WarehouseUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None


class ServiceConsumableRead(BaseModel):
    id: UUID
    clinic_id: UUID
    service_id: UUID
    product_id: UUID
    quantity_per_service: Decimal
    unit: str


class InventoryTransactionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    warehouse_id: UUID
    product_id: UUID
    type: str
    quantity: Decimal
    happened_at: datetime
    description: str | None
    booking_id: UUID | None


class InventoryStockItem(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    quantity: Decimal


