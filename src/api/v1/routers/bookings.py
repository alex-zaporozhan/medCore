"""Bookings API router."""

import logging
from datetime import date
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import (
    get_current_patient,
    get_session_booking_domain_outbox,
    get_request_context,
    require_permissions,
)
from src.application.dto.booking_dto import (
    BookingAdminSetStatusBody,
    BookingCreateAdmin,
    BookingCreatePatient,
    BookingPatchAdmin,
    BookingRead,
    BookingRescheduleRequest,
    CheckoutInfoResponse,
    CompleteBookingRequest,
    EligibleSubscriptionItem,
    BookingCompletionResult,
    BookingErrorResponse,
    BookingErrorCode,
)
from src.application.multitenancy import ClinicForbiddenError
from src.application.services.multitenancy_alert_service import record_multitenancy_mismatch_for_admin
from src.api.v1.multitenancy_http import clinic_forbidden_admin_detail
from src.core.patient_messages import BOOKING_INVALID_STATUS, BOOKING_NOT_FOUND
from src.core.context import RequestContext
from src.application.dto.card_dto import (
    BookingCardConsumableItem,
    BookingCardResponse,
    BookingCardServiceItem,
    BookingCardTaskItem,
)
from src.application.services.booking_service import BookingService
from src.application.services.booking_completion_service import (
    BookingCompletionService,
    booking_completion_erp_retry_total,
)
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.booking import Booking, BookingStatus
from src.application.errors import (
    booking_error_from_completion_result,
    booking_error_from_value_error,
)
from src.application.booking_error_observability import record_booking_error_event
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bookings"])

BOOKING_ERROR_OPENAPI = {
    400: {"model": BookingErrorResponse, "description": "Business validation / slot / status"},
    404: {"model": BookingErrorResponse, "description": "Booking not found (structured body)"},
}


async def _emit_booking_api_error(
    status: int,
    error: BookingErrorResponse,
    clinic_id: UUID,
) -> NoReturn:
    await record_booking_error_event(
        clinic_id=clinic_id,
        code=error.code,
        source="api",
        trace_id=error.trace_id,
    )
    raise HTTPException(status_code=status, detail=error.model_dump())


def _booking_error_from_value_error(exc: ValueError, ctx: RequestContext | None) -> BookingErrorResponse:
    # For backwards compatibility within this module, delegate to shared helper.
    return booking_error_from_value_error(exc, ctx)


def _booking_not_found_error(ctx: RequestContext | None) -> BookingErrorResponse:
    return BookingErrorResponse(
        code=BookingErrorCode.BOOKING_NOT_FOUND,
        message=BOOKING_NOT_FOUND,
        trace_id=getattr(ctx, "trace_id", None) if ctx is not None else None,
    )


@router.get(
    "/patient/bookings",
    response_model=list[BookingRead],
)
async def get_patient_bookings(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_patient=Depends(get_current_patient),
):
    """Get bookings for current patient."""
    service = BookingService(session)
    return await service.get_patient_bookings(patient_id=current_patient.id, skip=skip, limit=limit)


@router.post(
    "/patient/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: BOOKING_ERROR_OPENAPI[400]},
)
async def create_patient_booking(
    data: BookingCreatePatient,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_patient=Depends(get_current_patient),
    context: RequestContext = Depends(get_request_context),
):
    """Create booking from patient flow (status pending)."""
    service = BookingService(session)
    try:
        booking = await service.create_patient_booking(
            patient_id=current_patient.id,
            patient_clinic_id=current_patient.clinic_id,
            data=data,
            context=context,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            data.clinic_id,
        )
    return booking


