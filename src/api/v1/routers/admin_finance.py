"""Admin ERP finance API: cashboxes and financial transactions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.erp_finance_dto import (
    CashboxCreate,
    CashboxRead,
    CashboxUpdate,
    FinancialTransactionCreate,
    FinancialTransactionRead,
)
from src.application.services.finance_service import (
    CreateFinancialTransactionInput,
    FinanceService,
)
from src.application.services.loyalty_service import LoyaltyService
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-finance"],
    dependencies=[Depends(require_permissions("view_finance"))],
)


@router.get(
    "/{clinic_id}/finance/liability",
)
async def get_finance_liability(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """B6.2: Liability Dashboard — unearned revenue from active subscriptions."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = LoyaltyService(session)
    total, count = await service.get_liability(clinic_id)
    from decimal import Decimal
    return {
        "unearned_revenue": str(total.quantize(Decimal("0.01"))),
        "active_subscriptions_count": count,
    }


@router.get(
    "/{clinic_id}/finance/cashboxes",
    response_model=list[CashboxRead],
)
async def list_cashboxes(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[CashboxRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = FinanceService(session)
    items = await service.list_cashboxes(clinic_id)
    result = []
    for c in items:
        balance = await service.get_cashbox_balance(clinic_id, c.id)
        result.append(
            CashboxRead(
                id=c.id,
                clinic_id=c.clinic_id,
                name=c.name,
                type=c.type,
                currency=c.currency,
                is_default=c.is_default,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                balance=balance,
            )
        )
    return result


@router.post(
    "/{clinic_id}/finance/cashboxes",
    response_model=CashboxRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_cashbox(
    clinic_id: UUID,
    data: CashboxCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_finance")),
) -> CashboxRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = FinanceService(session)
    cashbox = await service.create_cashbox(
        clinic_id=clinic_id,
        name=data.name,
        type=data.type,
        currency=data.currency,
        is_default=data.is_default,
        is_active=data.is_active,
    )
    await session.commit()
    return CashboxRead.model_validate(cashbox)


@router.patch(
    "/{clinic_id}/finance/cashboxes/{cashbox_id}",
    response_model=CashboxRead,
)
async def update_cashbox(
    clinic_id: UUID,
    cashbox_id: UUID,
    data: CashboxUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_finance")),
) -> CashboxRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = FinanceService(session)
    cashbox = await service.get_cashbox(cashbox_id)
    if not cashbox or cashbox.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cashbox not found")
    if data.name is not None:
        cashbox.name = data.name
    if data.type is not None:
        cashbox.type = data.type
    if data.currency is not None:
        cashbox.currency = data.currency
    if data.is_default is not None:
        cashbox.is_default = data.is_default
    if data.is_active is not None:
        cashbox.is_active = data.is_active
    cashbox = await service.update_cashbox(cashbox)
    await session.commit()
    return CashboxRead.model_validate(cashbox)


@router.delete(
    "/{clinic_id}/finance/cashboxes/{cashbox_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_cashbox(
    clinic_id: UUID,
    cashbox_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_finance")),
) -> None:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = FinanceService(session)
    cashbox = await service.get_cashbox(cashbox_id)
    if not cashbox or cashbox.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cashbox not found")
    await service.delete_cashbox(cashbox_id)
    await session.commit()


@router.get(
    "/{clinic_id}/finance/transactions",
    response_model=list[FinancialTransactionRead],
)
async def list_financial_transactions(
    clinic_id: UUID,
    cashbox_id: UUID | None = Query(None),
    type_filter: str | None = Query(None, description="income|expense|transfer"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[FinancialTransactionRead]:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = FinanceService(session)
    items = await service.list_transactions(
        clinic_id=clinic_id,
        cashbox_id=cashbox_id,
        type_filter=type_filter,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return [FinancialTransactionRead.model_validate(t) for t in items]


@router.post(
    "/{clinic_id}/finance/transactions",
    response_model=FinancialTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_financial_transaction(
    clinic_id: UUID,
    data: FinancialTransactionCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_finance")),
) -> FinancialTransactionRead:
    """Create income, expense or transfer. Transfer creates two movements (expense from, income to)."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if data.type not in ("income", "expense", "transfer"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type must be income, expense or transfer",
        )
    service = FinanceService(session)
    now = datetime.now()
    description = data.category or None
    if data.type == "transfer":
        if not data.from_cashbox_id or not data.to_cashbox_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="from_cashbox_id and to_cashbox_id required for transfer",
            )
        if data.from_cashbox_id == data.to_cashbox_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="from and to cashbox must differ",
            )
        from_cashbox = await service.get_cashbox(data.from_cashbox_id)
        to_cashbox = await service.get_cashbox(data.to_cashbox_id)
        if not from_cashbox or from_cashbox.clinic_id != clinic_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="From cashbox not found")
        if not to_cashbox or to_cashbox.clinic_id != clinic_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="To cashbox not found")
        if data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="amount must be positive",
            )
        out_tx = await service.create_transaction(
            CreateFinancialTransactionInput(
                clinic_id=clinic_id,
                cashbox_id=data.from_cashbox_id,
                type="expense",
                amount=data.amount,
                currency=from_cashbox.currency,
                happened_at=now,
                description=description,
                booking_id=None,
                payment_id=None,
                source="manual",
            )
        )
        await service.create_transaction(
            CreateFinancialTransactionInput(
                clinic_id=clinic_id,
                cashbox_id=data.to_cashbox_id,
                type="income",
                amount=data.amount,
                currency=to_cashbox.currency,
                happened_at=now,
                description=description,
                booking_id=None,
                payment_id=None,
                source="manual",
            )
        )
        await session.commit()
        await session.refresh(out_tx)
        return FinancialTransactionRead.model_validate(out_tx)
    else:
        if not data.cashbox_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cashbox_id required for income/expense",
            )
        if data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="amount must be positive",
            )
        cashbox = await service.get_cashbox(data.cashbox_id)
        if not cashbox or cashbox.clinic_id != clinic_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cashbox not found")
        tx = await service.create_transaction(
            CreateFinancialTransactionInput(
                clinic_id=clinic_id,
                cashbox_id=data.cashbox_id,
                type=data.type,
                amount=data.amount,
                currency=cashbox.currency,
                happened_at=now,
                description=description,
                booking_id=None,
                payment_id=None,
                source="manual",
            )
        )
        await session.commit()
        await session.refresh(tx)
        return FinancialTransactionRead.model_validate(tx)
