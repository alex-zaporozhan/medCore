"""Schedule service for building doctor schedule with Redis cache."""

import json
import logging
from datetime import date, datetime, timedelta, time
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.schedule_dto import (
    AggregatedSchedule,
    DailySchedule,
    DoctorSlot,
    ScheduleSlot,
)
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_absence import DoctorAbsence
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.interfaces.repositories.booking_repository import BookingRepository
from src.infrastructure.database.booking_repo_impl import BookingRepositoryImpl
from src.infrastructure.database.redis_client import get_redis

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for doctor schedule operations with Redis cache."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.booking_repository: BookingRepository = BookingRepositoryImpl(session)

    async def _get_redis(self) -> Redis:
        """Get Redis client instance."""
        return await get_redis()

    @staticmethod
    def _cache_key(doctor_id: UUID, day: date) -> str:
        """Build Redis cache key for schedule."""
        return f"schedule:{doctor_id}:{day.isoformat()}"

    async def get_daily_schedule(
        self,
        doctor_id: UUID,
        day: date,
    ) -> DailySchedule:
        """Get doctor's schedule for a specific day, using cache-aside in Redis."""
        redis = await self._get_redis()
        cache_key = self._cache_key(doctor_id, day)

        cached = await redis.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                logger.debug(
                    "Schedule cache hit",
                    extra={"doctor_id": str(doctor_id), "date": day.isoformat()},
                )
                return DailySchedule.model_validate(payload)
            except Exception:
                logger.warning(
                    "Failed to deserialize cached schedule, rebuilding",
                    extra={"doctor_id": str(doctor_id), "date": day.isoformat()},
                )

        schedule = await self._build_daily_schedule(doctor_id, day)

        try:
            await redis.setex(
                cache_key,
                300,  # 5 minutes TTL
                schedule.model_dump_json(),
            )
        except Exception:
            logger.exception(
                "Failed to store schedule in Redis",
                extra={"doctor_id": str(doctor_id), "date": day.isoformat()},
            )

        return schedule

    async def invalidate_daily_schedule_cache(
        self,
        doctor_id: UUID,
        day: date,
    ) -> None:
        """Invalidate cached schedule for a specific day."""
        redis = await self._get_redis()
        cache_key = self._cache_key(doctor_id, day)
        await redis.delete(cache_key)
        logger.info(
            "Schedule cache invalidated",
            extra={"doctor_id": str(doctor_id), "date": day.isoformat()},
        )

    async def _build_daily_schedule(
        self,
        doctor_id: UUID,
        day: date,
    ) -> DailySchedule:
        """Build schedule from working hours and bookings."""
        # If doctor is on absence (vacation) this day, no slots
        absence_result = await self.session.execute(
            select(DoctorAbsence.id).where(
                DoctorAbsence.doctor_id == doctor_id,
                DoctorAbsence.date_from <= day,
                DoctorAbsence.date_to >= day,
            ).limit(1)
        )
        if absence_result.scalar_one_or_none() is not None:
            return DailySchedule(doctor_id=doctor_id, date=day, slots=[])

        weekday = day.weekday()  # 0 = Monday

        # Load clinic config via any doctor clinic (we assume single-clinic instance)
        clinic_result = await self.session.execute(select(Clinic).limit(1))
        clinic = clinic_result.scalar_one()

        # Load working hours for doctor and weekday
        wh_result = await self.session.execute(
            select(DoctorWorkingHours).where(
                DoctorWorkingHours.doctor_id == doctor_id,
                DoctorWorkingHours.weekday == weekday,
            )
        )
        working_hours = wh_result.scalars().all()

        if not working_hours:
            return DailySchedule(doctor_id=doctor_id, date=day, slots=[])

        # For MVP assume single continuous interval per day
        wh = working_hours[0]
        slot_minutes = clinic.slot_duration_minutes

        slots: list[ScheduleSlot] = []
        current_start = datetime.combine(day, wh.start_time)
        end_dt = datetime.combine(day, wh.end_time)

        while current_start < end_dt:
            current_end = current_start + timedelta(minutes=slot_minutes)
            if current_end > end_dt:
                break

            slots.append(
                ScheduleSlot(
                    start_time=current_start.time(),
                    end_time=current_end.time(),
                    is_available=True,
                    booking_id=None,
                    status=None,
                )
            )
            current_start = current_end

        # Load bookings for that day and mark slots as occupied
        bookings = await self.booking_repository.get_for_doctor_on_date(doctor_id, day)
        booking_by_time: dict[tuple[str, str], Booking] = {}
        for b in bookings:
            key = (b.appointment_date.isoformat(), b.appointment_time.isoformat())
            booking_by_time[key] = b

        for slot in slots:
            key = (day.isoformat(), slot.start_time.isoformat())
            booking = booking_by_time.get(key)
            if booking and booking.status != "cancelled":
                slot.is_available = False
                slot.booking_id = booking.id
                slot.status = booking.status

        logger.info(
            "Schedule built",
            extra={
                "doctor_id": str(doctor_id),
                "date": day.isoformat(),
                "slots_total": len(slots),
                "slots_available": sum(1 for s in slots if s.is_available),
            },
        )

        return DailySchedule(doctor_id=doctor_id, date=day, slots=slots)

    async def _default_times_for_clinic(self, clinic: Clinic) -> list[time]:
        """Build default time grid from clinic workday and slot duration."""
        start_dt = datetime.combine(date(2000, 1, 1), clinic.workday_start)
        end_dt = datetime.combine(date(2000, 1, 1), clinic.workday_end)
        step = timedelta(minutes=clinic.slot_duration_minutes)
        out: list[time] = []
        while start_dt < end_dt:
            out.append(start_dt.time())
            start_dt += step
        return out

    async def get_aggregated_schedule(
        self,
        doctor_ids: list[UUID],
        day: date,
    ) -> AggregatedSchedule:
        """Build aggregated schedule for multiple doctors: unified time grid, by_doctor slots aligned to times."""
        if not doctor_ids:
            return AggregatedSchedule(doctors=[], date=day, times=[], by_doctor={})

        all_times_set: set[time] = set()
        doctor_slots_by_time: dict[UUID, dict[time, DoctorSlot]] = {}
        for doctor_id in doctor_ids:
            daily = await self.get_daily_schedule(doctor_id=doctor_id, day=day)
            by_t: dict[time, DoctorSlot] = {}
            for slot in daily.slots:
                all_times_set.add(slot.start_time)
                by_t[slot.start_time] = DoctorSlot(
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    is_available=slot.is_available,
                    booking_id=slot.booking_id,
                    status=slot.status,
                )
            doctor_slots_by_time[doctor_id] = by_t

        times = sorted(all_times_set)        # If no doctor has working hours for this day, use clinic default grid so admin always sees a grid
        if not times:
            doc_result = await self.session.execute(
                select(Doctor.clinic_id).where(Doctor.id == doctor_ids[0]).limit(1)
            )
            clinic_id_row = doc_result.one_or_none()
            if clinic_id_row:
                clinic_result = await self.session.execute(
                    select(Clinic).where(Clinic.id == clinic_id_row[0])
                )
                clinic = clinic_result.scalar_one_or_none()
            else:
                clinic = None
            if clinic:
                times = await self._default_times_for_clinic(clinic)
                for doctor_id in doctor_ids:
                    doctor_slots_by_time[doctor_id] = {
                        t: DoctorSlot(start_time=t, end_time=t, is_available=False, booking_id=None, status=None)
                        for t in times
                    }

        by_doctor: dict[str, list[DoctorSlot]] = {}
        for doctor_id in doctor_ids:
            by_t = doctor_slots_by_time[doctor_id]
            by_doctor[str(doctor_id)] = [
                by_t.get(t, DoctorSlot(start_time=t, end_time=t, is_available=False, booking_id=None, status=None))
                for t in times
            ]

        return AggregatedSchedule(
            doctors=doctor_ids,
            date=day,
            times=times,
            by_doctor=by_doctor,
        )
