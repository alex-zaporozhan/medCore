import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .event_bus import EventBus
from .standard_events import BOOKING_CANCELLED, BOOKING_NO_SHOW
from .domain_event import DomainEvent
from src.application.services.task_service import TaskService
from src.domain.entities.booking import Booking
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl


logger = logging.getLogger(__name__)


async def create_system_task_for_cancelled_booking(
    event: DomainEvent,
    session: AsyncSession,
) -> None:
    """Create system task when booking is cancelled."""
    booking_id_raw = event.payload.get("booking_id")
    if not booking_id_raw:
        logger.warning("[Tasks] BOOKING_CANCELLED without booking_id payload")
        return
    try:
        booking_id = UUID(str(booking_id_raw))
    except Exception:
        logger.warning(
            "[Tasks] BOOKING_CANCELLED with invalid booking_id payload",
            extra={"payload": event.payload},
        )
        return

    booking = await session.get(Booking, booking_id)
    if not booking:
        logger.warning(
            "[Tasks] Booking not found for cancelled event",
            extra={"booking_id": str(booking_id)},
        )
        return

    repo: TaskRepository = TaskRepositoryImpl(session)
    service = TaskService(repo)

    due_at = datetime.utcnow() + timedelta(days=1)
    await service.create_task(
        clinic_id=booking.clinic_id,
        title="Обработать отменённую запись",
        description=(
            "Запись отменена. Свяжитесь с пациентом, чтобы переназначить визит "
            "или предложить слот другим пациентам."
        ),
        priority="high",
        creator_id=None,
        assignee_id=None,
        role_assignee="admin",
        due_at=due_at,
        booking_id=booking.id,
        patient_id=booking.patient_id,
        source="system",
        source_event_id=booking.id,
    )


async def create_system_task_for_no_show(
    event: DomainEvent,
    session: AsyncSession,
) -> None:
    """Create system task when patient no-shows."""
    booking_id_raw = event.payload.get("booking_id")
    if not booking_id_raw:
        logger.warning("[Tasks] BOOKING_NO_SHOW without booking_id payload")
        return
    try:
        booking_id = UUID(str(booking_id_raw))
    except Exception:
        logger.warning(
            "[Tasks] BOOKING_NO_SHOW with invalid booking_id payload",
            extra={"payload": event.payload},
        )
        return

    booking = await session.get(Booking, booking_id)
    if not booking:
        logger.warning(
            "[Tasks] Booking not found for no-show event",
            extra={"booking_id": str(booking_id)},
        )
        return

    repo: TaskRepository = TaskRepositoryImpl(session)
    service = TaskService(repo)

    due_at = datetime.utcnow() + timedelta(days=1)
    await service.create_task(
        clinic_id=booking.clinic_id,
        title="Обработать no-show пациента",
        description=(
            "Пациент не пришёл на приём. Свяжитесь с пациентом, уточните причину "
            "и предложите новую дату/время."
        ),
        priority="medium",
        creator_id=None,
        assignee_id=None,
        role_assignee="admin",
        due_at=due_at,
        booking_id=booking.id,
        patient_id=booking.patient_id,
        source="system",
        source_event_id=booking.id,
    )


def register_tasks_event_handlers(event_bus: EventBus) -> None:
    """
    Register task-related event handlers.

    NOTE: EventBus handlers here are thin; they are expected to be wrapped with
    database session management at the publishing site (see ARCH_RBAC_AND_TASKS).
    """
    # We keep registration to document supported events; actual AsyncSession
    # wiring is done where events are published.
    event_bus.subscribe(BOOKING_CANCELLED, lambda event: None)
    event_bus.subscribe(BOOKING_NO_SHOW, lambda event: None)

