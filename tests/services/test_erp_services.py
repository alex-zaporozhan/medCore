from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.application.services.finance_service import (
    CreateFinancialTransactionInput,
    FinanceService,
)
from src.application.services.inventory_service import (
    InsufficientStockError,
    InventoryMovementInput,
    InventoryService,
)
from src.application.services.payroll_service import (
    PayrollService,
    SalaryCalculationContext,
)
from src.core.datetime_utils import utc_now
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.inventory_transaction import InventoryTransaction
from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.product import Product
from src.domain.entities.salary_transaction import SalaryTransaction
from src.domain.entities.warehouse import Warehouse
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_finance_service_creates_transaction_and_balance(init_db, seed_data):
  clinic_id = seed_data["clinic_id"]

  async with db_base.AsyncSessionLocal() as session:
    svc = FinanceService(session)

    cashbox = await svc.create_cashbox(
      clinic_id=clinic_id,
      name="Main cash",
      type="cash",
      currency="RUB",
      is_default=True,
      is_active=True,
    )

    await svc.create_transaction(
      CreateFinancialTransactionInput(
        clinic_id=clinic_id,
        cashbox_id=cashbox.id,
        type="income",
        amount=Decimal("1000.00"),
        currency="RUB",
        happened_at=utc_now(),
        description="Test income",
        booking_id=None,
        payment_id=None,
        source="test",
      )
    )
    await svc.create_transaction(
      CreateFinancialTransactionInput(
        clinic_id=clinic_id,
        cashbox_id=cashbox.id,
        type="expense",
        amount=Decimal("200.00"),
        currency="RUB",
        happened_at=utc_now(),
        description="Test expense",
        booking_id=None,
        payment_id=None,
        source="test",
      )
    )
    await session.commit()

    balance = await svc.get_cashbox_balance(clinic_id=clinic_id, cashbox_id=cashbox.id)
    assert balance == Decimal("800.00")

    result = await session.execute(
      select(FinancialTransaction).where(FinancialTransaction.clinic_id == clinic_id)
    )
    txs = list(result.scalars().all())
    assert len(txs) == 2


@pytest.mark.asyncio
async def test_payroll_service_calculates_salary_from_policy(init_db, seed_data):
  clinic_id = seed_data["clinic_id"]
  doctor_id = seed_data["doctor_id"]

  async with db_base.AsyncSessionLocal() as session:
    svc = PayrollService(session)

    policy = PayrollPolicy(
      clinic_id=clinic_id,
      doctor_id=doctor_id,
      role=None,
      fixed_per_shift=Decimal("0.00"),
      percent_from_services=Decimal("0.3000"),
      percent_from_products=Decimal("0.1000"),
    )
    session.add(policy)
    await session.flush()

    tx = await svc.calculate_and_create_salary_transaction(
      SalaryCalculationContext(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        role=None,
        services_amount=Decimal("1000.00"),
        products_amount=Decimal("200.00"),
        period_start=date.today(),
        period_end=date.today(),
        booking_id=None,
      )
    )
    await session.commit()

    assert isinstance(tx, SalaryTransaction)
    assert tx.amount == Decimal("340.00")


@pytest.mark.asyncio
async def test_inventory_service_stock_and_insufficient_error(init_db, seed_data):
  clinic_id = seed_data["clinic_id"]

  async with db_base.AsyncSessionLocal() as session:
    svc = InventoryService(session)

    product = Product(
      clinic_id=clinic_id,
      sku="TST-001",
      name="Test Gloves",
      unit="pcs",
      is_active=True,
    )
    warehouse = Warehouse(
      clinic_id=clinic_id,
      name="Main warehouse",
      is_default=True,
    )
    session.add(warehouse)
    session.add(product)
    await session.flush()

    incoming = InventoryMovementInput(
      clinic_id=clinic_id,
      warehouse_id=warehouse.id,
      product_id=product.id,
      type="incoming",
      quantity=Decimal("10.000"),
      happened_at=datetime.utcnow(),
      description="Initial stock",
      booking_id=None,
    )
    await svc.register_movement(incoming)

    outgoing_ok = InventoryMovementInput(
      clinic_id=clinic_id,
      warehouse_id=warehouse.id,
      product_id=product.id,
      type="outgoing",
      quantity=Decimal("3.000"),
      happened_at=datetime.utcnow(),
      description="Usage",
      booking_id=None,
    )
    await svc.register_movement(outgoing_ok)
    await session.commit()

    stock = await svc.get_stock(
      clinic_id=clinic_id,
      product_id=product.id,
      warehouse_id=warehouse.id,
    )
    assert stock == Decimal("7.000")

    outgoing_too_much = InventoryMovementInput(
      clinic_id=clinic_id,
      warehouse_id=warehouse.id,
      product_id=product.id,
      type="outgoing",
      quantity=Decimal("8.000"),
      happened_at=datetime.utcnow(),
      description="Too much",
      booking_id=None,
    )

    with pytest.raises(InsufficientStockError):
      await svc.register_movement(outgoing_too_much)

