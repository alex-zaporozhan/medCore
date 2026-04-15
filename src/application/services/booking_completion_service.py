from __future__ import annotations

from datetime import datetime
from uuid import UUID
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.booking_dto import BookingCompletionResult
from src.application.dto.erp_finance_dto import (
    ErpBookingCompletionResult,
    ErpVisitNodeRequest,
    ErpVisitServiceItem,
    ErpVisitPaymentItem,
    ErpVisitPayrollInput,
    ErpVisitInventoryItem,
)
from src.application.dto.loyalty_dto import LoyaltyWriteOffResult
from src.application.services.booking_erp_service import (
    BookingErpService,
    ERPConfigurationError,
)
from src.application.services.erp_node_service import ErpVisitNodeService
from src.application.loyalty_completion_errors import LoyaltyVisitCompletionBlocked
from src.application.services.loyalty_service import (
    LoyaltyService,
    UseSubscriptionForBookingInput,
)
from src.application.events.event_bus import get_event_bus
from src.application.events.standard_events import make_booking_completed_event
from src.application.services.domain_outbox_service import enqueue_domain_event
from src.core.config import settings
from src.core.context import RequestContext
from src.core.prometheus_labels import clinic_bucket_label
from src.core.patient_messages import (
    BOOKING_NOT_FOUND,
    BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED,
)
from src.domain.entities.booking import Booking, BookingStatus, coerce_booking_status
from src.application.services.booking_status_service import BookingStatusService
from src.application.services.forms_service import FormsService
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.application.services.task_service import TaskService
from src.core.metrics import (  # no-op fallback when prometheus_client is absent
    Counter,
    Histogram,
    business_chain_booking_erp_duration_seconds,
    business_chain_booking_erp_errors_total,
    business_chain_booking_erp_step_duration_seconds,
    business_chain_booking_erp_total,
)


def _booking_status_str(status: BookingStatus | str) -> str:
    return coerce_booking_status(status).value


def _actor_trace_id(actor: object) -> str | None:
    """``RequestContext`` has ``trace_id``; ORM ``AdminUser`` does not."""
    tid = getattr(actor, "trace_id", None)
    return str(tid) if tid is not None else None


logger = logging.getLogger(__name__)

# Metrics for visit completion attempts and outcomes.
booking_completion_attempts_total = Counter(  # type: ignore[call-arg]
    "booking_completion_attempts_total",
    "Total attempts to complete visit via BookingCompletionService.complete_visit.",
    ["clinic_bucket", "status"],
)

booking_completion_errors_total = Counter(  # type: ignore[call-arg]
    "booking_completion_errors_total",
    "Total errors during booking completion facade flow.",
    ["clinic_bucket", "error_type"],
)

booking_completion_duration_seconds = Histogram(  # type: ignore[call-arg]
    "booking_completion_duration_seconds",
    "Duration of BookingCompletionService.complete_visit calls in seconds.",
    ["clinic_bucket"],
)


class FormsGateError(Exception):
    """Raised inside forms savepoint when mandatory signed forms are missing."""

    def __init__(self, codes: list[str]) -> None:
        super().__init__(codes)
        self.codes = codes


class ErpCompletionFailed(Exception):
    """Re-raised from loyalty/ERP savepoint so nested transaction rolls back."""

    __slots__ = ("exc",)

    def __init__(self, exc: ERPConfigurationError) -> None:
        self.exc = exc


class UnexpectedErpCompletionFailed(Exception):
    __slots__ = ("exc",)

    def __init__(self, exc: Exception) -> None:
        self.exc = exc


class LoyaltyBlockingError(Exception):
    """Subscription/wallet loyalty rules forbid completing the visit (rolls back nested txn)."""

    __slots__ = ("cause", "subscription_id")

    def __init__(
        self,
        cause: LoyaltyVisitCompletionBlocked,
        *,
        subscription_id: UUID | None = None,
    ) -> None:
        self.cause = cause
        self.subscription_id = subscription_id


booking_completion_erp_retry_total = Counter(  # type: ignore[call-arg]
    "booking_completion_erp_retry_total",
    "Admin retry of complete_visit after a prior ERP configuration error.",
    ["clinic_bucket"],
)