@router.delete(
    "/patient/bookings/{booking_id}",
    response_model=BookingRead,
    responses={400: BOOKING_ERROR_OPENAPI[400], 404: BOOKING_ERROR_OPENAPI[404]},
)
async def cancel_own_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_patient=Depends(get_current_patient),
    context: RequestContext = Depends(get_request_context),
):
    """Cancel own booking."""
    service = BookingService(session)
    try:
        booking = await service.cancel_booking(
            clinic_id=current_patient.clinic_id,
            booking_id=booking_id,
            context=context,
        )
    except ClinicForbiddenError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_patient.clinic_id,
        )
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_patient.clinic_id,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_patient.clinic_id,
        )

    if booking.patient_id != current_patient.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel other patient's booking")

    logger.info(
        "Patient cancelled own booking",
        extra={"booking_id": str(booking_id), "patient_id": str(current_patient.id)},
    )
    return booking


@router.get(
    "/admin/bookings/{booking_id}/checkout-info",
    response_model=CheckoutInfoResponse,
)
async def get_booking_checkout_info(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
) -> CheckoutInfoResponse:
    """Eligible subscriptions for this booking (Checkout Hub)."""
    from src.domain.entities.booking import Booking
    from src.application.services.loyalty_service import LoyaltyService
    from datetime import datetime

    result = await session.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.clinic_id == current_admin.clinic_id,
            Booking.deleted_at.is_(None),
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    loyalty = LoyaltyService(session)
    eligible = await loyalty.get_eligible_subscriptions_for_booking(
        clinic_id=booking.clinic_id,
        patient_id=booking.patient_id,
        service_id=booking.service_id,
        on_date=datetime.now(),
    )
    items = [
        EligibleSubscriptionItem(
            customer_subscription_id=sub.id,
            package_name=pkg.name,
            remaining_visits=sub.remaining_visits,
            remaining_amount=sub.remaining_amount,
        )
        for sub, pkg in eligible
    ]
    return CheckoutInfoResponse(eligible_subscriptions=items)


@router.get(
    "/admin/bookings/{booking_id}/card",
    response_model=BookingCardResponse,
)
async def get_booking_card(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
) -> BookingCardResponse:
    """Rich booking card for drawer: booking, services, consumables, tasks."""
    from src.domain.entities.booking import Booking
    from src.domain.entities.service import Service
    from src.domain.entities.service_consumable import ServiceConsumable
    from src.domain.entities.task import Task
    from src.domain.entities.product import Product

    result = await session.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.clinic_id == current_admin.clinic_id,
            Booking.deleted_at.is_(None),
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    booking_dict = BookingRead.model_validate(booking).model_dump()

    # Single service for this booking
    svc_result = await session.execute(select(Service).where(Service.id == booking.service_id))
    service = svc_result.scalar_one_or_none()
    services = [
        BookingCardServiceItem(
            service_id=booking.service_id,
            service_name=service.name if service else "",
            amount=booking.prepayment_amount,
        )
    ]

    # Consumables for this service (technocard)
    cons_result = await session.execute(
        select(ServiceConsumable, Product.name).join(
            Product, Product.id == ServiceConsumable.product_id
        ).where(
            ServiceConsumable.service_id == booking.service_id,
            ServiceConsumable.clinic_id == current_admin.clinic_id,
        )
    )
    consumables = [
        BookingCardConsumableItem(
            product_id=sc.product_id,
            product_name=pname,
            quantity_per_service=sc.quantity_per_service,
            unit=sc.unit,
        )
        for sc, pname in cons_result.all()
    ]

    # Tasks linked to this booking
    task_result = await session.execute(
        select(Task).where(
            Task.booking_id == booking_id,
            Task.clinic_id == current_admin.clinic_id,
        )
    )
    tasks = [
        BookingCardTaskItem(
            id=t.id,
            title=t.title,
            status=t.status,
            priority=t.priority,
            due_at=t.due_at,
        )
        for t in task_result.scalars().all()
    ]

    return BookingCardResponse(
        booking=booking_dict,
        services=services,
        consumables=consumables,
        tasks=tasks,
    )


