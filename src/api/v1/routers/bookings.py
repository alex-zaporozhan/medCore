"""Bookings API router."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.application.dto.booking_dto import (
    BookingCreateAdmin,
    BookingCreatePatient,
    BookingRead,
    BookingRescheduleRequest,
    CheckoutInfoResponse,
    CompleteBookingRequest,
    EligibleSubscriptionItem,
)
from src.application.dto.card_dto import (
    BookingCardConsumableItem,
    BookingCardResponse,
    BookingCardServiceItem,
    BookingCardTaskItem,
)
from src.application.services.booking_service import BookingService
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bookings"])


@router.get(
    "/patient/bookings",
    response_model=list[BookingRead],
)
async def get_patient_bookings(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    """Get bookings for current patient."""
    service = BookingService(session)
    return await service.get_patient_bookings(patient_id=current_patient.id, skip=skip, limit=limit)


@router.post(
    "/patient/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_patient_booking(
    data: BookingCreatePatient,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    """Create booking from patient flow (status pending)."""
    service = BookingService(session)
    try:
        booking = await service.create_patient_booking(patient_id=current_patient.id, data=data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return booking


@router.delete(
    "/patient/bookings/{booking_id}",
    response_model=BookingRead,
)
async def cancel_own_booking(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_patient=Depends(get_current_patient),
):
    """Cancel own booking."""
    service = BookingService(session)
    try:
        booking = await service.cancel_booking(booking_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return bookings


@router.post(
    "/admin/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_booking(
    data: BookingCreateAdmin,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Create booking from admin side. Optionally pass waitlist_entry_id to convert a waitlist entry."""
    service = BookingService(session)
    try:
        booking = await service.create_admin_booking(current_admin.clinic_id, data)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return booking


@router.put(
    "/admin/bookings/{booking_id}/cancel",
    response_model=BookingRead,
)
async def cancel_booking_admin(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin cancel booking."""
    service = BookingService(session)
    try:
        booking = await service.cancel_booking(current_admin.clinic_id, booking_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return booking


@router.put(
    "/admin/bookings/{booking_id}/complete",
    response_model=BookingRead,
)
async def complete_booking_admin(
    booking_id: UUID,
    body: CompleteBookingRequest | None = Body(None),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin mark booking as completed. Optional use_subscription_id to apply specific package."""
    service = BookingService(session)
    use_subscription_id = body.use_subscription_id if body else None
    try:
        booking = await service.complete_booking(
            current_admin.clinic_id, booking_id, use_subscription_id=use_subscription_id
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return booking


@router.put(
    "/admin/bookings/{booking_id}/mark-no-show",
    response_model=BookingRead,
)
async def mark_no_show_admin(
    booking_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin mark booking as no_show."""
    service = BookingService(session)
    try:
        booking = await service.mark_no_show(current_admin.clinic_id, booking_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return booking


@router.put(
    "/admin/bookings/{booking_id}/reschedule",
    response_model=BookingRead,
)
async def reschedule_booking_admin(
    booking_id: UUID,
    data: BookingRescheduleRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin reschedule booking (optionally to another doctor via to_doctor_id)."""
    service = BookingService(session)
    try:
        booking = await service.reschedule_booking(current_admin.clinic_id, booking_id, data)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return booking

