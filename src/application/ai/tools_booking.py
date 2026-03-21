from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError

from src.application.ai.booking_tools_adapter import get_available_slots_via_adapter
from src.application.ai.tools_base import Tool, ToolContext, ToolError
from src.application.ai.tokenization import (
    make_booking_token,
    make_patient_token,
    parse_booking_token,
    parse_patient_token,
)
from src.application.dto.booking_ai_dto import (
    AvailableSlot,
    BookingSummary,
    CancelBookingInput as CancelBookingArgs,
    CancelBookingOutput as CancelBookingResult,
    CreateBookingInput as CreateBookingArgs,
    CreateBookingOutput as CreateBookingResult,
    GetAvailableSlotsInput as GetAvailableSlotsArgs,
    RescheduleBookingInput as RescheduleBookingArgs,
    RescheduleBookingOutput as RescheduleBookingResult,
)
from src.application.dto.booking_dto import (
    BookingCreateAdmin,
    BookingErrorCode,
    BookingRead,
    BookingRescheduleRequest,
)
from src.application.multitenancy import ClinicForbiddenError
from src.core.patient_messages import (
    BOOKING_CANNOT_CANCEL_PAST,
    BOOKING_CANNOT_CANCEL_STATUS,
    BOOKING_CANNOT_RESCHEDULE_CANCELLED,
    BOOKING_INVALID_STATUS,
    BOOKING_NOT_FOUND,
    BOOKING_SLOT_ALREADY_BOOKED,
)


#
# NOTE: DTO definitions are in src/application/dto/booking_ai_dto.py
# and imported above. Keep tools implementation here.


class GetAvailableSlotsTool(Tool):
    name = "get_available_slots"
    description = (
        "Получить свободные слоты расписания врача в указанном диапазоне дат. "
        "Минимально требуется doctor_id; service_id используется для валидации соответствия услуги врачу."
    )
    args_schema = GetAvailableSlotsArgs
    required_permissions = {"booking.ai_tools.use"}

    async def __call__(self, ctx: ToolContext, args: GetAvailableSlotsArgs) -> list[AvailableSlot] | ToolError:
        return await get_available_slots_via_adapter(ctx, args)


