"""CSV import and export service for schedule and bookings."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, time as dtime
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.booking_slot_advisory_lock import (
    acquire_doctor_slot_xact_advisory_lock,
)
from src.application.services.schedule_service import ScheduleService
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.csv_import_job import CsvImportJob
from src.domain.entities.doctor import Doctor
from src.domain.entities.patient import Patient
from src.domain.entities.service import Service

logger = logging.getLogger(__name__)

_MAX_SCHEDULE_CSV_ERROR_LINES = 40


class CsvImportService:
    """Service for CSV-based schedule import and booking export."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.schedule_service = ScheduleService(session)

    async def _get_default_clinic(self) -> Clinic:
        """Get default clinic (single-clinic instance)."""
        result = await self.session.execute(select(Clinic).limit(1))
        clinic = result.scalar_one_or_none()
        if clinic is None:
            raise RuntimeError("No clinic configured for CSV operations")
        return clinic

    async def _get_doctor(self, doctor_id: UUID, clinic_id: UUID) -> Doctor:
        """Ensure doctor exists in given clinic."""
        result = await self.session.execute(
            select(Doctor).where(
                Doctor.id == doctor_id,
                Doctor.clinic_id == clinic_id,
                Doctor.deleted_at.is_(None),
            )
        )
        doctor = result.scalar_one_or_none()
        if doctor is None:
            raise ValueError(f"Doctor {doctor_id} not found for clinic")
        return doctor

    async def _get_or_create_technical_patient(self, clinic_id: UUID) -> Patient:
        """Get or create technical patient used for CSV-imported slots."""
        # Technical marker: phone is unlikely to collide with real patients.
        marker_phone = "+70000000000"
        result = await self.session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.phone == marker_phone,
                Patient.deleted_at.is_(None),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is not None:
            return patient

        patient = Patient(
            clinic_id=clinic_id,
            phone=marker_phone,
            full_name="CSV Imported Slot",
        )
        self.session.add(patient)
        await self.session.flush()
        await self.session.refresh(patient)
        return patient

    async def _get_or_create_technical_service(self, clinic_id: UUID) -> Service:
        """Get or create technical service used for CSV-imported slots."""
        marker_name = "[CSV Imported Slot]"
        result = await self.session.execute(
            select(Service).where(
                Service.clinic_id == clinic_id,
                Service.name == marker_name,
                Service.deleted_at.is_(None),
            )
        )
        service = result.scalar_one_or_none()
        if service is not None:
            return service

        service = Service(
            clinic_id=clinic_id,
            name=marker_name,
            category="integration",
            description="Technical service for schedule slots imported from CSV",
            price=Decimal("0.00"),
            duration_minutes=30,
        )
        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def _create_slot_booking_if_absent(
        self,
        *,
        clinic_id: UUID,
        doctor_id: UUID,
        day: date,
        slot_time: dtime,
        patient_id: UUID,
        service_id: UUID,
    ) -> bool:
        """Create booking for slot if there is no existing non-deleted booking.

        Returns True if a new booking was created.
        """
        result = await self.session.execute(
            select(Booking).where(
                Booking.clinic_id == clinic_id,
                Booking.doctor_id == doctor_id,
                Booking.appointment_date == day,
                Booking.appointment_time == slot_time,
                Booking.deleted_at.is_(None),
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            # Do not touch existing real bookings; CSV import only fills free slots.
            return False

        await acquire_doctor_slot_xact_advisory_lock(
            self.session,
            doctor_id=doctor_id,
            appointment_date=day,
            appointment_time=slot_time,
        )
        result2 = await self.session.execute(
            select(Booking).where(
                Booking.clinic_id == clinic_id,
                Booking.doctor_id == doctor_id,
                Booking.appointment_date == day,
                Booking.appointment_time == slot_time,
                Booking.deleted_at.is_(None),
            )
        )
        if result2.scalar_one_or_none() is not None:
            return False

        booking = Booking(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=day,
            appointment_time=slot_time,
            # Imported slots are pending by default to respect prepayment rules.
            status="pending",
            prepayment_amount=Decimal("0.00"),
            notes="Imported from CSV schedule",
        )
        self.session.add(booking)
        await self.session.flush()
        logger.info(
            "CSV slot booking created",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(clinic_id),
                "doctor_id": str(doctor_id),
                "date": day.isoformat(),
                "time": slot_time.isoformat(),
            },
        )
        return True

    @staticmethod
    def _parse_time_slots(raw: str) -> list[dtime]:
        """Parse time_slots JSON array into list of time objects."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in time_slots: {exc.msg}") from exc

        if not isinstance(data, list):
            raise ValueError("time_slots must be a JSON array of strings")

        result: list[dtime] = []
        for item in data:
            if not isinstance(item, str):
                raise ValueError("time_slots items must be strings")
            try:
                hour, minute = item.split(":", 1)
                result.append(dtime(hour=int(hour), minute=int(minute)))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Invalid time format in time_slots: {item}") from exc
        return result

    async def import_schedule_from_csv(
        self,
        *,
        file_name: str,
        content: str,
    ) -> CsvImportJob:
        """Import schedule from CSV and create technical bookings for free slots.

        Contract: **row-level** processing (aligned with commerce CSV): invalid rows are
        skipped with errors recorded; valid rows commit in one transaction at the end.
        Status ``completed_with_errors`` when at least one row failed but others succeeded;
        ``failed`` only when nothing could be imported or the file/header is invalid.

        CSV format:
        - Columns: doctor_id,date,time_slots
        - doctor_id: UUID
        - date: YYYY-MM-DD
        - time_slots: JSON array of "HH:MM" strings
        """
        clinic = await self._get_default_clinic()
        technical_patient = await self._get_or_create_technical_patient(clinic.id)
        technical_service = await self._get_or_create_technical_service(clinic.id)

        job = CsvImportJob(
            clinic_id=clinic.id,
            file_name=file_name,
            status="processing",
            total_rows=0,
            processed_rows=0,
            error=None,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        reader = csv.DictReader(io.StringIO(content))
        required_fields = {"doctor_id", "date", "time_slots"}
        if not reader.fieldnames or not required_fields.issubset(reader.fieldnames):
            job.status = "failed"
            job.error = "CSV must contain columns: doctor_id,date,time_slots"
            await self.session.flush()
            logger.warning(
                "CSV import failed: missing columns",
                extra={"job_id": str(job.id), "file_name": file_name},
            )
            raise ValueError(job.error)

        total_rows = 0
        created_slots = 0
        errors: list[str] = []
        touched_keys: set[tuple[UUID, date]] = set()

        for row_index, row in enumerate(reader, start=2):  # header is line 1
            total_rows += 1
            raw_doctor_id = (row.get("doctor_id") or "").strip()
            raw_date = (row.get("date") or "").strip()
            raw_slots = (row.get("time_slots") or "").strip()

            try:
                if not raw_doctor_id or not raw_date or not raw_slots:
                    raise ValueError("doctor_id, date and time_slots must be non-empty")

                doctor_id = UUID(raw_doctor_id)
                # Validate doctor belongs to clinic.
                await self._get_doctor(doctor_id, clinic.id)

                try:
                    day = date.fromisoformat(raw_date)
                except Exception as exc:  # noqa: BLE001
                    raise ValueError(f"Invalid date format: {raw_date}") from exc

                slot_times = self._parse_time_slots(raw_slots)
                if not slot_times:
                    raise ValueError("time_slots must contain at least one time value")

                for slot_time in slot_times:
                    created = await self._create_slot_booking_if_absent(
                        clinic_id=clinic.id,
                        doctor_id=doctor_id,
                        day=day,
                        slot_time=slot_time,
                        patient_id=technical_patient.id,
                        service_id=technical_service.id,
                    )
                    if created:
                        created_slots += 1
                        touched_keys.add((doctor_id, day))
            except Exception as exc:  # noqa: BLE001
                message = f"Row {row_index}: {exc}"
                if len(errors) < _MAX_SCHEDULE_CSV_ERROR_LINES:
                    errors.append(message)
                logger.warning(
                    "CSV import row failed",
                    extra={
                        "job_id": str(job.id),
                        "file_name": file_name,
                        "row_index": row_index,
                        "error": str(exc),
                    },
                )
                continue

        job.total_rows = total_rows
        job.processed_rows = created_slots

        if errors and created_slots == 0:
            job.status = "failed"
            job.error = "; ".join(errors)
            await self.session.flush()
            logger.warning(
                "CSV import failed",
                extra={
                    "job_id": str(job.id),
                    "file_name": file_name,
                    "total_rows": total_rows,
                    "processed_rows": created_slots,
                },
            )
            raise ValueError(errors[0])

        if errors:
            job.status = "completed_with_errors"
            job.error = "; ".join(errors)
        else:
            job.status = "completed"
            job.error = None
        await self.session.flush()

        # Invalidate schedule cache for affected doctor/day pairs.
        for doctor_id, day in touched_keys:
            await self.schedule_service.invalidate_daily_schedule_cache(
                doctor_id=doctor_id,
                day=day,
            )

        logger.info(
            "CSV import completed",
            extra={
                "job_id": str(job.id),
                "file_name": file_name,
                "total_rows": total_rows,
                "created_slots": created_slots,
            },
        )
        return job

    async def export_completed_bookings_csv(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> tuple[str, int]:
        """Export completed bookings as CSV for a date range.

        Returns CSV text and number of exported rows.
        """
        clinic = await self._get_default_clinic()

        result = await self.session.execute(
            select(
                Booking.id,
                Patient.phone,
                Doctor.full_name,
                Service.name,
                Booking.appointment_date,
                Booking.appointment_time,
                Service.price,
            )
            .join(Patient, Patient.id == Booking.patient_id)
            .join(Doctor, Doctor.id == Booking.doctor_id)
            .join(Service, Service.id == Booking.service_id)
            .where(
                Booking.clinic_id == clinic.id,
                Booking.status == "completed",
                Booking.appointment_date >= date_from,
                Booking.appointment_date <= date_to,
                Booking.deleted_at.is_(None),
                Patient.deleted_at.is_(None),
                Doctor.deleted_at.is_(None),
                Service.deleted_at.is_(None),
            )
            .order_by(
                Booking.appointment_date.asc(),
                Booking.appointment_time.asc(),
            )
        )

        rows: Iterable[tuple] = result.all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "booking_id",
                "patient_phone",
                "doctor_name",
                "service_name",
                "date",
                "time",
                "price",
            ]
        )

        count = 0
        for (
            booking_id,
            patient_phone,
            doctor_name,
            service_name,
            appt_date,
            appt_time,
            price,
        ) in rows:
            writer.writerow(
                [
                    str(booking_id),
                    patient_phone or "",
                    doctor_name,
                    service_name,
                    appt_date.isoformat(),
                    appt_time.strftime("%H:%M"),
                    f"{price:.2f}",
                ]
            )
            count += 1

        csv_text = output.getvalue()

        logger.info(
            "CSV export completed",
            extra={
                "clinic_id": str(clinic.id),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "rows": count,
            },
        )

        return csv_text, count

