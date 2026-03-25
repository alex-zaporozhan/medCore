from __future__ import annotations

from datetime import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.application.services.booking_completion_service import BookingCompletionService
from src.application.services.loyalty_service import InsufficientSubscriptionBalance
from src.application.services.booking_erp_service import ERPConfigurationError
from src.application.services.booking_service import BookingService
from src.core.context import RequestContext
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.task import Task
from src.application.dto.erp_finance_dto import ErpVisitNodeResult
from src.application.dto.erp_loyalty_dto import ErpLoyaltyWriteOffSummary
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_complete_visit_not_found_or_clinic_mismatch(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        service = BookingCompletionService(session)
        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=uuid4(),
            actor=actor,
        )

    assert result.success is False
    assert result.error_code == "booking_not_found"


@pytest.mark.asyncio
async def test_complete_visit_invalid_status(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(10, 0),
                    "status": "completed",  # уже завершён
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)
        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

    assert result.success is False
    assert result.error_code == "invalid_status"


@pytest.mark.asyncio
async def test_complete_visit_success_happy_path(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(11, 0),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)
        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

        booking = await session.get(Booking, booking_read.id)

    assert result.success is True
    assert result.final_status == "completed"
    assert result.erp_summary is not None
    assert booking is not None
    assert booking.status == "completed"


@pytest.mark.asyncio
async def test_complete_visit_unexpected_loyalty_error_best_effort(init_db, seed_data, monkeypatch):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(12, 0),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)

        async def _raise_loyalty_error(*args, **kwargs):
            raise RuntimeError("simulated loyalty failure")

        monkeypatch.setattr(
            service.loyalty_service,
            "use_subscription_for_booking",
            _raise_loyalty_error,
        )

        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

    assert result.success is True
    assert result.loyalty_summary is not None
    assert result.loyalty_summary.get("error_code") == "loyalty_apply_failed"


@pytest.mark.asyncio
async def test_complete_visit_subscription_business_error_blocks(init_db, seed_data, monkeypatch):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(12, 30),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)

        fake_sub = SimpleNamespace(
            id=uuid4(),
            remaining_visits=1,
            remaining_amount=None,
            patient_id=patient_id,
            clinic_id=clinic_id,
            status="active",
        )

        async def _raise_subscription_business(*args, **kwargs):
            raise InsufficientSubscriptionBalance("no visits left")

        monkeypatch.setattr(
            service.loyalty_service,
            "use_subscription_for_booking",
            _raise_subscription_business,
        )
        monkeypatch.setattr(
            service.loyalty_service,
            "select_subscription_for_booking",
            lambda **kw: fake_sub,
        )

        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

        booking = await session.get(Booking, booking_read.id)
        tasks = (
            await session.execute(
                select(Task).where(
                    Task.booking_id == booking_read.id,
                    Task.title == "LOYALTY_MISMATCH",
                )
            )
        ).scalars().all()

    assert result.success is False
    assert result.error_code == "insufficient_subscription_balance"
    assert booking is not None
    assert booking.status != BookingStatus.COMPLETED
    assert len(tasks) >= 1


@pytest.mark.asyncio
async def test_complete_visit_erp_configuration_error_reported(init_db, seed_data, monkeypatch):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(13, 0),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)

        async def _raise_erp_config_error(*args, **kwargs):
            raise ERPConfigurationError("missing_cashbox", "No default cashbox configured for clinic")

        monkeypatch.setattr(
            service.erp_node_service,
            "process_visit_completion",
            _raise_erp_config_error,
        )

        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

        booking = await session.get(Booking, booking_read.id)
        tasks = (
            await session.execute(
                select(Task).where(
                    Task.booking_id == booking_read.id,
                    Task.source == "system",
                )
            )
        ).scalars().all()

    # При конфигурационной ошибке ERP фасад не завершает визит и возвращает контролируемую ошибку.
    assert result.success is False
    assert result.error_code == "missing_cashbox"
    assert result.erp_summary is not None
    assert result.erp_summary.get("error_code") == "missing_cashbox"
    # ERP summary должно содержать тип ERP‑ошибки, согласованный с классификацией.
    assert result.erp_summary.get("error_type") == "finance"
    assert booking is not None
    # Статус бронирования не меняется на completed при ошибке ERP.
    assert booking.status == "confirmed"
    # Должна быть создана системная задача по ERP‑сбою
    assert len(tasks) == 1
    assert tasks[0].clinic_id == clinic_id
    assert tasks[0].booking_id == booking_read.id
    assert tasks[0].source == "system"