@router.get(
    "/admin/bookings",
    response_model=list[BookingRead],
)
async def get_admin_bookings(
    doctor_id: UUID | None = None,
    date_filter: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    patient_phone: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin search for bookings with filters."""
    service = BookingService(session)
    try:
        bookings = await service.search_admin_bookings(
            clinic_id=current_admin.clinic_id,
            doctor_id=doctor_id,
            date_filter=date_filter,
            status=status_filter,
            patient_phone=patient_phone,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        # For now keep generic 400 without BookingErrorResponse as it's a filter error,
        # not a booking/payment lifecycle error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return bookings


@router.post(
    "/admin/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: BOOKING_ERROR_OPENAPI[400]},
)
async def create_admin_booking(
    data: BookingCreateAdmin,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """Create booking from admin side. Optionally pass waitlist_entry_id to convert a waitlist entry."""
    service = BookingService(session)
    try:
        booking = await service.create_admin_booking(
            current_admin.clinic_id,
            data,
            context=context,
        )
    except LookupError as exc:
        # For waitlist-specific errors keep existing behavior for admin UX.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )
    return booking


@router.put(
    "/admin/bookings/{booking_id}/cancel",
    response_model=BookingRead,
    responses={400: BOOKING_ERROR_OPENAPI[400], 404: BOOKING_ERROR_OPENAPI[404]},
)
async def cancel_booking_admin(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """Admin cancel booking."""
    service = BookingService(session)
    try:
        booking = await service.cancel_booking(
            current_admin.clinic_id,
            booking_id,
            context=context,
        )
    except ClinicForbiddenError as exc:
        await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, context),
        ) from exc
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_admin.clinic_id,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )
    return booking


@router.put(
    "/admin/bookings/{booking_id}/complete",
    response_model=BookingCompletionResult,
    dependencies=[Depends(require_permissions("manage_finance"))],
    responses={
        400: BOOKING_ERROR_OPENAPI[400],
        404: BOOKING_ERROR_OPENAPI[404],
    },
)
async def complete_booking_admin(
    booking_id: UUID,
    request: Request,
    body: CompleteBookingRequest | None = Body(None),
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Admin mark booking as completed via unified completion facade.

    RBAC: доступ только для админских ролей с пермишеном `manage_finance`,
    так как операция завершения визита приводит к денежным/ERP‑движениям.
    """
    trace_id = getattr(request.state, "trace_id", None)
    completion_service = BookingCompletionService(session)
    use_subscription_id = body.use_subscription_id if body else None
    result = await completion_service.complete_visit(
        booking_id=booking_id,
        actor=current_admin,  # current_admin implements RequestContext-ish fields
        use_subscription_id=use_subscription_id,
    )
    if not result.success:
        err = booking_error_from_completion_result(result, None, trace_id=trace_id)
        await record_booking_error_event(
            clinic_id=current_admin.clinic_id,
            code=err.code,
            source="api",
            trace_id=err.trace_id,
        )
        status_code = (
            status.HTTP_404_NOT_FOUND
            if result.error_code == "booking_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=err.model_dump())
    return result


@router.put(
    "/admin/bookings/{booking_id}/complete/retry",
    response_model=BookingCompletionResult,
    dependencies=[Depends(require_permissions("manage_finance"))],
    responses={
        400: BOOKING_ERROR_OPENAPI[400],
        404: BOOKING_ERROR_OPENAPI[404],
    },
)
async def retry_complete_booking_admin(
    booking_id: UUID,
    request: Request,
    body: CompleteBookingRequest | None = Body(None),
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Retry posting a visit to ERP after a previous failure left ``erp_error_code`` set (BKG_CORE G4).
    """
    trace_id = getattr(request.state, "trace_id", None)
    b = await session.get(Booking, booking_id)
    if not b or b.clinic_id != current_admin.clinic_id:
        err = BookingErrorResponse(
            code=BookingErrorCode.BOOKING_NOT_FOUND,
            message=BOOKING_NOT_FOUND,
            trace_id=trace_id,
        )
        await record_booking_error_event(
            clinic_id=current_admin.clinic_id,
            code=err.code,
            source="api",
            trace_id=err.trace_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.model_dump())
    if b.erp_error_code is None:
        err = BookingErrorResponse(
            code=BookingErrorCode.VALIDATION_ERROR,
            message="No pending ERP error on this booking; use PUT /admin/bookings/{id}/complete.",
            details={"reason": "no_pending_erp_error"},
            trace_id=trace_id,
        )
        await record_booking_error_event(
            clinic_id=current_admin.clinic_id,
            code=err.code,
            source="api",
            trace_id=err.trace_id,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.model_dump())
    logger.info(
        "booking_complete_erp_retry_attempt",
        extra={
            "booking_id": str(booking_id),
            "clinic_id": str(b.clinic_id),
            "previous_erp_error_code": b.erp_error_code,
        },
    )
    booking_completion_erp_retry_total.labels(
        clinic_bucket=clinic_bucket_label(str(b.clinic_id)),
    ).inc()
    completion_service = BookingCompletionService(session)
    use_subscription_id = body.use_subscription_id if body else None
    result = await completion_service.complete_visit(
        booking_id=booking_id,
        actor=current_admin,
        use_subscription_id=use_subscription_id,
    )
    if not result.success:
        err = booking_error_from_completion_result(result, None, trace_id=trace_id)
        await record_booking_error_event(
            clinic_id=current_admin.clinic_id,
            code=err.code,
            source="api",
            trace_id=err.trace_id,
        )
        status_code = (
            status.HTTP_404_NOT_FOUND
            if result.error_code == "booking_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=err.model_dump())
    return result


@router.put(
    "/admin/bookings/{booking_id}/mark-no-show",
    response_model=BookingRead,
    responses={400: BOOKING_ERROR_OPENAPI[400], 404: BOOKING_ERROR_OPENAPI[404]},
)
async def mark_no_show_admin(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """Admin mark booking as no_show."""
    service = BookingService(session)
    try:
        booking = await service.mark_no_show(current_admin.clinic_id, booking_id, context=context)
    except ClinicForbiddenError as exc:
        await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, context),
        ) from exc
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_admin.clinic_id,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )
    return booking


@router.put(
    "/admin/bookings/{booking_id}/status",
    response_model=BookingRead,
    responses={
        400: BOOKING_ERROR_OPENAPI[400],
        403: {"description": "Нет права manage_finance для завершения визита (status=completed)"},
        404: BOOKING_ERROR_OPENAPI[404],
    },
)
async def set_booking_status_admin(
    booking_id: UUID,
    body: BookingAdminSetStatusBody,
    request: Request,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """
    Смена статуса админом: cancel / complete / no_show делегируются узким сервисам;
    прочие переходы — через state machine без «тихого» PATCH.
    """
    try:
        target = BookingStatus(body.status)
    except ValueError:
        error = _booking_error_from_value_error(ValueError(BOOKING_INVALID_STATUS), context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )

    service = BookingService(session)

    if target == BookingStatus.CANCELLED:
        try:
            return await service.cancel_booking(
                current_admin.clinic_id,
                booking_id,
                context=context,
            )
        except ClinicForbiddenError as exc:
            await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=clinic_forbidden_admin_detail(exc, context),
            ) from exc
        except LookupError:
            error = _booking_not_found_error(context)
            await _emit_booking_api_error(
                status.HTTP_404_NOT_FOUND,
                error,
                current_admin.clinic_id,
            )
        except ValueError as exc:
            error = _booking_error_from_value_error(exc, context)
            await _emit_booking_api_error(
                status.HTTP_400_BAD_REQUEST,
                error,
                current_admin.clinic_id,
            )

    if target == BookingStatus.NO_SHOW:
        try:
            return await service.mark_no_show(current_admin.clinic_id, booking_id, context=context)
        except ClinicForbiddenError as exc:
            await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=clinic_forbidden_admin_detail(exc, context),
            ) from exc
        except LookupError:
            error = _booking_not_found_error(context)
            await _emit_booking_api_error(
                status.HTTP_404_NOT_FOUND,
                error,
                current_admin.clinic_id,
            )
        except ValueError as exc:
            error = _booking_error_from_value_error(exc, context)
            await _emit_booking_api_error(
                status.HTTP_400_BAD_REQUEST,
                error,
                current_admin.clinic_id,
            )

    if target == BookingStatus.COMPLETED:
        if "manage_finance" not in context.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        trace_id = getattr(request.state, "trace_id", None)
        completion_service = BookingCompletionService(session)
        result = await completion_service.complete_visit(
            booking_id=booking_id,
            actor=current_admin,
            use_subscription_id=body.use_subscription_id,
        )
        if not result.success:
            err = booking_error_from_completion_result(result, None, trace_id=trace_id)
            await record_booking_error_event(
                clinic_id=current_admin.clinic_id,
                code=err.code,
                source="api",
                trace_id=err.trace_id,
            )
            status_code = (
                status.HTTP_404_NOT_FOUND
                if result.error_code == "booking_not_found"
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(status_code=status_code, detail=err.model_dump())
        row = await session.get(Booking, booking_id)
        if row is None or row.clinic_id != current_admin.clinic_id:
            error = _booking_not_found_error(context)
            await _emit_booking_api_error(
                status.HTTP_404_NOT_FOUND,
                error,
                current_admin.clinic_id,
            )
        return BookingRead.model_validate(row)

    try:
        return await service.transition_booking_status_admin_light(
            current_admin.clinic_id,
            booking_id,
            target,
            context=context,
        )
    except ClinicForbiddenError as exc:
        await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, context),
        ) from exc
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_admin.clinic_id,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )


@router.patch(
    "/admin/bookings/{booking_id}",
    response_model=BookingRead,
    responses={400: BOOKING_ERROR_OPENAPI[400], 404: BOOKING_ERROR_OPENAPI[404]},
)
async def patch_booking_admin(
    booking_id: UUID,
    data: BookingPatchAdmin,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """P2: частичное обновление записи (комментарий администратора)."""
    service = BookingService(session)
    try:
        booking = await service.patch_booking_admin(current_admin.clinic_id, booking_id, data)
    except ClinicForbiddenError as exc:
        await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, context),
        ) from exc
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_admin.clinic_id,
        )
    return booking


@router.put(
    "/admin/bookings/{booking_id}/reschedule",
    response_model=BookingRead,
    responses={400: BOOKING_ERROR_OPENAPI[400], 404: BOOKING_ERROR_OPENAPI[404]},
)
async def reschedule_booking_admin(
    booking_id: UUID,
    data: BookingRescheduleRequest,
    session: AsyncSession = Depends(get_session_booking_domain_outbox),
    current_admin: AdminUser = Depends(get_current_admin),
    context: RequestContext = Depends(get_request_context),
):
    """Admin reschedule booking (optionally to another doctor via to_doctor_id)."""
    service = BookingService(session)
    try:
        booking = await service.reschedule_booking(current_admin.clinic_id, booking_id, data)
    except ClinicForbiddenError as exc:
        await record_multitenancy_mismatch_for_admin(session, current_admin, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, context),
        ) from exc
    except LookupError:
        error = _booking_not_found_error(context)
        await _emit_booking_api_error(
            status.HTTP_404_NOT_FOUND,
            error,
            current_admin.clinic_id,
        )
    except ValueError as exc:
        error = _booking_error_from_value_error(exc, context)
        await _emit_booking_api_error(
            status.HTTP_400_BAD_REQUEST,
            error,
            current_admin.clinic_id,
        )
    return booking

