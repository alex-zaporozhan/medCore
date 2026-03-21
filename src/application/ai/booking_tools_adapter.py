"""Thin adapter: booking AI tools → schedule/booking services (QA_ARCH W4.1 J2/J3).

Keeps Tool classes as HTTP/schema wrappers; shared logic and caps live here.
"""

from __future__ import annotations

from datetime import timedelta

from src.application.ai.tools_base import ToolContext, ToolError
from src.application.dto.booking_ai_dto import AvailableSlot, GetAvailableSlotsInput
from src.application.dto.schedule_dto import DailySchedule
from src.core.config import settings


async def get_available_slots_via_adapter(
    ctx: ToolContext,
    args: GetAvailableSlotsInput,
) -> list[AvailableSlot] | ToolError:
    """Fetch available slots with the same invariants as GetAvailableSlotsTool; caps result size."""
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

    max_days = settings.booking_ai_tools_max_range_days
    range_days = (args.date_to - args.date_from).days
    if range_days > max_days:
        return ToolError(
            code="date_range_too_large",
            message=f"Слишком большой диапазон дат. Максимум {max_days} дней.",
            details={
                "date_from": args.date_from.isoformat(),
                "date_to": args.date_to.isoformat(),
                "max_days": max_days,
            },
        )

    if args.doctor_id is None:
        return ToolError(
            code="doctor_required",
            message="Для первой версии инструмента требуется doctor_id.",
        )

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
            clinic_id=clinic_id,
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
        current = current + timedelta(days=1)

    cap = settings.booking_ai_tools_max_slots
    if len(slots) > cap:
        return slots[:cap]
    return slots
