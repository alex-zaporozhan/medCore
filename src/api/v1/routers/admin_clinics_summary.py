"""Admin endpoints: patient and doctor summary for HoverCard (Zero-Click Context)."""

from __future__ import annotations

from datetime import date, datetime, time as dtime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.chat_dto import MessagesResponse
from src.application.services.chat_service import ChatService
from src.application.dto.card_dto import (
    DoctorCardPayrollItem,
    DoctorCardResponse,
    DoctorCardServiceDoctorItem,
    DoctorCardWorkingHoursItem,
    PatientCardCommItem,
    PatientCardFinanceItem,
    PatientCardPatient,
    PatientCardResponse,
    PatientCardVisitItem,
)
from src.application.dto.summary_dto import DoctorSummaryRead, PatientSummaryRead
from src.domain.entities.booking import Booking
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.notification import Notification
from src.domain.entities.patient import Patient
from src.domain.entities.payment import Payment
from src.domain.entities.payroll_policy import PayrollPolicy
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.domain.entities.wallet import Wallet

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-summary"],
    dependencies=[Depends(require_permissions("view_crm"))],
)


class MarketingInsightsResponse(BaseModel):
    """Stub response for GET marketing/insights (B4.5)."""

    insights: list[str]


@router.get(
    "/{clinic_id}/patients/{patient_id}/summary",
    response_model=PatientSummaryRead,
)
async def get_patient_summary(
    clinic_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> PatientSummaryRead:
    """Get lightweight patient summary for HoverCard. ACL: patient must belong to clinic."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    # LTV: sum of succeeded payments for this patient's bookings
    ltv_result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).select_from(Payment).join(
            Booking, Booking.id == Payment.booking_id
        ).where(
            Booking.patient_id == patient_id,
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
            Payment.status == "succeeded",
        )
    )
    ltv = Decimal(str(ltv_result.scalar() or 0))

    # Next visit: nearest future booking (pending/confirmed)
    today = date.today()
    next_result = await session.execute(
        select(Booking, Doctor.full_name)
        .join(Doctor, Doctor.id == Booking.doctor_id)
        .where(
            Booking.patient_id == patient_id,
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
            Booking.status.in_(["pending", "confirmed"]),
            (Booking.appointment_date > today) | (
                (Booking.appointment_date == today) & (Booking.appointment_time >= dtime(0, 0))
            ),
        )
        .order_by(Booking.appointment_date.asc(), Booking.appointment_time.asc())
        .limit(1)
    )
    row = next_result.one_or_none()
    next_visit_at: datetime | None = None
    next_visit_doctor_name: str | None = None
    if row:
        booking, doctor_name = row
        next_visit_at = datetime.combine(
            booking.appointment_date,
            booking.appointment_time,
            tzinfo=timezone.utc,
        )
        next_visit_doctor_name = doctor_name

    return PatientSummaryRead(
        id=patient.id,
        full_name=patient.full_name,
        phone=patient.phone,
        ltv=ltv,
        next_visit_at=next_visit_at,
        next_visit_doctor_name=next_visit_doctor_name,
    )


@router.get(
    "/{clinic_id}/patients/{patient_id}/messages",
    response_model=MessagesResponse,
)
async def get_patient_messages(
    clinic_id: UUID,
    patient_id: UUID,
    limit: int = Query(20, ge=1, le=200),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> MessagesResponse:
    """Last messages of the patient's chat (Communications tab). Returns items + next_cursor; 404 if patient not in clinic."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    cursor_uuid: UUID | None = None
    if cursor:
        try:
            cursor_uuid = UUID(cursor)
        except (ValueError, TypeError):
            cursor_uuid = None

    service = ChatService(session)
    return await service.list_messages_for_admin_by_patient(
        clinic_id=clinic_id,
        patient_id=patient_id,
        cursor=cursor_uuid,
        limit=limit,
    )


@router.get(
    "/{clinic_id}/doctors/{doctor_id}/summary",
    response_model=DoctorSummaryRead,
)
async def get_doctor_summary(
    clinic_id: UUID,
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> DoctorSummaryRead:
    """Get lightweight doctor summary for HoverCard. ACL: doctor must belong to clinic."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or not in clinic")

    result = await session.execute(
        select(Doctor).where(
            Doctor.id == doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
        )
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or not in clinic")

    return DoctorSummaryRead(
        id=doctor.id,
        full_name=doctor.full_name,
        phone=None,
        specialization=doctor.specialization,
    )


@router.get(
    "/{clinic_id}/patients/{patient_id}/card",
    response_model=PatientCardResponse,
)
async def get_patient_card(
    clinic_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> PatientCardResponse:
    """Rich patient card for drawer: patient, visits, finances, notes, comms."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or not in clinic")

    # LTV
    ltv_result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).select_from(Payment).join(
            Booking, Booking.id == Payment.booking_id
        ).where(
            Booking.patient_id == patient_id,
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
            Payment.status == "succeeded",
        )
    )
    ltv = Decimal(str(ltv_result.scalar() or 0))

    # Bonus balance (wallet)
    wallet_result = await session.execute(
        select(Wallet.balance).where(
            Wallet.patient_id == patient_id,
            Wallet.clinic_id == clinic_id,
        )
    )
    bonus_balance = Decimal(str(wallet_result.scalar() or 0))

    patient_block = PatientCardPatient(
        id=patient.id,
        full_name=patient.full_name,
        phone=patient.phone,
        email=patient.email,
        ltv=ltv,
        bonus_balance=bonus_balance,
        tags=[],
    )

    # Visits: bookings with doctor_name, service_name, amount, nps
    visits_stmt = (
        select(Booking, Doctor.full_name, Service.name)
        .join(Doctor, Doctor.id == Booking.doctor_id)
        .join(Service, Service.id == Booking.service_id)
        .where(
            Booking.patient_id == patient_id,
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
        )
        .order_by(Booking.appointment_date.desc(), Booking.appointment_time.desc())
    )
    visits_result = await session.execute(visits_stmt)
    visits_rows = visits_result.all()
    visits: list[PatientCardVisitItem] = []
    for b, doctor_name, service_name in visits_rows:
        amount = b.prepayment_amount or Decimal("0")
        if b.payment_id:
            pay_row = await session.execute(
                select(Payment.amount).where(Payment.id == b.payment_id)
            )
            pay_amt = pay_row.scalar_one_or_none()
            if pay_amt is not None:
                amount = pay_amt
        visits.append(
            PatientCardVisitItem(
                id=b.id,
                date=b.appointment_date,
                doctor_name=doctor_name or "",
                service_name=service_name or "",
                status=b.status,
                amount=amount,
                nps=None,
            )
        )

    # Finances: payments and refunds for this patient's bookings
    pay_stmt = (
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(
            Booking.patient_id == patient_id,
            Booking.clinic_id == clinic_id,
            Booking.deleted_at.is_(None),
        )
        .order_by(Payment.created_at.desc())
    )
    pay_result = await session.execute(pay_stmt)
    payments = list(pay_result.scalars().all())
    finances: list[PatientCardFinanceItem] = []
    for p in payments:
        fin_type = "refund" if p.status == "refunded" else "payment"
        finances.append(
            PatientCardFinanceItem(
                type=fin_type,
                amount=p.amount,
                date=p.created_at,
                description=None,
            )
        )

    # Comms: notifications for patient
    notif_stmt = (
        select(Notification)
        .where(
            Notification.patient_id == patient_id,
            Notification.clinic_id == clinic_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    notif_result = await session.execute(notif_stmt)
    comms = [
        PatientCardCommItem(
            channel=n.channel,
            template=n.template,
            status=n.status,
            sent_at=n.sent_at,
            created_at=n.created_at,
        )
        for n in notif_result.scalars().all()
    ]

    return PatientCardResponse(
        patient=patient_block,
        visits=visits,
        finances=finances,
        notes=[],
        comms=comms,
    )


@router.get(
    "/{clinic_id}/doctors/{doctor_id}/card",
    response_model=DoctorCardResponse,
)
async def get_doctor_card(
    clinic_id: UUID,
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> DoctorCardResponse:
    """Rich doctor card for drawer: profile, working_hours, payroll_policy, services."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or not in clinic")

    result = await session.execute(
        select(Doctor).where(
            Doctor.id == doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
        )
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found or not in clinic")

    doctor_dict = {
        "id": doctor.id,
        "clinic_id": doctor.clinic_id,
        "full_name": doctor.full_name,
        "specialization": doctor.specialization,
        "photo_url": doctor.photo_url,
        "rating": float(doctor.rating),
        "experience_years": doctor.experience_years,
        "is_active": doctor.is_active,
        "specialist_role": doctor.specialist_role,
        "specialist_role_custom_name": doctor.specialist_role_custom_name,
        "display_role": doctor.display_role,
    }

    # Working hours
    wh_result = await session.execute(
        select(DoctorWorkingHours).where(DoctorWorkingHours.doctor_id == doctor_id)
    )
    working_hours = [
        DoctorCardWorkingHoursItem(
            weekday=wh.weekday,
            start_time=wh.start_time.strftime("%H:%M"),
            end_time=wh.end_time.strftime("%H:%M"),
        )
        for wh in wh_result.scalars().all()
    ]

    # Payroll policy (one per doctor)
    payroll_result = await session.execute(
        select(PayrollPolicy).where(
            PayrollPolicy.doctor_id == doctor_id,
            PayrollPolicy.clinic_id == clinic_id,
        ).limit(1)
    )
    payroll = payroll_result.scalar_one_or_none()
    payroll_item: DoctorCardPayrollItem | None = None
    if payroll:
        payroll_item = DoctorCardPayrollItem(
            id=payroll.id,
            name=payroll.role or "doctor",
            type=payroll.role or "doctor",
        )

    # Services (service_doctor links)
    sd_result = await session.execute(
        select(ServiceDoctor, Service.name).join(
            Service, Service.id == ServiceDoctor.service_id
        ).where(
            ServiceDoctor.doctor_id == doctor_id,
            Service.clinic_id == clinic_id,
        )
    )
    services = [
        DoctorCardServiceDoctorItem(
            service_id=sd.service_id,
            service_name=sname or "",
            custom_price=sd.custom_price,
            is_active=sd.is_active,
        )
        for sd, sname in sd_result.all()
    ]

    return DoctorCardResponse(
        doctor=doctor_dict,
        working_hours=working_hours,
        payroll_policy=payroll_item,
        services=services,
    )


@router.get(
    "/{clinic_id}/marketing/insights",
    response_model=MarketingInsightsResponse,
)
async def get_marketing_insights(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> MarketingInsightsResponse:
    """Marketing insights (B4.5). Stub: returns empty list; later AI/UTM analysis."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return MarketingInsightsResponse(insights=[])