@pytest.mark.asyncio
async def test_complete_visit_creates_task_on_loyalty_erp_inconsistent_obligation(init_db, seed_data, monkeypatch):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(14, 0),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)

        async def _fake_success_with_loyalty_warning(*args, **kwargs):
            # Имитация успешного ERP‑узла с предупреждением о несогласованности обязательств Loyalty/ERP.
            return ErpVisitNodeResult(
                success=True,
                finance_ids=[],
                payroll_ids=[],
                inventory_ids=[],
                warnings=[],
                error_code=None,
                error_message=None,
                loyalty_summary=ErpLoyaltyWriteOffSummary(
                    booking_id=booking_read.id,
                    clinic_id=clinic_id,
                    total_write_off_amount=0,
                    obligation_ids=[],
                    remaining_amounts={},
                    warnings=["attempt_write_off_more_than_remaining"],
                ),
            )

        monkeypatch.setattr(
            service.erp_node_service,
            "process_visit_completion",
            _fake_success_with_loyalty_warning,
        )

        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

        booking = await session.get(Booking, booking_read.id)
        tasks = (
            await session.execute(
                select(Task).where(
                    Task.booking_id == booking_read.id,
                    Task.source == "system",
                    Task.title == "LOYALTY_ERP_INCONSISTENT_OBLIGATION",
                )
            )
        ).scalars().all()

    # ERP‑узел успешно завершился, визит завершён.
    assert result.success is True
    assert booking is not None
    assert booking.status == "completed"
    # Должна быть создана системная задача о несогласованных ERP/Loyalty‑обязательствах.
    assert len(tasks) == 1
    assert tasks[0].clinic_id == clinic_id
    assert tasks[0].booking_id == booking_read.id
    assert tasks[0].source == "system"


@pytest.mark.asyncio
async def test_complete_visit_erp_node_failure_sets_error_and_creates_task(
    init_db,
    seed_data,
    monkeypatch,
):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(15, 0),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        service = BookingCompletionService(session)

        async def _fake_node_failure(*args, **kwargs):
            return ErpVisitNodeResult(
                success=False,
                finance_ids=[],
                payroll_ids=[],
                inventory_ids=[],
                warnings=[],
                error_code="missing_cashbox",
                error_message="No default cashbox configured for clinic",
                loyalty_summary=None,
            )

        monkeypatch.setattr(
            service.erp_node_service,
            "process_visit_completion",
            _fake_node_failure,
        )

        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )

        result = await service.complete_visit(
            booking_id=booking_read.id,
            actor=actor,
        )

        booking = await session.get(Booking, booking_read.id)
        tasks = (
            await session.execute(
                select(Task).where(
                    Task.booking_id == booking_read.id,
                    Task.source == "system",
                )
            )
        ).scalars().all()

    assert result.success is False
    assert result.error_code == "missing_cashbox"
    assert booking is not None
    # Статус бронирования не меняется на completed при ошибке ERP‑узла.
    assert booking.status == "confirmed"
    assert booking.erp_error_code == "missing_cashbox"
    # Должна быть создана системная задача по ERP‑сбою
    assert len(tasks) == 1
    assert tasks[0].clinic_id == clinic_id
    assert tasks[0].booking_id == booking_read.id


@pytest.mark.asyncio
async def test_complete_visit_blocked_when_required_form_missing(init_db, seed_data, monkeypatch):
    """Paperless gate runs before loyalty: no signed form for required template -> fail, no loyalty call."""
    from sqlalchemy import delete

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    loyalty_called = {"n": 0}

    async def _loyalty_should_not_run(*args, **kwargs):
        loyalty_called["n"] += 1
        raise AssertionError("loyalty should not run when forms gate fails")

    template_code = f"mandatory_visit_form_{uuid4().hex[:10]}"

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            DigitalFormTemplate(
                clinic_id=clinic_id,
                code=template_code,
                name="Mandatory",
                description=None,
                version=1,
                schema={"fields": []},
                requires_signature=False,
                required_for_visit_completion=True,
                active=True,
            )
        )
        await session.commit()

    try:
        async with db_base.AsyncSessionLocal() as session:
            booking_service = BookingService(session)
            booking_read = await booking_service.create_admin_booking(
                clinic_id=clinic_id,
                data=type(
                    "obj",
                    (),
                    {
                        "clinic_id": clinic_id,
                        "patient_id": patient_id,
                        "doctor_id": doctor_id,
                        "service_id": service_id,
                        "appointment_date": day,
                        "appointment_time": time(14, 30),
                        "status": "confirmed",
                        "prepayment_amount": 0,
                        "notes": None,
                        "waitlist_entry_id": None,
                    },
                )(),
            )
            await session.commit()

        async with db_base.AsyncSessionLocal() as session:
            service = BookingCompletionService(session)
            monkeypatch.setattr(
                service.loyalty_service,
                "use_subscription_for_booking",
                _loyalty_should_not_run,
            )
            actor = RequestContext(
                clinic_id=clinic_id,
                user_id=seed_data["admin_id"],
                user_type="admin",
            )
            result = await service.complete_visit(
                booking_id=booking_read.id,
                actor=actor,
            )

        assert result.success is False
        assert result.error_code == "missing_required_forms"
        assert loyalty_called["n"] == 0
        assert result.loyalty_summary is None
    finally:
        async with db_base.AsyncSessionLocal() as session:
            await session.execute(
                delete(DigitalFormTemplate).where(
                    DigitalFormTemplate.clinic_id == clinic_id,
                    DigitalFormTemplate.code == template_code,
                )
            )
            await session.commit()
