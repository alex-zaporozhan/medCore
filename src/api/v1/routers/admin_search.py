"""Admin global search (Spotlight). B5.1."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient

router = APIRouter(prefix="/admin", tags=["admin-search"])


class SearchSectionItem(BaseModel):
    label: str
    path: str


class SearchPatientItem(BaseModel):
    id: UUID
    full_name: str | None
    phone: str


class SearchBookingItem(BaseModel):
    id: UUID
    patient_name: str | None
    date: date


class GlobalSearchResponse(BaseModel):
    sections: list[SearchSectionItem]
    patients: list[SearchPatientItem]
    bookings: list[SearchBookingItem]


# Static nav sections for Spotlight (B5.1)
DEFAULT_SECTIONS = [
    SearchSectionItem(label="Дашборд", path="/admin"),
    SearchSectionItem(label="Записи", path="/admin/bookings"),
    SearchSectionItem(label="Пациенты", path="/admin/patients"),
    SearchSectionItem(label="Врачи", path="/admin/doctors"),
    SearchSectionItem(label="Услуги", path="/admin/services"),
    SearchSectionItem(label="CRM", path="/admin/crm"),
    SearchSectionItem(label="Задачи", path="/admin/tasks"),
    SearchSectionItem(label="Финансы", path="/admin/finance"),
    SearchSectionItem(label="Лист ожидания", path="/admin/waitlist"),
    SearchSectionItem(label="Настройки", path="/admin/settings"),
]


@router.get("/search", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("view_crm")),
) -> GlobalSearchResponse:
    """Global search for Spotlight: sections (static) + patients (name/phone) + bookings (patient name, date). ACL: current clinic only."""
    clinic_id = current_admin.clinic_id
    if not clinic_id:
        return GlobalSearchResponse(sections=DEFAULT_SECTIONS, patients=[], bookings=[])

    pattern = f"%{q.strip()}%"
    patients: list[SearchPatientItem] = []
    bookings: list[SearchBookingItem] = []

    # Patients: LIKE full_name or phone
    patient_stmt = (
        select(Patient)
        .where(
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
            (Patient.full_name.ilike(pattern) | Patient.phone.ilike(pattern)),
        )
        .limit(limit)
    )
    patient_result = await session.execute(patient_stmt)
    for p in patient_result.scalars().all():
        patients.append(
            SearchPatientItem(id=p.id, full_name=p.full_name, phone=p.phone or "")
        )

    # Bookings: join Patient for name; filter by patient name/phone or booking id
    booking_cond = Patient.full_name.ilike(pattern) | Patient.phone.ilike(pattern)
    try:
        bid_uuid = UUID(q.strip())
        booking_cond = booking_cond | (Booking.id == bid_uuid)
    except ValueError:
        pass
    booking_stmt = (
        select(Booking, Patient.full_name)
        .join(Patient, Patient.id == Booking.patient_id)
        .where(
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
            booking_cond,
        )
        .order_by(Booking.appointment_date.desc(), Booking.appointment_time.desc())
        .limit(limit)
    )
    booking_result = await session.execute(booking_stmt)
    for b, pname in booking_result.all():
        bookings.append(
            SearchBookingItem(id=b.id, patient_name=pname, date=b.appointment_date)
        )

    return GlobalSearchResponse(
        sections=DEFAULT_SECTIONS,
        patients=patients,
        bookings=bookings,
    )
