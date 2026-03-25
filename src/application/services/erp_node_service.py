from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.erp_finance_dto import ErpVisitNodeRequest, ErpVisitNodeResult
from src.application.dto.erp_loyalty_dto import ErpLoyaltyWriteOffSummary
from src.domain.entities.erp_loyalty_obligation import (
    ErpLoyaltyObligation,
    ErpLoyaltyObligationMovement,
)
from src.application.services.booking_erp_service import BookingErpService, ERPConfigurationError


logger = logging.getLogger(__name__)


class FinanceProcessor(Protocol):
    async def process_finance(
        self,
        request: ErpVisitNodeRequest,
        session: AsyncSession,
    ) -> tuple[list[UUID], list[str]]:
        """Process finance part of visit completion.

        Returns a tuple of (finance_ids, warnings).
        Implementations must not commit/rollback the transaction.
        """


class PayrollProcessor(Protocol):
    async def process_payroll(
        self,
        request: ErpVisitNodeRequest,
        session: AsyncSession,
    ) -> tuple[list[UUID], list[str]]:
        """Process payroll part of visit completion.

        Returns a tuple of (payroll_ids, warnings).
        """


class InventoryProcessor(Protocol):
    async def process_inventory(
        self,
        request: ErpVisitNodeRequest,
        session: AsyncSession,
    ) -> tuple[list[UUID], list[str]]:
        """Process inventory part of visit completion.

        Returns a tuple of (inventory_ids, warnings).
        """


