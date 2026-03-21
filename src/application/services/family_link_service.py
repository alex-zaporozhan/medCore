"""FamilyLink CRUD and spend limit checks for loyalty (LOY_FAMILY_013)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.metrics import loyalty_family_link_lifecycle_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.family_link import FamilyLink
from src.domain.entities.patient import Patient
from src.domain.entities.subscription_usage import SubscriptionUsage
from src.domain.entities.wallet_transaction import WalletTransaction

logger = logging.getLogger(__name__)


class FamilyLinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _ensure_patients_in_clinic(
        self, clinic_id: UUID, *patient_ids: UUID
    ) -> None:
        stmt = select(Patient.id).where(
            Patient.clinic_id == clinic_id,
            Patient.id.in_(list(patient_ids)),
        )
        result = await self.session.execute(stmt)
        found = {row[0] for row in result.all()}
        if found != set(patient_ids):
            raise ValueError("patients_not_in_clinic")

    async def create_family_link(
        self,
        clinic_id: UUID,
        *,
        primary_patient_id: UUID,
        related_patient_id: UUID,
        relation_type: str = "other",
        can_spend_from_owner_loyalty: bool = False,
        can_view_owner_history: bool = False,
        spending_limit_total: Decimal | None = None,
        spending_limit_periodic: Decimal | None = None,
        valid_until: datetime | None = None,
        created_by: UUID | None = None,
    ) -> FamilyLink:
        if primary_patient_id == related_patient_id:
            raise ValueError("primary_and_related_must_differ")
        await self._ensure_patients_in_clinic(
            clinic_id, primary_patient_id, related_patient_id
        )
        now = datetime.now(timezone.utc)
        row = FamilyLink(
            clinic_id=clinic_id,
            primary_patient_id=primary_patient_id,
            related_patient_id=related_patient_id,
            relation_type=relation_type,
            can_spend_from_owner_loyalty=can_spend_from_owner_loyalty,
            can_view_owner_history=can_view_owner_history,
            spending_limit_total=spending_limit_total,
            spending_limit_periodic=spending_limit_periodic,
            valid_until=valid_until,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            is_active=True,
        )
        self.session.add(row)
        await self.session.flush()
        loyalty_family_link_lifecycle_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            action="created",
        ).inc()
        logger.info(
            "family_link created",
            extra={
                "clinic_id": str(clinic_id),
                "family_link_id": str(row.id),
                "relation_type": relation_type,
                "can_spend": can_spend_from_owner_loyalty,
            },
        )
        return row

    async def update_family_link(
        self,
        clinic_id: UUID,
        link_id: UUID,
        updates: dict[str, Any],
    ) -> FamilyLink:
        row = await self.session.get(FamilyLink, link_id)
        if row is None or row.clinic_id != clinic_id:
            raise ValueError("family_link_not_found")
        allowed = {
            "relation_type",
            "can_spend_from_owner_loyalty",
            "can_view_owner_history",
            "spending_limit_total",
            "spending_limit_periodic",
            "valid_until",
        }
        for key, value in updates.items():
            if key in allowed:
                setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        logger.info(
            "family_link updated",
            extra={"clinic_id": str(clinic_id), "family_link_id": str(row.id)},
        )
        return row

    async def deactivate_family_link(self, clinic_id: UUID, link_id: UUID) -> None:
        row = await self.session.get(FamilyLink, link_id)
        if row is None or row.clinic_id != clinic_id:
            raise ValueError("family_link_not_found")
        row.is_active = False
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        loyalty_family_link_lifecycle_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            action="deactivated",
        ).inc()
        logger.info(
            "family_link deactivated",
            extra={"clinic_id": str(clinic_id), "family_link_id": str(link_id)},
        )

    async def primary_patient_ids_for_whom_viewer_can_see_loyalty_history(
        self,
        clinic_id: UUID,
        viewer_patient_id: UUID,
        at_time: datetime,
    ) -> list[UUID]:
        """Patients (owners) whose subscription usage timeline may be shown to viewer."""
        if at_time.tzinfo is None:
            at_time = at_time.replace(tzinfo=timezone.utc)
        stmt = select(FamilyLink.primary_patient_id).where(
            FamilyLink.clinic_id == clinic_id,
            FamilyLink.related_patient_id == viewer_patient_id,
            FamilyLink.is_active.is_(True),
            FamilyLink.can_view_owner_history.is_(True),
            or_(FamilyLink.valid_until.is_(None), FamilyLink.valid_until >= at_time),
        )
        result = await self.session.execute(stmt)
        return list({row[0] for row in result.all()})

    async def list_for_patient(
        self, clinic_id: UUID, patient_id: UUID
    ) -> list[FamilyLink]:
        stmt = (
            select(FamilyLink)
            .where(
                FamilyLink.clinic_id == clinic_id,
                FamilyLink.is_active.is_(True),
                or_(
                    FamilyLink.primary_patient_id == patient_id,
                    FamilyLink.related_patient_id == patient_id,
                ),
            )
            .order_by(FamilyLink.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_spend_link(
        self,
        clinic_id: UUID,
        owner_patient_id: UUID,
        beneficiary_patient_id: UUID,
        at_time: datetime,
    ) -> FamilyLink | None:
        if owner_patient_id == beneficiary_patient_id:
            return None
        stmt = select(FamilyLink).where(
            FamilyLink.clinic_id == clinic_id,
            FamilyLink.primary_patient_id == owner_patient_id,
            FamilyLink.related_patient_id == beneficiary_patient_id,
            FamilyLink.is_active.is_(True),
            FamilyLink.can_spend_from_owner_loyalty.is_(True),
            or_(
                FamilyLink.valid_until.is_(None),
                FamilyLink.valid_until >= at_time,
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _sum_amount_for_link(self, family_link_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(SubscriptionUsage.used_amount), 0)).where(
            SubscriptionUsage.family_link_id == family_link_id,
            SubscriptionUsage.used_amount.isnot(None),
        )
        r = await self.session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _sum_visits_for_link(self, family_link_id: UUID) -> int:
        stmt = select(func.coalesce(func.sum(SubscriptionUsage.used_visits), 0)).where(
            SubscriptionUsage.family_link_id == family_link_id,
            SubscriptionUsage.used_visits.isnot(None),
        )
        r = await self.session.execute(stmt)
        return int(r.scalar_one() or 0)

    async def _sum_amount_for_link_month(
        self, family_link_id: UUID, bounds: tuple[datetime, datetime]
    ) -> Decimal:
        start, end = bounds
        stmt = select(func.coalesce(func.sum(SubscriptionUsage.used_amount), 0)).where(
            SubscriptionUsage.family_link_id == family_link_id,
            SubscriptionUsage.used_amount.isnot(None),
            SubscriptionUsage.used_at >= start,
            SubscriptionUsage.used_at < end,
        )
        r = await self.session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _sum_visits_for_link_month(
        self, family_link_id: UUID, bounds: tuple[datetime, datetime]
    ) -> int:
        start, end = bounds
        stmt = select(func.coalesce(func.sum(SubscriptionUsage.used_visits), 0)).where(
            SubscriptionUsage.family_link_id == family_link_id,
            SubscriptionUsage.used_visits.isnot(None),
            SubscriptionUsage.used_at >= start,
            SubscriptionUsage.used_at < end,
        )
        r = await self.session.execute(stmt)
        return int(r.scalar_one() or 0)

    async def _sum_wallet_spend_for_link(self, family_link_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            WalletTransaction.family_link_id == family_link_id,
            WalletTransaction.type == "spend",
        )
        r = await self.session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _sum_wallet_spend_for_link_month(
        self, family_link_id: UUID, bounds: tuple[datetime, datetime]
    ) -> Decimal:
        start, end = bounds
        stmt = select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            WalletTransaction.family_link_id == family_link_id,
            WalletTransaction.type == "spend",
            WalletTransaction.happened_at >= start,
            WalletTransaction.happened_at < end,
        )
        r = await self.session.execute(stmt)
        return Decimal(str(r.scalar_one()))

    async def _combined_monetary_spend_for_link(self, family_link_id: UUID) -> Decimal:
        """Subscription amount usages + wallet spends tagged with this family link."""
        sub = await self._sum_amount_for_link(family_link_id)
        w = await self._sum_wallet_spend_for_link(family_link_id)
        return sub + w

    async def _combined_monetary_spend_for_link_month(
        self, family_link_id: UUID, bounds: tuple[datetime, datetime]
    ) -> Decimal:
        return await self._sum_amount_for_link_month(
            family_link_id, bounds
        ) + await self._sum_wallet_spend_for_link_month(family_link_id, bounds)

    @staticmethod
    def _month_bounds_utc(at_time: datetime) -> tuple[datetime, datetime]:
        if at_time.tzinfo is None:
            at_time = at_time.replace(tzinfo=timezone.utc)
        at_utc = at_time.astimezone(timezone.utc)
        start = at_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    async def assert_spend_within_limits(
        self,
        link: FamilyLink,
        *,
        used_amount: Decimal | None,
        used_visits: int | None,
        at_time: datetime,
    ) -> None:
        if link.spending_limit_total is not None:
            if used_amount is not None:
                prev = await self._combined_monetary_spend_for_link(link.id)
                if prev + used_amount > link.spending_limit_total:
                    raise ValueError("family_spend_limit_total_exceeded")
            elif used_visits is not None and used_visits > 0:
                prev_v = await self._sum_visits_for_link(link.id)
                if prev_v + used_visits > int(link.spending_limit_total):
                    raise ValueError("family_spend_limit_total_exceeded")

        if link.spending_limit_periodic is not None:
            bounds = self._month_bounds_utc(at_time)
            if used_amount is not None:
                prev_m = await self._combined_monetary_spend_for_link_month(
                    link.id, bounds
                )
                if prev_m + used_amount > link.spending_limit_periodic:
                    raise ValueError("family_spend_limit_periodic_exceeded")
            elif used_visits is not None and used_visits > 0:
                prev_vm = await self._sum_visits_for_link_month(link.id, bounds)
                if prev_vm + used_visits > int(link.spending_limit_periodic):
                    raise ValueError("family_spend_limit_periodic_exceeded")
