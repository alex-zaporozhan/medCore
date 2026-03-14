"""SQLAlchemy implementations for ERP inventory repositories."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
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

logger = logging.getLogger(__name__)


class ProductRepositoryImpl(ProductRepository):
    """SQLAlchemy implementation of ProductRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        logger.info(
            "Product created",
            extra={"product_id": str(product.id), "clinic_id": str(product.clinic_id)},
        )
        return product

    async def get_by_id(self, product_id: UUID) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def list_for_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ):
        query: Select[tuple[Product]] = select(Product).where(
            Product.clinic_id == clinic_id,
        )
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, product: Product) -> Product:
        await self.session.flush()
        await self.session.refresh(product)
        logger.info(
            "Product updated",
            extra={"product_id": str(product.id), "clinic_id": str(product.clinic_id)},
        )
        return product

    async def delete(self, product_id: UUID) -> None:
        product = await self.get_by_id(product_id)
        if product:
            await self.session.delete(product)
            await self.session.flush()
            logger.info("Product deleted", extra={"product_id": str(product_id)})


class WarehouseRepositoryImpl(WarehouseRepository):
    """SQLAlchemy implementation of WarehouseRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, warehouse: Warehouse) -> Warehouse:
        self.session.add(warehouse)
        await self.session.flush()
        await self.session.refresh(warehouse)
        logger.info(
            "Warehouse created",
            extra={"warehouse_id": str(warehouse.id), "clinic_id": str(warehouse.clinic_id)},
        )
        return warehouse

    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        return result.scalar_one_or_none()

    async def get_default_for_clinic(self, clinic_id: UUID) -> Warehouse | None:
        result = await self.session.execute(
            select(Warehouse).where(
                Warehouse.clinic_id == clinic_id,
                Warehouse.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_clinic(self, clinic_id: UUID):
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.clinic_id == clinic_id)
        )
        return list(result.scalars().all())

    async def update(self, warehouse: Warehouse) -> Warehouse:
        await self.session.flush()
        await self.session.refresh(warehouse)
        logger.info(
            "Warehouse updated",
            extra={"warehouse_id": str(warehouse.id), "clinic_id": str(warehouse.clinic_id)},
        )
        return warehouse

    async def delete(self, warehouse_id: UUID) -> None:
        warehouse = await self.get_by_id(warehouse_id)
        if warehouse:
            await self.session.delete(warehouse)
            await self.session.flush()
            logger.info("Warehouse deleted", extra={"warehouse_id": str(warehouse_id)})


class InventoryTransactionRepositoryImpl(InventoryTransactionRepository):
    """SQLAlchemy implementation of InventoryTransactionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tx: InventoryTransaction) -> InventoryTransaction:
        self.session.add(tx)
        await self.session.flush()
        await self.session.refresh(tx)
        logger.info(
            "Inventory transaction created",
            extra={
                "tx_id": str(tx.id),
                "clinic_id": str(tx.clinic_id),
                "warehouse_id": str(tx.warehouse_id),
                "product_id": str(tx.product_id),
                "type": tx.type,
            },
        )
        return tx

    async def list_for_clinic(
        self,
        clinic_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        query: Select[tuple[InventoryTransaction]] = select(InventoryTransaction).where(
            InventoryTransaction.clinic_id == clinic_id,
        )
        if product_id:
            query = query.where(InventoryTransaction.product_id == product_id)
        if warehouse_id:
            query = query.where(InventoryTransaction.warehouse_id == warehouse_id)
        if date_from:
            query = query.where(InventoryTransaction.happened_at >= date_from)
        if date_to:
            query = query.where(InventoryTransaction.happened_at <= date_to)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stock_for_product(
        self,
        clinic_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
    ) -> Decimal:
        amount_case = func.sum(
            func.case(
                (
                    (InventoryTransaction.type == "incoming", InventoryTransaction.quantity),
                ),
                else_=-InventoryTransaction.quantity,
            )
        )
        result = await self.session.execute(
            select(func.coalesce(amount_case, 0)).where(
                InventoryTransaction.clinic_id == clinic_id,
                InventoryTransaction.product_id == product_id,
                InventoryTransaction.warehouse_id == warehouse_id,
            )
        )
        return Decimal(result.scalar() or 0)


class ServiceConsumableRepositoryImpl(ServiceConsumableRepository):
    """SQLAlchemy implementation of ServiceConsumableRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, consumable: ServiceConsumable) -> ServiceConsumable:
        self.session.add(consumable)
        await self.session.flush()
        await self.session.refresh(consumable)
        logger.info(
            "Service consumable created",
            extra={
                "consumable_id": str(consumable.id),
                "clinic_id": str(consumable.clinic_id),
                "service_id": str(consumable.service_id),
                "product_id": str(consumable.product_id),
            },
        )
        return consumable

    async def list_for_service(
        self,
        clinic_id: UUID,
        service_id: UUID,
    ):
        result = await self.session.execute(
            select(ServiceConsumable).where(
                ServiceConsumable.clinic_id == clinic_id,
                ServiceConsumable.service_id == service_id,
            )
        )
        return list(result.scalars().all())

    async def delete_for_service(self, clinic_id: UUID, service_id: UUID) -> None:
        result = await self.session.execute(
            select(ServiceConsumable).where(
                ServiceConsumable.clinic_id == clinic_id,
                ServiceConsumable.service_id == service_id,
            )
        )
        for row in result.scalars().all():
            await self.session.delete(row)
        await self.session.flush()
        logger.info(
            "Service consumables deleted for service",
            extra={"clinic_id": str(clinic_id), "service_id": str(service_id)},
        )