@dataclass
class ErpVisitNodeService:
    """Application-level ERP node for visit completion.

    Coordinates finance, payroll and inventory processors in a single
    transactional unit owned by the caller (BookingCompletionService).
    """

    finance_processor: FinanceProcessor | None = None
    payroll_processor: PayrollProcessor | None = None
    inventory_processor: InventoryProcessor | None = None

    async def process_visit_completion(
        self,
        request: ErpVisitNodeRequest,
        *,
        session: AsyncSession,
    ) -> ErpVisitNodeResult:
        """Main ERP entrypoint for visit completion.

        Coordinates finance/payroll/inventory processors. Keeps
        backward-compatible behaviour by falling back to legacy
        BookingErpService when processors are not configured.
        """

        # Basic structural validation hook (extendable later).
        if not request.booking_id or not request.clinic_id:
            logger.warning(
                "[ERP_NODE] invalid request for visit completion",
                extra={
                    "booking_id": str(request.booking_id) if request.booking_id else None,
                    "clinic_id": str(request.clinic_id) if request.clinic_id else None,
                    "chain": "booking_to_erp",
                    "step": "erp",
                    "error_type": "validation",
                },
            )
            return ErpVisitNodeResult(
                success=False,
                finance_ids=[],
                payroll_ids=[],
                inventory_ids=[],
                warnings=[],
                error_code="validation_invalid_request",
                error_message="ERP visit node request must contain booking_id and clinic_id.",
            )

        services_count = len(request.services or [])
        payments_count = len(request.payments or [])
        payroll_count = len(request.payroll_inputs or [])
        inventory_count = len(request.inventory_items or [])

        services_total = sum((item.total_amount for item in request.services), Decimal("0"))
        payments_total = sum((item.amount for item in request.payments), Decimal("0"))

        logger.info(
            "[ERP_NODE] process_visit_completion called",
            extra={
                "booking_id": str(request.booking_id),
                "clinic_id": str(request.clinic_id),
                "services_count": services_count,
                "services_total": str(services_total),
                "payments_count": payments_count,
                "payments_total": str(payments_total),
                "payroll_count": payroll_count,
                "inventory_count": inventory_count,
                "chain": "booking_to_erp",
                "step": "erp",
                "status": "start",
                "error_type": "success",
            },
        )

        finance_ids: list[UUID] = []
        payroll_ids: list[UUID] = []
        inventory_ids: list[UUID] = []
        warnings: list[str] = []

        # Backward-compatible path: if no processors are configured, delegate
        # to legacy BookingErpService, which encapsulates existing ERP flow.
        if (
            self.finance_processor is None
            and self.payroll_processor is None
            and self.inventory_processor is None
        ):
            legacy_service = BookingErpService(session)
            try:
                await legacy_service.process_booking_completed(request.booking_id)
            except ERPConfigurationError as exc:
                logger.warning(
                    "[ERP_NODE] ERP configuration error during visit completion",
                    extra={
                        "booking_id": str(request.booking_id),
                        "clinic_id": str(request.clinic_id),
                        "error_code": exc.code,
                        "chain": "booking_to_erp",
                        "step": "erp",
                        "status": "error",
                        "error_type": self._classify_error_code(exc.code),
                    },
                )
                return ErpVisitNodeResult(
                    success=False,
                    finance_ids=[],
                    payroll_ids=[],
                    inventory_ids=[],
                    warnings=[],
                    error_code=exc.code,
                    error_message=str(exc),
                )
            except Exception as exc:
                logger.exception(
                    "[ERP_NODE] legacy ERP flow crashed during process_booking_completed",
                    extra={
                        "booking_id": str(request.booking_id),
                        "clinic_id": str(request.clinic_id),
                        "chain": "booking_to_erp",
                        "step": "erp",
                        "status": "error",
                        "error_type": "unexpected",
                    },
                )
                return ErpVisitNodeResult(
                    success=False,
                    finance_ids=[],
                    payroll_ids=[],
                    inventory_ids=[],
                    warnings=[],
                    error_code="unexpected_error",
                    error_message=str(exc),
                    loyalty_summary=None,
                )
            try:
                loyalty_summary = await self._build_loyalty_summary(
                    clinic_id=request.clinic_id,
                    booking_id=request.booking_id,
                    session=session,
                )
            except Exception as exc:
                # Legacy path should never crash node-level contract; convert to
                # stable node result for caller and tests.
                logger.exception(
                    "[ERP_NODE] legacy loyalty summary build failed",
                    extra={
                        "booking_id": str(request.booking_id),
                        "clinic_id": str(request.clinic_id),
                        "chain": "booking_to_erp",
                        "step": "erp",
                        "status": "error",
                        "error_type": "unexpected",
                    },
                )
                return ErpVisitNodeResult(
                    success=False,
                    finance_ids=[],
                    payroll_ids=[],
                    inventory_ids=[],
                    warnings=[],
                    error_code="unexpected_error",
                    error_message=str(exc),
                    loyalty_summary=None,
                )

            logger.info(
                "[ERP_NODE] visit completion processed successfully (legacy ERP flow)",
                extra={
                    "booking_id": str(request.booking_id),
                    "clinic_id": str(request.clinic_id),
                    "chain": "booking_to_erp",
                    "step": "erp",
                    "status": "success",
                    "error_type": "success",
                },
            )

            return ErpVisitNodeResult(
                success=True,
                finance_ids=[],
                payroll_ids=[],
                inventory_ids=[],
                warnings=[],
                error_code=None,
                error_message=None,
                loyalty_summary=loyalty_summary,
            )

        # New processor-based flow. Each processor is optional; missing ones
        # simply leave corresponding IDs empty.
        try:
            if self.finance_processor is not None:
                f_ids, f_warnings = await self.finance_processor.process_finance(
                    request,
                    session,
                )
                finance_ids.extend(f_ids)
                warnings.extend(f_warnings)

            if self.payroll_processor is not None:
                p_ids, p_warnings = await self.payroll_processor.process_payroll(
                    request,
                    session,
                )
                payroll_ids.extend(p_ids)
                warnings.extend(p_warnings)

            if self.inventory_processor is not None:
                i_ids, i_warnings = await self.inventory_processor.process_inventory(
                    request,
                    session,
                )
                inventory_ids.extend(i_ids)
                warnings.extend(i_warnings)
        except ERPConfigurationError as exc:
            error_type = self._classify_error_code(exc.code)
            logger.warning(
                "[ERP_NODE] ERP configuration error in processors during visit completion",
                extra={
                    "booking_id": str(request.booking_id),
                    "clinic_id": str(request.clinic_id),
                    "error_code": exc.code,
                    "error_type": error_type,
                    "chain": "booking_to_erp",
                    "step": "erp",
                    "status": "error",
                },
            )
            return ErpVisitNodeResult(
                success=False,
                finance_ids=finance_ids,
                payroll_ids=payroll_ids,
                inventory_ids=inventory_ids,
                warnings=warnings,
                error_code=exc.code,
                error_message=str(exc),
            )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "[ERP_NODE] unexpected error during visit completion",
                extra={
                    "booking_id": str(request.booking_id),
                    "clinic_id": str(request.clinic_id),
                    "chain": "booking_to_erp",
                    "step": "erp",
                    "status": "error",
                    "error_type": "unexpected",
                },
            )
            return ErpVisitNodeResult(
                success=False,
                finance_ids=finance_ids,
                payroll_ids=payroll_ids,
                inventory_ids=inventory_ids,
                warnings=warnings,
                error_code="unexpected_error",
                error_message=str(exc),
            )

        loyalty_summary = await self._build_loyalty_summary(
            clinic_id=request.clinic_id,
            booking_id=request.booking_id,
            session=session,
        )

        logger.info(
            "[ERP_NODE] visit completion processed successfully (processor flow)",
            extra={
                "booking_id": str(request.booking_id),
                "clinic_id": str(request.clinic_id),
                "finance_ids_count": len(finance_ids),
                "payroll_ids_count": len(payroll_ids),
                "inventory_ids_count": len(inventory_ids),
                "warnings_count": len(warnings),
                "chain": "booking_to_erp",
                "step": "erp",
                "status": "success",
                "error_type": "success",
            },
        )

        return ErpVisitNodeResult(
            success=True,
            finance_ids=finance_ids,
            payroll_ids=payroll_ids,
            inventory_ids=inventory_ids,
            warnings=warnings,
            error_code=None,
            error_message=None,
            loyalty_summary=loyalty_summary,
        )

    async def _build_loyalty_summary(
        self,
        *,
        clinic_id: UUID,
        booking_id: UUID,
        session: AsyncSession,
    ) -> ErpLoyaltyWriteOffSummary | None:
        """Aggregate ERP loyalty obligation movements for this visit into summary."""

        stmt = select(ErpLoyaltyObligationMovement).where(
            ErpLoyaltyObligationMovement.clinic_id == clinic_id,
            ErpLoyaltyObligationMovement.booking_id == booking_id,
            ErpLoyaltyObligationMovement.movement_type == "WRITE_OFF_ON_VISIT",
        )
        result = await session.execute(stmt)
        movements: list[ErpLoyaltyObligationMovement] = list(result.scalars().all())
        if not movements:
            return None

        total_write_off = Decimal("0")
        obligation_ids: set[UUID] = set()
        for m in movements:
            total_write_off += -m.amount_delta  # amount_delta is negative for write-off
            obligation_ids.add(m.obligation_id)

        remaining_amounts: dict[UUID, Decimal] = {}
        if obligation_ids:
            obligations_stmt = select(ErpLoyaltyObligation).where(
                ErpLoyaltyObligation.id.in_(list(obligation_ids))
            )
            obligations_result = await session.execute(obligations_stmt)
            for o in obligations_result.scalars().all():
                remaining_amounts[o.id] = o.remaining_amount

        return ErpLoyaltyWriteOffSummary(
            booking_id=booking_id,
            clinic_id=clinic_id,
            total_write_off_amount=total_write_off,
            obligation_ids=list(obligation_ids),
            remaining_amounts=remaining_amounts,
            warnings=[],
        )

    @staticmethod
    def _classify_error_code(code: str | None) -> str:
        if not code:
            return "unknown"
        lowered = code.lower()
        if "cashbox" in lowered or "finance" in lowered or "payment" in lowered:
            return "finance"
        if "payroll" in lowered or "salary" in lowered or "policy" in lowered:
            return "payroll"
        if "warehouse" in lowered or "stock" in lowered or "inventory" in lowered:
            return "inventory"
        if "validation" in lowered or lowered.startswith("validation_"):
            return "validation"
        return "unknown"

