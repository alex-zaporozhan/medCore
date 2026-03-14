"""Inventory repository interfaces for ERP products, warehouses and inventory transactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.product import Product
from src.domain.entities.service_consumable import ServiceConsumable
from src.domain.entities.warehouse import Warehouse


class ProductRepository(ABC):
    """Repository interface for Product entity."""

    @abstractmethod
    async def create(self, product: Product) -> Product:
        ...

    @abstractmethod
    async def get_by_id(self, product_id: UUID) -> Product | None:
        ...

    @abstractmethod
    async def list_for_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ) -> Sequence[Product]:
        ...

    @abstractmethod
    async def update(self, product: Product) -> Product:
        ...

    @abstractmethod
    async def delete(self, product_id: UUID) -> None:
        ...


class WarehouseRepository(ABC):
    """Repository interface for Warehouse entity."""

    @abstractmethod
    async def create(self, warehouse: Warehouse) -> Warehouse:
        ...

    @abstractmethod
    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        ...

    @abstractmethod
    async def get_default_for_clinic(self, clinic_id: UUID) -> Warehouse | None:
        ...

    @abstractmethod
    async def list_for_clinic(self, clinic_id: UUID) -> Sequence[Warehouse]:
        ...

    @abstractmethod
    async def update(self, warehouse: Warehouse) -> Warehouse:
        ...

    @abstractmethod
    async def delete(self, warehouse_id: UUID) -> None:
        ...


class InventoryTransactionRepository(ABC):
    """Repository interface for InventoryTransaction entity."""

    @abstractmethod
    async def create(self, tx: InventoryTransaction) -> InventoryTransaction:
        ...

    @abstractmethod
    async def list_for_clinic(
        self,
        clinic_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Sequence[InventoryTransaction]:
        ...

    @abstractmethod
    async def get_stock_for_product(
        self,
        clinic_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
    ) -> Decimal:
        """Return current stock for given product and warehouse."""
        ...


class ServiceConsumableRepository(ABC):
    """Repository interface for ServiceConsumable entity."""

    @abstractmethod
    async def create(self, consumable: ServiceConsumable) -> ServiceConsumable:
        ...

    @abstractmethod
    async def list_for_service(
        self,
        clinic_id: UUID,
        service_id: UUID,
    ) -> Sequence[ServiceConsumable]:
        ...

    @abstractmethod
    async def delete_for_service(self, clinic_id: UUID, service_id: UUID) -> None:
        ...

