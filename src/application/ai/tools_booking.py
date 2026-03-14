from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError

from src.application.ai.tools_base import Tool, ToolContext, ToolError
from src.application.dto.booking_dto import BookingCreateAdmin, BookingRead
from src.application.dto.schedule_dto import DailySchedule
from src.core.patient_messages import BOOKING_SLOT_ALREADY_BOOKED


class GetAvailableSlotsArgs(BaseModel):
    clinic_id: UUID
    service_id: UUID | None = None
    doctor_id: UUID | None = None
    date_from: date
    date_to: date


class AvailableSlot(BaseModel):
    clinic_id: UUID
    doctor_id: UUID
    service_id: UUID | None = None
    date: date
    start_time: str
    end_time: str | None = None


class CreateBookingArgs(BaseModel):
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    service_id: UUID
    appointment_start: datetime = Field(
        description="Start of appointment in ISO 8601 format (UTC or clinic local time)."
    )
    notes: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="ai_agent", description="Logical source marker for analytics/audit.")


class CreateBookingResult(BaseModel):
    booking: BookingRead


class GetAvailableSlotsTool(Tool):
    name = "get_available_slots"
    description = (
        "Получить свободные слоты расписания врача в указанном диапазоне дат. "
        "Минимально требуется doctor_id; service_id используется для валидации соответствия услуги врачу."
    )
    args_schema = GetAvailableSlotsArgs

    async def __call__(self, ctx: ToolContext, args: GetAvailableSlotsArgs) -> list[AvailableSlot] | ToolError:
        # Enforce clinic boundary: runtime context clinic_id overrides any arg value.
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Инструмент может работать только в пределах одной клиники.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        if args.date_from > args.date_to:
            return ToolError(
                code="invalid_date_range",
                message="date_from не может быть больше date_to.",
                details={"date_from": args.date_from.isoformat(), "date_to": args.date_to.isoformat()},
            )

        if args.doctor_id is None:
            return ToolError(
                code="doctor_required",
                message="Для первой версии инструмента требуется doctor_id.",
            )

        # Optional validation: ensure doctor provides the requested service.
        if args.service_id is not None:
            try:
                await ctx.booking_service._ensure_service_doctor(args.service_id, args.doctor_id)  # type: ignore[attr-defined]
            except ValueError as exc:
                return ToolError(
                    code="invalid_service_doctor",
                    message=str(exc),
                    details={
                        "service_id": str(args.service_id),
                        "doctor_id": str(args.doctor_id),
                    },
                )

        slots: list[AvailableSlot] = []
        current = args.date_from
        while current <= args.date_to:
            daily: DailySchedule = await ctx.schedule_service.get_daily_schedule(
                doctor_id=args.doctor_id,
                day=current,
            )
            for slot in daily.slots:
                if not slot.is_available:
                    continue
                slots.append(
                    AvailableSlot(
                        clinic_id=clinic_id,
                        doctor_id=args.doctor_id,
                        service_id=args.service_id,
                        date=current,
                        start_time=slot.start_time.isoformat(),
                        end_time=slot.end_time.isoformat() if slot.end_time else None,
                    )
                )
            # Step by one day
            current = current + timedelta(days=1)

        return slots


class CreateBookingTool(Tool):
    name = "create_booking"
    description = (
        "Создать новую запись на приём, используя те же проверки, что и админское API. "
        "Возвращает созданную запись или структурированную ошибку конфликта слота."
    )
    args_schema = CreateBookingArgs

    async def __call__(self, ctx: ToolContext, args: CreateBookingArgs) -> CreateBookingResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code="clinic_mismatch",
                message="Нельзя создавать запись в другой клинике.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        # Split appointment_start into date / time to reuse existing Booking DTOs.
        appointment_date = args.appointment_start.date()
        appointment_time = args.appointment_start.time()

        payload = BookingCreateAdmin(
            clinic_id=clinic_id,
            patient_id=args.patient_id,
            doctor_id=args.doctor_id,
            service_id=args.service_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="pending",
            prepayment_amount=None,
            notes=self._augment_notes_with_source(args.notes, args.source),
        )

        try:
            booking_read = await ctx.booking_service.create_admin_booking(
                clinic_id=clinic_id,
                data=payload,
            )
        except ValueError as exc:
            message = str(exc)
            code = "validation_error"
            if message == BOOKING_SLOT_ALREADY_BOOKED:
                code = "slot_conflict"
            return ToolError(
                code=code,
                message=message,
                details={
                    "clinic_id": str(clinic_id),
                    "doctor_id": str(args.doctor_id),
                    "service_id": str(args.service_id),
                    "patient_id": str(args.patient_id),
                },
            )
        except IntegrityError:
            # DB-level unique constraint conflict on slot.
            return ToolError(
                code="slot_conflict",
                message="Указанный слот уже занят другой записью.",
            )
        except ValidationError as exc:
            return ToolError(
                code="invalid_args",
                message="Некорректные аргументы для создания записи.",
                details={"errors": exc.errors()},
            )
        except Exception as exc:  # noqa: BLE001
            return ToolError(
                code="unexpected_error",
                message="Не удалось создать запись из-за внутренней ошибки.",
                details={"error": str(exc)},
            )

        return CreateBookingResult(booking=booking_read)

    @staticmethod
    def _augment_notes_with_source(notes: str | None, source: str) -> str | None:
        marker = f"[source={source}]"
        if notes:
            if marker in notes:
                return notes
            return f"{marker} {notes}"
        return marker

