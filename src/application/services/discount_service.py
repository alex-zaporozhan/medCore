"""Discount service: CRUD and applicable discount calculation."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.discount_dto import DiscountCreate, DiscountUpdate
from src.domain.entities.booking import Booking
from src.domain.entities.discount import Discount


class DiscountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_clinic(self, clinic_id: UUID) -> list[Discount]:
        result = await self.session.execute(
            select(Discount).where(
                Discount.clinic_id == clinic_id,
            ).order_by(Discount.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, discount_id: UUID, clinic_id: UUID) -> Discount | None:
        result = await self.session.execute(
            select(Discount).where(
                Discount.id == discount_id,
                Discount.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, clinic_id: UUID, data: DiscountCreate) -> Discount:
        discount = Discount(
            clinic_id=clinic_id,
            name=data.name,
            discount_type=data.discount_type,
            service_id=data.service_id,
            doctor_id=data.doctor_id,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            percent_off=data.percent_off,
            amount_off=data.amount_off,
            is_active=data.is_active,
        )
        self.session.add(discount)
        await self.session.flush()
        return discount

    async def update(
        self, discount_id: UUID, clinic_id: UUID, data: DiscountUpdate
    ) -> Discount | None:
        discount = await self.get_by_id(discount_id, clinic_id)
        if not discount:
            return None
        if data.name is not None:
            discount.name = data.name
        if data.discount_type is not None:
            discount.discount_type = data.discount_type
        if data.service_id is not None:
            discount.service_id = data.service_id
        if data.doctor_id is not None:
            discount.doctor_id = data.doctor_id
        if data.valid_from is not None:
            discount.valid_from = data.valid_from
        if data.valid_until is not None:
            discount.valid_until = data.valid_until
        if data.percent_off is not None:
            discount.percent_off = data.percent_off
        if data.amount_off is not None:
            discount.amount_off = data.amount_off
        if data.is_active is not None:
            discount.is_active = data.is_active
        await self.session.flush()
        return discount

    async def delete(self, discount_id: UUID, clinic_id: UUID) -> bool:
        discount = await self.get_by_id(discount_id, clinic_id)
        if not discount:
            return False
        await self.session.delete(discount)
        await self.session.flush()
        return True

    async def is_patient_first_visit(self, patient_id: UUID, clinic_id: UUID) -> bool:
        result = await self.session.execute(
            select(Booking.id).where(
                Booking.patient_id == patient_id,
                Booking.clinic_id == clinic_id,
                Booking.status == "completed",
            ).limit(1)
        )
        return result.scalar_one_or_none() is None

    async def get_applicable_discount(
        self,
        clinic_id: UUID,
        service_id: UUID | None,
        doctor_id: UUID | None,
        patient_id: UUID | None,
        on_date: date,
        price: Decimal,
    ) -> tuple[Discount | None, Decimal, Decimal]:
        """
        Return (discount, discount_amount, final_amount). Checks first_visit, service, doctor, period.
        """
        result = await self.session.execute(
            select(Discount).where(
                Discount.clinic_id == clinic_id,
                Discount.is_active.is_(True),
            )
        )
        discounts = list(result.scalars().all())
        for d in discounts:
            if d.valid_from and on_date < d.valid_from:
                continue
            if d.valid_until and on_date > d.valid_until:
                continue
            if d.discount_type == "first_visit":
                if patient_id and await self.is_patient_first_visit(patient_id, clinic_id):
                    amt, final = self.compute_discount_and_final(d, price)
                    return d, amt, final
            elif d.discount_type == "service" and service_id and d.service_id == service_id:
                amt, final = self.compute_discount_and_final(d, price)
                return d, amt, final
            elif d.discount_type == "doctor" and doctor_id and d.doctor_id == doctor_id:
                amt, final = self.compute_discount_and_final(d, price)
                return d, amt, final
            elif d.discount_type == "period":
                amt, final = self.compute_discount_and_final(d, price)
                return d, amt, final
        return None, Decimal("0"), price

    @staticmethod
    def _discount_amount(discount: Discount, price: Decimal) -> Decimal:
        if discount.percent_off is not None and discount.percent_off > 0:
            return (price * discount.percent_off / 100).quantize(Decimal("0.01"))
        if discount.amount_off is not None and discount.amount_off > 0:
            return min(discount.amount_off, price)
        return Decimal("0")

    def compute_discount_and_final(
        self, discount: Discount | None, price: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Return (discount_amount, final_amount)."""
        if not discount:
            return Decimal("0"), price
        amt = self._discount_amount(discount, price)
        return amt, max(Decimal("0"), price - amt)
