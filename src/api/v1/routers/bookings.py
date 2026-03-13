"""Bookings API router."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.application.dto.booking_dto import (
    BookingCreateAdmin,
    BookingCreatePatient,
    BookingRead,
    BookingRescheduleRequest,
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
    """Create booking from admin side."""
    service = BookingService(session)
    try:
        booking = await service.create_admin_booking(current_admin.clinic_id, data)
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
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Admin mark booking as completed."""
    service = BookingService(session)
    try:
        booking = await service.complete_booking(current_admin.clinic_id, booking_id)
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

