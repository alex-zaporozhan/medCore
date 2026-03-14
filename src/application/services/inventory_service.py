"""ERP inventory service: products, warehouses, consumables, and stock movements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.product import Product
from src.domain.entities.service_consumable import ServiceConsumable
from src.domain.entities.warehouse import Warehouse
from src.domain.interfaces.repositories.inventory_repository import (
    InventoryTransactionRepository,
    ProductRepository,
    ServiceConsumableRepository,
    WarehouseRepository,
)
from src.infrastructure.database.inventory_repo_impl import (
    InventoryTransactionRepositoryImpl,
    ProductRepositoryImpl,
    ServiceConsumableRepositoryImpl,
    WarehouseRepositoryImpl,
)


@dataclass
class InventoryMovementInput:
    clinic_id: UUID
    warehouse_id: UUID
    product_id: UUID
    type: str  # incoming|outgoing|adjustment
    quantity: Decimal
    happened_at: datetime
    description: str | None
    booking_id: UUID | None


class InsufficientStockError(RuntimeError):
    """Raised when trying to spend more stock than available."""


class InventoryService:
    """Application service for ERP inventory operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.product_repository: ProductRepository = ProductRepositoryImpl(session)
        self.warehouse_repository: WarehouseRepository = WarehouseRepositoryImpl(session)
        self.tx_repository: InventoryTransactionRepository = InventoryTransactionRepositoryImpl(
            session
        )
        self.consumable_repository: ServiceConsumableRepository = ServiceConsumableRepositoryImpl(
            session
        )

    # Products
    async def create_product(
        self,
        clinic_id: UUID,
        name: str,
        unit: str,
        sku: str | None = None,
        is_active: bool = True,
    ) -> Product:
        product = Product(
            clinic_id=clinic_id,
            sku=sku,
            name=name,
            unit=unit,
            is_active=is_active,
        )
        return await self.product_repository.create(product)

    async def update_product(self, product: Product) -> Product:
        return await self.product_repository.update(product)

    async def get_product(self, product_id: UUID) -> Product | None:
        return await self.product_repository.get_by_id(product_id)

    async def list_products(self, clinic_id: UUID, is_active: bool | None = None) -> list[Product]:
        return list(
            await self.product_repository.list_for_clinic(
                clinic_id=clinic_id,
                is_active=is_active,
            )
        )

    async def delete_product(self, product_id: UUID) -> None:
        await self.product_repository.delete(product_id)

    # Warehouses
    async def create_warehouse(
        self,
        clinic_id: UUID,
        name: str,
        is_default: bool = False,
    ) -> Warehouse:
        warehouse = Warehouse(
            clinic_id=clinic_id,
            name=name,
            is_default=is_default,
        )
        return await self.warehouse_repository.create(warehouse)

    async def update_warehouse(self, warehouse: Warehouse) -> Warehouse:
        return await self.warehouse_repository.update(warehouse)

    async def get_warehouse(self, warehouse_id: UUID) -> Warehouse | None:
        return await self.warehouse_repository.get_by_id(warehouse_id)

    async def list_warehouses(self, clinic_id: UUID) -> list[Warehouse]:
        return list(await self.warehouse_repository.list_for_clinic(clinic_id))

    async def delete_warehouse(self, warehouse_id: UUID) -> None:
        await self.warehouse_repository.delete(warehouse_id)

    async def get_default_warehouse(self, clinic_id: UUID) -> Warehouse | None:
        return await self.warehouse_repository.get_default_for_clinic(clinic_id)

    # Consumables
    async def upsert_service_consumables(
        self,
        clinic_id: UUID,
        service_id: UUID,
        items: list[tuple[UUID, Decimal, str]],
    ) -> list[ServiceConsumable]:
        """Replace tech card for service with provided product/quantity/unit tuples."""
        await self.consumable_repository.delete_for_service(clinic_id, service_id)
        created: list[ServiceConsumable] = []
        for product_id, quantity_per_service, unit in items:
            consumable = ServiceConsumable(
                clinic_id=clinic_id,
                service_id=service_id,
                product_id=product_id,
                quantity_per_service=quantity_per_service,
                unit=unit,
            )
            created.append(await self.consumable_repository.create(consumable))
        return created

    async def list_service_consumables(
        self,
        clinic_id: UUID,
        service_id: UUID,
    ) -> list[ServiceConsumable]:
        return list(
            await self.consumable_repository.list_for_service(
                clinic_id=clinic_id,
                service_id=service_id,
            )
        )

    # Inventory movements
    async def register_movement(
        self,
        data: InventoryMovementInput,
        check_stock: bool = True,
    ) -> InventoryTransaction:
        """Create inventory movement, validating stock for outgoing type."""
        if data.type == "outgoing" and check_stock:
            current_stock = await self.tx_repository.get_stock_for_product(
                clinic_id=data.clinic_id,
                product_id=data.product_id,
                warehouse_id=data.warehouse_id,
            )
            if current_stock < data.quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for product {data.product_id} in warehouse {data.warehouse_id}"
                )

        tx = InventoryTransaction(
            clinic_id=data.clinic_id,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            type=data.type,
            quantity=data.quantity,
            happened_at=data.happened_at,
            description=data.description,
            booking_id=data.booking_id,
        )
        return await self.tx_repository.create(tx)

    async def list_transactions(
        self,
        clinic_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[InventoryTransaction]:
        return list(
            await self.tx_repository.list_for_clinic(
                clinic_id=clinic_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                date_from=date_from,
                date_to=date_to,
            )
        )

    async def get_stock(
        self,
        clinic_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
    ) -> Decimal:
        return await self.tx_repository.get_stock_for_product(
            clinic_id=clinic_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
        )