class BookingCompletionService:
    """Facade for atomic booking completion across ERP/Loyalty/CRM."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.booking_repository: BookingRepository = BookingRepositoryImpl(session)
        self.loyalty_service = LoyaltyService(session)
        self.erp_node_service = ErpVisitNodeService()
        self.task_repository: TaskRepository = TaskRepositoryImpl(session)
        self.task_service = TaskService(self.task_repository)
        self.status_service = BookingStatusService()

    async def complete_visit(
        self,
        booking_id: UUID,
        *,
        actor: RequestContext,
        use_subscription_id: UUID | None = None,
    ) -> BookingCompletionResult:
        """
        High-level completion flow.

        Single facade that validates booking state, orchestrates
        Loyalty/ERP/CRM steps and returns a structured
        BookingCompletionResult without exposing ORM details.

        Loyalty write-off + ERP node + status transition run inside one SQLAlchemy
        SAVEPOINT (nested transaction). If ERP fails, that savepoint rolls back so
        loyalty changes are not persisted while the outer transaction still applies
        ERP failure handling (erp_error_code, tasks, metrics) in a single commit.
        """
        started_at = datetime.now()
        # AdminUser exposes ``id``; RequestContext uses ``user_id``.
        actor_uid = getattr(actor, "user_id", None) or getattr(actor, "id", None)

        logger.info(
            "BookingCompletionService.complete_visit called",
            extra={
                "booking_id": str(booking_id),
                "actor_clinic_id": str(actor.clinic_id) if actor.clinic_id else None,
                "actor_user_id": str(actor_uid) if actor_uid else None,
                "trace_id": _actor_trace_id(actor),
                "chain": "booking_to_erp",
                "step": "start",
            },
        )

        booking = await self.booking_repository.get_by_id(booking_id)
        if booking:
            booking.status = coerce_booking_status(booking.status)
        if not booking or booking.clinic_id != actor.clinic_id:
            clinic_label = str(actor.clinic_id) if actor.clinic_id else "unknown"
            booking_completion_attempts_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                status="not_found_or_clinic_mismatch",
            ).inc()
            booking_completion_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                error_type="not_found_or_clinic_mismatch",
            ).inc()
            elapsed = (datetime.now() - started_at).total_seconds()
            booking_completion_duration_seconds.labels(clinic_bucket=clinic_bucket_label(clinic_label)).observe(elapsed)
            business_chain_booking_erp_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                status="not_found_or_clinic_mismatch",
            ).inc()
            business_chain_booking_erp_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                error_type="not_found_or_clinic_mismatch",
            ).inc()
            business_chain_booking_erp_duration_seconds.labels(
                clinic_bucket=clinic_bucket_label(clinic_label)
            ).observe(elapsed)
            logger.warning(
                "BookingCompletionService: booking not found or clinic mismatch",
                extra={
                    "booking_id": str(booking_id),
                    "actor_clinic_id": str(actor.clinic_id) if actor.clinic_id else None,
                    "booking_clinic_id": str(booking.clinic_id) if booking else None,
                    "trace_id": _actor_trace_id(actor),
                    "chain": "booking_to_erp",
                    "step": "start",
                },
            )
            return BookingCompletionResult(
                success=False,
                booking_id=booking_id,
                final_status="unknown",
                error_code="booking_not_found",
                error_message=BOOKING_NOT_FOUND,
            )

        if booking.status not in {
            BookingStatus.CONFIRMED,
            BookingStatus.PENDING,
            BookingStatus.REGISTERED,
            BookingStatus.IN_PROGRESS,
        }:
            clinic_label = str(booking.clinic_id)
            booking_completion_attempts_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                status="invalid_status",
            ).inc()
            booking_completion_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                error_type="invalid_status",
            ).inc()
            logger.warning(
                "BookingCompletionService: invalid booking status for completion",
                extra={
                    "booking_id": str(booking.id),
                    "clinic_id": str(booking.clinic_id),
                    "status": booking.status,
                    "trace_id": _actor_trace_id(actor),
                    "chain": "booking_to_erp",
                    "step": "start",
                },
            )
            elapsed = (datetime.now() - started_at).total_seconds()
            booking_completion_duration_seconds.labels(clinic_bucket=clinic_bucket_label(clinic_label)).observe(elapsed)
            business_chain_booking_erp_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                status="invalid_status",
            ).inc()
            business_chain_booking_erp_errors_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_label),
                error_type="invalid_status",
            ).inc()
            business_chain_booking_erp_duration_seconds.labels(
                clinic_bucket=clinic_bucket_label(clinic_label)
            ).observe(elapsed)
            return BookingCompletionResult(
                success=False,
                booking_id=booking.id,
                final_status=_booking_status_str(booking.status),
                error_code="invalid_status",
                error_message=BOOKING_ONLY_PENDING_CONFIRMED_COMPLETED,
            )

        booking_completion_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            status="attempt",
        ).inc()
        business_chain_booking_erp_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            status="attempt",
        ).inc()

        # Обязательные формы: до loyalty и ERP — не списывать подписку и не проводить визит без документов.
        forms_service = FormsService(self.session)
        await forms_service.mark_expired_submissions(booking.clinic_id, booking.id)
        try:
            async with self.session.begin_nested():
                missing_forms = await forms_service.list_missing_required_signed_template_codes(
                    booking.clinic_id,
                    booking.id,
                )
                if missing_forms:
                    raise FormsGateError(missing_forms)
        except FormsGateError as e:
            missing_label = ", ".join(e.codes)
            if booking.patient_id is None:
                err_msg = (
                    "Нельзя завершить визит: на записи не указан пациент при наличии обязательных форм к завершению. "
                    f"Шаблоны: {missing_label}. Назначьте пациента или скорректируйте настройки шаблонов."
                )
            else:
                err_msg = (
                    f"Required signed forms are missing for this visit: {missing_label}. "
                    "Complete or re-issue the documents before completing the visit."
                )
            try:
                await self.task_service.create_task(
                    clinic_id=booking.clinic_id,
                    title="PAPERLESS_REQUIRED_FORMS_MISSING",
                    description=err_msg + (f" trace_id={_actor_trace_id(actor)}" if _actor_trace_id(actor) else ""),
                    priority="high",
                    role_assignee="owner",
                    booking_id=booking.id,
                    patient_id=booking.patient_id,
                    source="system",
                    source_event_id=booking.id,
                    trace_id=_actor_trace_id(actor),
                )
            except Exception:
                logger.exception(
                    "BookingCompletionService: failed to create paperless missing-forms task",
                    extra={
                        "booking_id": str(booking.id),
                        "clinic_id": str(booking.clinic_id),
                        "trace_id": _actor_trace_id(actor),
                    },
                )
            return BookingCompletionResult(
                success=False,
                booking_id=booking.id,
                final_status=_booking_status_str(booking.status),
                erp_summary=None,
                loyalty_summary=None,
                warnings=[],
                error_code="missing_required_forms",
                error_message=err_msg,
            )

        try:
            async with self.session.begin_nested():
                now = datetime.now()

                prepare_started = datetime.now()
                logger.info(
                    "BookingCompletionService.complete_visit: preparing data for loyalty/ERP steps",
                    extra={
                        "booking_id": str(booking.id),
                        "clinic_id": str(booking.clinic_id),
                        "trace_id": _actor_trace_id(actor),
                        "chain": "booking_to_erp",
                        "step": "prepare",
                    },
                )
        
                # Loyalty: subscription business errors block completion (G1 / ERP_LOYALTY_011).
                candidate = None
                if use_subscription_id is not None:
                    sub = await self.loyalty_service.customer_repo.get_by_id(use_subscription_id)
                    if (
                        sub is not None
                        and sub.clinic_id == actor.clinic_id
                        and sub.status == "active"
                        and await self.loyalty_service.patient_can_use_subscription(
                            actor.clinic_id,
                            sub,
                            booking.patient_id,
                            now,
                        )
                    ):
                        candidate = sub
                if candidate is None and use_subscription_id is None:
                    candidate = await self.loyalty_service.select_subscription_for_booking(
                        clinic_id=booking.clinic_id,
                        patient_id=booking.patient_id,
                        booking_id=booking.id,
                        on_date=now,
                    )
                business_chain_booking_erp_step_duration_seconds.labels(
                    clinic_bucket=clinic_bucket_label(booking.clinic_id),
                    step="prepare",
                ).observe((datetime.now() - prepare_started).total_seconds())
        
                loyalty_summary: dict | None = None
                loyalty_result: LoyaltyWriteOffResult | None = None
                if candidate is not None:
                    try:
                        used_visits = 1 if (candidate.remaining_visits or 0) > 0 else None
                        used_amount = None if used_visits else (candidate.remaining_amount or None)
                        if used_visits is not None or used_amount is not None:
                            step_started = datetime.now()
                            await self.loyalty_service.use_subscription_for_booking(
                                UseSubscriptionForBookingInput(
                                    clinic_id=booking.clinic_id,
                                    booking_id=booking.id,
                                    subscription_id=candidate.id,
                                    used_visits=used_visits,
                                    used_amount=used_amount,
                                    used_at=now,
                                    beneficiary_patient_id=booking.patient_id,
                                )
                            )
                            step_elapsed = (datetime.now() - step_started).total_seconds()
                            business_chain_booking_erp_step_duration_seconds.labels(
                                clinic_bucket=clinic_bucket_label(booking.clinic_id),
                                step="loyalty",
                            ).observe(step_elapsed)
                            booking.paid_by_subscription = True
                            loyalty_result = LoyaltyWriteOffResult(
                                success=True,
                                booking_id=booking.id,
                                subscription_id=candidate.id,
                                remaining_visits=None,
                                remaining_amount=None,
                            )
                            loyalty_summary = loyalty_result.model_dump()
        
                            logger.info(
                                "BookingCompletionService: loyalty write-off applied during completion",
                                extra={
                                    "booking_id": str(booking.id),
                                    "clinic_id": str(booking.clinic_id),
                                    "subscription_id": str(candidate.id),
                                    "trace_id": _actor_trace_id(actor),
                                    "chain": "booking_to_erp",
                                    "step": "loyalty",
                                },
                            )
                    except LoyaltyVisitCompletionBlocked as e:
                        raise LoyaltyBlockingError(
                            e,
                            subscription_id=candidate.id,
                        ) from e
                    except Exception:
                        # Unexpected loyalty errors: best-effort (non-blocking), legacy behaviour.
                        booking_completion_errors_total.labels(
                            clinic_bucket=clinic_bucket_label(booking.clinic_id),
                            error_type="loyalty_error",
                        ).inc()
                        business_chain_booking_erp_errors_total.labels(
                            clinic_bucket=clinic_bucket_label(booking.clinic_id),
                            error_type="loyalty_error",
                        ).inc()
                        loyalty_result = LoyaltyWriteOffResult(
                            success=False,
                            booking_id=booking.id,
                            subscription_id=candidate.id if candidate else None,
                            error_code="loyalty_apply_failed",
                            error_message="Loyalty write-off failed during booking completion",
                            remaining_visits=None,
                            remaining_amount=None,
                        )
                        loyalty_summary = loyalty_result.model_dump()

                        logger.exception(
                            "BookingCompletionService: loyalty error during completion",
                            extra={
                                "booking_id": str(booking.id),
                                "clinic_id": str(booking.clinic_id),
                                "subscription_id": str(candidate.id) if candidate else None,
                                "trace_id": _actor_trace_id(actor),
                                "chain": "booking_to_erp",
                                "step": "loyalty",
                            },
                        )
        
                erp_result_dto: ErpBookingCompletionResult | None = None
                erp_summary: dict | None = None
                try:
                    step_started_erp = datetime.now()
        
                    # Минимальное наполнение ErpVisitNodeRequest на основе уже доступного контекста.
                    services: list[ErpVisitServiceItem] = []
                    payments: list[ErpVisitPaymentItem] = []
                    payroll_inputs: list[ErpVisitPayrollInput] = []
                    inventory_items: list[ErpVisitInventoryItem] = []
        
                    booking_erp = BookingErpService(self.session)
                    ctx = await booking_erp._load_context(booking.id)  # type: ignore[attr-defined]
        
                    # Хотя бы одна услуга визита.
                    if ctx.service is not None:
                        price = ctx.services_amount
                        services.append(
                            ErpVisitServiceItem(
                                service_id=ctx.service.id,
                                quantity=Decimal("1"),
                                price=price,
                                total_amount=price,  # TODO: учесть скидки/кошелёк отдельно
                            )
                        )
        
                    # Хотя бы один платёж, если он есть.
                    if booking.payment_id is not None:
                        payment = await booking_erp.payment_repository.get_by_id(booking.payment_id)
                        if payment is not None:
                            payments.append(
                                ErpVisitPaymentItem(
                                    source="cash",  # TODO: различать cash/acquiring/package/deposit
                                    amount=payment.amount,
                                    external_payment_id=payment.id,
                                )
                            )
        
                    # Минимальный payroll по основному исполнителю.
                    try:
                        payroll_inputs.append(
                            ErpVisitPayrollInput(
                                doctor_id=booking.doctor_id,
                                role=getattr(ctx.doctor, "specialist_role", None),
                                services_amount=ctx.services_amount,
                                products_amount=ctx.products_amount,
                                period_start=ctx.period_start,
                                period_end=ctx.period_end,
                            )
                        )
                    except Exception:
                        # TODO: если невозможно собрать payroll без большого рефакторинга,
                        # оставить payroll_inputs пустым.
                        pass
        
                    # Базовый список расходников по визиту.
                    try:
                        default_warehouse = await booking_erp.inventory_service.get_default_warehouse(
                            booking.clinic_id
                        )
                        if default_warehouse is not None:
                            consumables = await booking_erp.inventory_service.list_service_consumables(
                                clinic_id=booking.clinic_id,
                                service_id=booking.service_id,
                            )
                            for item in consumables:
                                inventory_items.append(
                                    ErpVisitInventoryItem(
                                        product_id=item.product_id,
                                        warehouse_id=default_warehouse.id,
                                        quantity=item.quantity_per_service,
                                        unit=item.unit,
                                    )
                                )
                    except Exception:
                        # TODO: если пока нельзя аккуратно связать визит и расходники — оставить список пустым.
                        pass
        
                    erp_node_request = ErpVisitNodeRequest(
                        booking_id=booking.id,
                        clinic_id=booking.clinic_id,
                        visit_date=now,
                        services=services,
                        payments=payments,
                        payroll_inputs=payroll_inputs,
                        inventory_items=inventory_items,
                    )
                    node_result = await self.erp_node_service.process_visit_completion(
                        erp_node_request,
                        session=self.session,
                    )
                    step_elapsed_erp = (datetime.now() - step_started_erp).total_seconds()
                    business_chain_booking_erp_step_duration_seconds.labels(
                        clinic_bucket=clinic_bucket_label(booking.clinic_id),
                        step="erp",
                    ).observe(step_elapsed_erp)
                    if not node_result.success:
                        raise ERPConfigurationError(
                            code=node_result.error_code or "erp_node_error",
                            message=node_result.error_message or "ERP node reported failure",
                        )
                    # If ERP node produced loyalty summary with inconsistency warnings,
                    # create an attention task so clinic owner can verify balances.
                    loyalty_write_off_summary = node_result.loyalty_summary
                    if (
                        loyalty_write_off_summary is not None
                        and "attempt_write_off_more_than_remaining"
                        in (loyalty_write_off_summary.warnings or [])
                    ):
                        try:
                            description = (
                                "Зафиксировано несоответствие ERP‑обязательства для подписки "
                                "при списании по визиту (attempt_write_off_more_than_remaining). "
                                "Проверьте остатки по подписке и ERP‑отчётности."
                            )
                            if _actor_trace_id(actor):
                                description += f" trace_id={_actor_trace_id(actor)}."
                            await self.task_service.create_task(
                                clinic_id=booking.clinic_id,
                                title="LOYALTY_ERP_INCONSISTENT_OBLIGATION",
                                description=description,
                                priority="high",
                                role_assignee="owner",
                                booking_id=booking.id,
                                patient_id=booking.patient_id,
                                source="system",
                                source_event_id=booking.id,
                                trace_id=_actor_trace_id(actor),
                            )
                        except Exception:
                            logger.exception(
                                "BookingCompletionService: failed to create loyalty/ERP inconsistency task",
                                extra={
                                    "booking_id": str(booking.id),
                                    "clinic_id": str(booking.clinic_id),
                                    "trace_id": _actor_trace_id(actor),
                                    "chain": "booking_to_erp",
                                    "step": "erp",
                                },
                            )
        
                    erp_result_dto = ErpBookingCompletionResult(
                        success=True,
                        booking_id=booking.id,
                        error_code=None,
                        error_message=None,
                        finance_transaction_ids=None,
                        payroll_transaction_ids=None,
                        inventory_movement_ids=None,
                        loyalty_write_off_summary=node_result.loyalty_summary,
                    )
                    erp_summary = erp_result_dto.model_dump()
                except LoyaltyVisitCompletionBlocked as e:
                    raise LoyaltyBlockingError(e, subscription_id=None) from e
                except ERPConfigurationError as exc:
                    raise ErpCompletionFailed(exc) from exc
                except Exception as exc:  # pragma: no cover
                    raise UnexpectedErpCompletionFailed(exc) from exc

                # ERP прошёл успешно — фиксируем факт обработки и переводим визит в completed.
                await self.status_service.transition(booking, BookingStatus.COMPLETED, context={})
                booking.erp_error_code = None
                await self.booking_repository.update(booking)

        except ErpCompletionFailed as w:
            return await self._handle_erp_configuration_error(booking, actor, w.exc, started_at)
        except UnexpectedErpCompletionFailed as w:
            return await self._handle_unexpected_erp_error(booking, actor, w.exc, started_at)
        except LoyaltyBlockingError as w:
            return await self._handle_loyalty_blocking(
                booking,
                actor,
                w.cause,
                started_at,
                subscription_id=w.subscription_id,
            )

        completed_event = make_booking_completed_event(
            booking,
            trace_id=getattr(actor, "trace_id", None),
            visit_revenue=None,
        )
        if settings.domain_outbox_booking_events_enabled:
            await enqueue_domain_event(self.session, completed_event)

        # Event subscribers (CRM, loyalty, …) open new DB sessions. Commit first so they
        # see ERP rows (e.g. financial_transactions) written in this transaction.
        await self.session.commit()

        # Publish BookingCompleted (in-process bus) or drain outbox after commit (ADR-009).
        logger.info(
            "BookingCompletionService: publishing BookingCompleted for CRM/subscribers",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(booking.clinic_id),
                "trace_id": _actor_trace_id(actor),
                "chain": "booking_to_erp",
                "step": "crm_publish",
            },
        )
        try:
            if not settings.domain_outbox_booking_events_enabled:
                event_bus = get_event_bus()
                await event_bus.publish(completed_event)
        except Exception:
            # Сохраняем успешное завершение, но добавляем предупреждение в сводку ERP.
            if erp_summary is None:
                erp_summary = {}
            erp_summary["event_bus_warning"] = "booking_completed_event_failed"

        elapsed = (datetime.now() - started_at).total_seconds()
        booking_completion_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id)
        ).observe(elapsed)
        business_chain_booking_erp_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id)
        ).observe(elapsed)

        logger.info(
            "BookingCompletionService: booking completed successfully",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(booking.clinic_id),
                "trace_id": _actor_trace_id(actor),
                "chain": "booking_to_erp",
                "step": "final",
            },
        )

        booking_completion_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            status="success",
        ).inc()
        business_chain_booking_erp_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            status="success",
        ).inc()

        return BookingCompletionResult(
            success=True,
            booking_id=booking.id,
            final_status=_booking_status_str(booking.status),
            erp_summary=erp_summary,
            loyalty_summary=loyalty_summary,
            warnings=[],
            error_code=None,
            error_message=None,
        )

    async def _handle_loyalty_blocking(
        self,
        booking: Booking,
        actor: RequestContext,
        exc: LoyaltyVisitCompletionBlocked,
        started_at: datetime,
        *,
        subscription_id: UUID | None = None,
    ) -> BookingCompletionResult:
        """Nested loyalty/ERP savepoint rolled back; booking stays non-completed; Task for clinic owner."""
        await self.session.refresh(booking)
        clinic_label = str(booking.clinic_id)
        booking_completion_attempts_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            status="loyalty_blocked",
        ).inc()
        booking_completion_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            error_type="loyalty_blocking",
        ).inc()
        business_chain_booking_erp_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            error_type="loyalty_blocking",
        ).inc()
        business_chain_booking_erp_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            status="loyalty_blocking",
        ).inc()
        try:
            description = (
                f"Loyalty rules blocked visit completion (code={exc.code}): {str(exc)}. "
                "Fix subscription/family access or adjust the visit before completing."
            )
            if _actor_trace_id(actor):
                description += f" trace_id={_actor_trace_id(actor)}."
            await self.task_service.create_task(
                clinic_id=booking.clinic_id,
                title="LOYALTY_MISMATCH",
                description=description,
                priority="high",
                role_assignee="owner",
                booking_id=booking.id,
                patient_id=booking.patient_id,
                source="system",
                source_event_id=booking.id,
                trace_id=_actor_trace_id(actor),
            )
        except Exception:
            logger.exception(
                "BookingCompletionService: failed to create LOYALTY_MISMATCH task",
                extra={
                    "booking_id": str(booking.id),
                    "clinic_id": str(booking.clinic_id),
                    "trace_id": _actor_trace_id(actor),
                },
            )
        elapsed = (datetime.now() - started_at).total_seconds()
        booking_completion_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(clinic_label)
        ).observe(elapsed)
        business_chain_booking_erp_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(clinic_label)
        ).observe(elapsed)

        loyalty_summary = LoyaltyWriteOffResult(
            success=False,
            booking_id=booking.id,
            subscription_id=subscription_id,
            error_code=exc.code,
            error_message=str(exc),
            remaining_visits=None,
            remaining_amount=None,
        ).model_dump()

        return BookingCompletionResult(
            success=False,
            booking_id=booking.id,
            final_status=_booking_status_str(booking.status),
            erp_summary=None,
            loyalty_summary=loyalty_summary,
            warnings=[],
            error_code=exc.code,
            error_message=str(exc),
        )

    async def _handle_erp_configuration_error(
        self,
        booking: Booking,
        actor: RequestContext,
        exc: ERPConfigurationError,
        started_at: datetime,
    ) -> BookingCompletionResult:
        """After nested rollback: persist ERP error on booking, metrics, task, structured failure."""
        await self.session.refresh(booking)
        booking_completion_errors_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            error_type="erp_configuration_error",
        ).inc()
        business_chain_booking_erp_errors_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            error_type="erp_configuration_error",
        ).inc()
        error_type = self._classify_erp_error_code(exc.code)
        chain_error_type = self._map_erp_error_type_for_chain(exc.code)
        business_chain_booking_erp_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            status=chain_error_type,
        ).inc()
        business_chain_booking_erp_errors_total.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id),
            error_type=chain_error_type,
        ).inc()
        booking.erp_error_code = exc.code
        await self.booking_repository.update(booking)
        try:
            description = (
                f"Не удалось провести визит в ERP (код: {exc.code}, "
                f"тип: {error_type.upper()}). "
                "Проверьте настройки кассы/ЗП/склада и перепроведите визит."
            )
            if _actor_trace_id(actor):
                description += f" trace_id={_actor_trace_id(actor)}."
            await self.task_service.create_task(
                clinic_id=booking.clinic_id,
                title="ERP‑ошибка при завершении визита",
                description=description,
                priority="high",
                role_assignee="owner",
                booking_id=booking.id,
                patient_id=booking.patient_id,
                source="system",
                source_event_id=booking.id,
                trace_id=_actor_trace_id(actor),
            )
        except Exception:
            logger.exception(
                "BookingCompletionService: failed to create ERP failure task",
                extra={
                    "booking_id": str(booking.id),
                    "clinic_id": str(booking.clinic_id),
                    "error_code": exc.code,
                    "trace_id": _actor_trace_id(actor),
                    "chain": "booking_to_erp",
                    "step": "erp",
                },
            )
        logger.error(
            "BookingCompletionService: ERP configuration error during completion",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(booking.clinic_id),
                "error_code": exc.code,
                "error_message": str(exc),
                "chain": "booking_to_erp",
                "step": "erp",
                "status": chain_error_type,
                "error_type": error_type,
            },
        )
        elapsed = (datetime.now() - started_at).total_seconds()
        booking_completion_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id)
        ).observe(elapsed)
        business_chain_booking_erp_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(booking.clinic_id)
        ).observe(elapsed)

        erp_result_dto = ErpBookingCompletionResult(
            success=False,
            booking_id=booking.id,
            error_code=exc.code,
            error_type=error_type,
            error_message=str(exc),
            finance_transaction_ids=None,
            payroll_transaction_ids=None,
            inventory_movement_ids=None,
            loyalty_write_off_summary=None,
        )
        erp_summary = erp_result_dto.model_dump()

        return BookingCompletionResult(
            success=False,
            booking_id=booking.id,
            final_status=_booking_status_str(booking.status),
            erp_summary=erp_summary,
            loyalty_summary=None,
            warnings=[],
            error_code=exc.code,
            error_message=str(exc),
        )

    async def _handle_unexpected_erp_error(
        self,
        booking: Booking,
        actor: RequestContext,
        exc: Exception,
        started_at: datetime,
    ) -> BookingCompletionResult:
        await self.session.refresh(booking)
        clinic_label = str(booking.clinic_id)
        booking_completion_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            error_type="erp_unexpected_error",
        ).inc()
        business_chain_booking_erp_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            error_type="erp_unexpected_error",
        ).inc()
        business_chain_booking_erp_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            status="erp_unexpected",
        ).inc()
        business_chain_booking_erp_errors_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_label),
            error_type="erp_unexpected",
        ).inc()
        logger.exception(
            "BookingCompletionService: unexpected ERP error during completion",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(booking.clinic_id),
                "chain": "booking_to_erp",
                "step": "erp",
                "status": "erp_unexpected",
                "error_type": "erp_unexpected",
            },
        )
        elapsed = (datetime.now() - started_at).total_seconds()
        booking_completion_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(clinic_label)
        ).observe(elapsed)
        business_chain_booking_erp_duration_seconds.labels(
            clinic_bucket=clinic_bucket_label(clinic_label)
        ).observe(elapsed)

        erp_result_dto = ErpBookingCompletionResult(
            success=False,
            booking_id=booking.id,
            error_code="unexpected_error",
            error_type="unexpected",
            error_message=str(exc),
            finance_transaction_ids=None,
            payroll_transaction_ids=None,
            inventory_movement_ids=None,
            loyalty_write_off_summary=None,
        )
        erp_summary = erp_result_dto.model_dump()

        return BookingCompletionResult(
            success=False,
            booking_id=booking.id,
            final_status=_booking_status_str(booking.status),
            erp_summary=erp_summary,
            loyalty_summary=None,
            warnings=[],
            error_code="unexpected_error",
            error_message=str(exc),
        )

    @staticmethod
    def _classify_erp_error_code(code: str | None) -> str:
        if not code:
            return "unexpected"
        lowered = code.lower()
        if "cashbox" in lowered or "finance" in lowered or "payment" in lowered:
            return "finance"
        if "payroll" in lowered or "salary" in lowered or "policy" in lowered:
            return "payroll"
        if "warehouse" in lowered or "stock" in lowered or "inventory" in lowered:
            return "inventory"
        if "validation" in lowered or lowered.startswith("validation_"):
            return "validation"
        return "unexpected"

    @staticmethod
    def _map_erp_error_type_for_chain(code: str | None) -> str:
        """
        Map low-level ERP error code to OBS chain error_type series
        used in business_chain_booking_erp_errors_total (label clinic_bucket, not raw clinic_id).
        """
        base = BookingCompletionService._classify_erp_error_code(code)
        if base == "finance":
            return "erp_finance"
        if base == "payroll":
            return "erp_payroll"
        if base == "inventory":
            return "erp_inventory"
        if base == "validation":
            return "erp_validation"
        return "erp_unexpected"