class CreateBookingTool(Tool):
    name = "create_booking"
    description = (
        "Создать новую запись на приём, используя те же проверки, что и админское API. "
        "Возвращает созданную запись или структурированную ошибку конфликта слота."
    )
    args_schema = CreateBookingArgs
    # Modifying tool: по ARCH доступен только привилегированным ролям.
    allowed_roles = {"admin", "owner", "ai_task_runner"}
    required_permissions = {"booking.ai_tools.use"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: CreateBookingArgs,
    ) -> CreateBookingResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code=BookingErrorCode.CLINIC_MISMATCH.value,
                message="Нельзя создавать запись в другой клинике.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        if args.patient_token:
            try:
                patient_id = parse_patient_token(args.patient_token)
            except ValueError as exc:
                return ToolError(
                    code=BookingErrorCode.VALIDATION_ERROR.value,
                    message="Некорректный patient_token. Ожидается формат PATIENT#<uuid>.",
                    details={"error": str(exc)},
                )
        elif args.patient_id is not None:
            patient_id = args.patient_id
        else:
            return ToolError(
                code=BookingErrorCode.VALIDATION_ERROR.value,
                message="Требуется patient_token (предпочтительно) или patient_id (deprecated).",
            )

        # Split appointment_start into date / time to reuse existing Booking DTOs.
        appointment_date = args.appointment_start.date()
        appointment_time = args.appointment_start.time()

        payload = BookingCreateAdmin(
            clinic_id=clinic_id,
            patient_id=patient_id,
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
            code = BookingErrorCode.VALIDATION_ERROR.value
            if message == BOOKING_SLOT_ALREADY_BOOKED:
                code = BookingErrorCode.SLOT_UNAVAILABLE.value
            return ToolError(
                code=code,
                message=message,
                details={
                    "clinic_id": str(clinic_id),
                    "doctor_id": str(args.doctor_id),
                    "service_id": str(args.service_id),
                    "patient_token": args.patient_token,
                    "patient_id": str(args.patient_id) if args.patient_id else None,
                },
            )
        except IntegrityError:
            # DB-level unique constraint conflict on slot.
            return ToolError(
                code=BookingErrorCode.SLOT_UNAVAILABLE.value,
                message="Указанный слот уже занят другой записью.",
            )
        except ValidationError as exc:
            return ToolError(
                code=BookingErrorCode.VALIDATION_ERROR.value,
                message="Некорректные аргументы для создания записи.",
                details={"errors": exc.errors()},
            )
        except Exception as exc:  # noqa: BLE001
            return ToolError(
                code=BookingErrorCode.SERVICE_UNAVAILABLE.value,
                message="Не удалось создать запись из-за внутренней ошибки.",
                details={"error": str(exc)},
            )

        booking_token = make_booking_token(booking_read.id)
        patient_token = make_patient_token(booking_read.patient_id)
        summary = BookingSummary(
            booking_token=booking_token,
            clinic_id=booking_read.clinic_id,
            patient_token=patient_token,
            doctor_id=booking_read.doctor_id,
            service_id=booking_read.service_id,
            appointment_date=booking_read.appointment_date,
            appointment_time=booking_read.appointment_time.isoformat(),
            status=booking_read.status,
            notes=booking_read.notes,
        )

        return CreateBookingResult(booking=summary)

    @staticmethod
    def _augment_notes_with_source(notes: str | None, source: str) -> str | None:
        marker = f"[source={source}]"
        if notes:
            if marker in notes:
                return notes
            return f"{marker} {notes}"
        return marker


class CancelBookingTool(Tool):
    name = "cancel_booking"
    description = (
        "Отменить существующую запись по токену BOOKING#... с учётом инвариантов статусов и времени."
    )
    args_schema = CancelBookingArgs
    allowed_roles = {"admin", "owner", "ai_task_runner"}
    required_permissions = {"booking.ai_tools.use"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: CancelBookingArgs,
    ) -> CancelBookingResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code=BookingErrorCode.CLINIC_MISMATCH.value,
                message="Нельзя отменять запись в другой клинике.",
                details={
                    "requested_clinic_id": str(args.clinic_id),
                    "context_clinic_id": str(clinic_id),
                },
            )

        try:
            booking_id = parse_booking_token(args.booking_token)
        except ValueError as exc:
            return ToolError(
                code=BookingErrorCode.VALIDATION_ERROR.value,
                message="Некорректный booking_token. Ожидается формат BOOKING#<uuid>.",
                details={"error": str(exc)},
            )

        try:
            booking_read = await ctx.booking_service.cancel_booking(
                clinic_id=clinic_id,
                booking_id=booking_id,
                context=ctx.request_context,
            )
        except ClinicForbiddenError:
            return ToolError(
                code=BookingErrorCode.BOOKING_NOT_FOUND.value,
                message=BOOKING_NOT_FOUND,
            )
        except LookupError:
            return ToolError(
                code=BookingErrorCode.BOOKING_NOT_FOUND.value,
                message=BOOKING_NOT_FOUND,
            )
        except ValueError as exc:
            message = str(exc)
            if message == BOOKING_CANNOT_CANCEL_STATUS:
                code = BookingErrorCode.BOOKING_STATUS_INVALID.value
            elif message == BOOKING_CANNOT_CANCEL_PAST:
                code = BookingErrorCode.VALIDATION_ERROR.value
            else:
                code = BookingErrorCode.VALIDATION_ERROR.value
            return ToolError(
                code=code,
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            return ToolError(
                code=BookingErrorCode.SERVICE_UNAVAILABLE.value,
                message="Не удалось отменить запись из-за внутренней ошибки.",
                details={"error": str(exc)},
            )

        summary = BookingSummary(
            booking_token=args.booking_token,
            clinic_id=booking_read.clinic_id,
            patient_token=make_patient_token(booking_read.patient_id),
            doctor_id=booking_read.doctor_id,
            service_id=booking_read.service_id,
            appointment_date=booking_read.appointment_date,
            appointment_time=booking_read.appointment_time.isoformat(),
            status=booking_read.status,
            notes=booking_read.notes,
        )

        return CancelBookingResult(success=True, booking=summary)


class RescheduleBookingTool(Tool):
    name = "reschedule_booking"
    description = (
        "Перенести существующую запись на другой слот (и при необходимости к другому врачу) "
        "по токену BOOKING#..., соблюдая инварианты расписания и статусов."
    )
    args_schema = RescheduleBookingArgs
    allowed_roles = {"admin", "owner", "ai_task_runner"}
    required_permissions = {"booking.ai_tools.use"}

    async def __call__(
        self,
        ctx: ToolContext,
        args: RescheduleBookingArgs,
    ) -> RescheduleBookingResult | ToolError:
        clinic_id = ctx.clinic_id
        if args.clinic_id != clinic_id:
            return ToolError(
                code=BookingErrorCode.CLINIC_MISMATCH.value,
                message="Нельзя переносить запись в другой клинике.",
                details={"requested_clinic_id": str(args.clinic_id), "context_clinic_id": str(clinic_id)},
            )

        try:
            booking_id = parse_booking_token(args.booking_token)
        except ValueError as exc:
            return ToolError(
                code=BookingErrorCode.VALIDATION_ERROR.value,
                message="Некорректный booking_token. Ожидается формат BOOKING#<uuid>.",
                details={"error": str(exc)},
            )

        new_date = args.new_appointment_start.date()
        new_time = args.new_appointment_start.time()

        request = BookingRescheduleRequest(
            appointment_date=new_date,
            appointment_time=new_time,
            to_doctor_id=args.to_doctor_id,
        )

        try:
            booking_read = await ctx.booking_service.reschedule_booking(
                clinic_id=clinic_id,
                booking_id=booking_id,
                data=request,
            )
        except ClinicForbiddenError:
            return ToolError(
                code=BookingErrorCode.BOOKING_NOT_FOUND.value,
                message=BOOKING_NOT_FOUND,
            )
        except LookupError:
            return ToolError(
                code=BookingErrorCode.BOOKING_NOT_FOUND.value,
                message=BOOKING_NOT_FOUND,
            )
        except ValueError as exc:
            message = str(exc)
            if message == BOOKING_CANNOT_RESCHEDULE_CANCELLED:
                code = BookingErrorCode.BOOKING_STATUS_INVALID.value
            elif message == BOOKING_SLOT_ALREADY_BOOKED:
                code = BookingErrorCode.SLOT_UNAVAILABLE.value
            else:
                code = BookingErrorCode.VALIDATION_ERROR.value
            return ToolError(
                code=code,
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            return ToolError(
                code=BookingErrorCode.SERVICE_UNAVAILABLE.value,
                message="Не удалось перенести запись из-за внутренней ошибки.",
                details={"error": str(exc)},
            )

        summary = BookingSummary(
            booking_token=args.booking_token,
            clinic_id=booking_read.clinic_id,
            patient_token=make_patient_token(booking_read.patient_id),
            doctor_id=booking_read.doctor_id,
            service_id=booking_read.service_id,
            appointment_date=booking_read.appointment_date,
            appointment_time=booking_read.appointment_time.isoformat(),
            status=booking_read.status,
            notes=booking_read.notes,
        )

        return RescheduleBookingResult(booking=summary)

