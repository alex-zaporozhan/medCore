"""PricingService: единый слой ценообразования с учётом скидок."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.discount_service import DiscountService
from src.domain.entities.discount import Discount


@dataclass
class PricingResult:
    """Результат расчёта цены с учётом скидок."""

    base_price: Decimal
    effective_price: Decimal
    discount_amount: Decimal
    discount_id: Optional[UUID]
    discount_type: Optional[str]
    discount_name: Optional[str]


class PricingService:
    """Единый сервис для расчёта base/effective цены по правилам скидок."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discount_svc = DiscountService(session)

    async def compute_effective_price(
        self,
        *,
        clinic_id: UUID,
        service_id: Optional[UUID],
        doctor_id: Optional[UUID],
        patient_id: Optional[UUID],
        on_date: date,
        base_price: Decimal,
    ) -> PricingResult:
        """Вернуть результат ценообразования для указанного контекста."""
        discount, discount_amount, effective_price = await self._discount_svc.get_applicable_discount(
            clinic_id=clinic_id,
            service_id=service_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            on_date=on_date,
            price=base_price,
        )
        discount_entity: Optional[Discount] = discount
        return PricingResult(
            base_price=base_price,
            effective_price=effective_price,
            discount_amount=discount_amount,
            discount_id=getattr(discount_entity, "id", None),
            discount_type=getattr(discount_entity, "discount_type", None),
            discount_name=getattr(discount_entity, "name", None),
        )

