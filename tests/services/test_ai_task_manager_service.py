"""Tests for AI Task Manager (TASKS_AI_021) runner/analyzer/generator."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.ai_task_manager_service import AiTaskManagerRunner
from src.application.services.task_service import TaskService
from src.domain.entities.ai_task_settings import AiTaskSettings
from src.domain.entities.booking import Booking
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.task import Task
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl


async def _cleanup_clinic(db_session: AsyncSession, clinic_id: uuid.UUID) -> None:
    """Best-effort cleanup to keep tests isolated without relying on rollbacks."""
    await db_session.execute(delete(Task).where(Task.clinic_id == clinic_id))
    await db_session.execute(delete(AiTaskSettings).where(AiTaskSettings.clinic_id == clinic_id))
    await db_session.execute(delete(Booking).where(Booking.clinic_id == clinic_id))
    await db_session.execute(delete(LeadCard).where(LeadCard.clinic_id == clinic_id))
    await db_session.execute(delete(LeadStage).where(LeadStage.clinic_id == clinic_id))
    await db_session.execute(delete(LeadPipeline).where(LeadPipeline.clinic_id == clinic_id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_ai_task_manager_noop_when_disabled(
    db_session: AsyncSession,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    await _cleanup_clinic(db_session, clinic_id)

    # Settings exist but disabled -> no-op
    db_session.add(AiTaskSettings(clinic_id=clinic_id, ai_tasks_enabled=False))
    await db_session.commit()

    repo = TaskRepositoryImpl(db_session)
    svc = TaskService(repo)
    runner = AiTaskManagerRunner(db_session, svc, repo)
    created = await runner.run_for_clinic(clinic_id)
    assert created == []


@pytest.mark.asyncio
async def test_ai_task_manager_creates_ai_suggested_task_from_no_show_pattern(
    db_session: AsyncSession,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    await _cleanup_clinic(db_session, clinic_id)
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    db_session.add(
        AiTaskSettings(
            clinic_id=clinic_id,
            ai_tasks_enabled=True,
            creation_mode="confirm",
            analyzer_thresholds={"no_show_min_count": 2},
            daily_clinic_limit=20,
            daily_patient_limit=3,
            daily_doctor_limit=5,
        )
    )

    now = datetime.now(timezone.utc)
    # Seed 2 no-show bookings within window so analyzer proposes a task.
    for i in range(2):
        b = Booking(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=(now - timedelta(days=3)).date(),
            appointment_time=time(10, 0) if i == 0 else time(10, 30),
            status="no_show",
            prepayment_amount=0,
            created_at=now,
            updated_at=now,
            erp_processed=False,
            erp_error_code=None,
            deleted_at=None,
            paid_by_subscription=False,
            notes=None,
            payment_id=None,
        )
        db_session.add(b)
    await db_session.commit()

    repo = TaskRepositoryImpl(db_session)
    svc = TaskService(repo)
    runner = AiTaskManagerRunner(db_session, svc, repo)
    created = await runner.run_for_clinic(clinic_id)
    assert len(created) == 1

    result = await db_session.execute(
        select(Task).where(Task.clinic_id == clinic_id).order_by(Task.created_at.desc()).limit(1)
    )
    task = result.scalars().first()
    assert task is not None
    assert task.source == "ai_suggested"
    assert task.patient_id == patient_id
    assert task.attention_kind == "retention_gap"
    assert task.attention_ref_id == patient_id
    assert task.source_event_id is not None


@pytest.mark.asyncio
async def test_ai_task_manager_respects_clinic_daily_limit_zero(
    db_session: AsyncSession,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    await _cleanup_clinic(db_session, clinic_id)
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    db_session.add(
        AiTaskSettings(
            clinic_id=clinic_id,
            ai_tasks_enabled=True,
            creation_mode="auto",
            analyzer_thresholds={"no_show_min_count": 2},
            daily_clinic_limit=0,  # block all creations
            daily_patient_limit=3,
            daily_doctor_limit=5,
        )
    )

    now = datetime.now(timezone.utc)
    for i in range(2):
        db_session.add(
            Booking(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=(now - timedelta(days=2)).date(),
                appointment_time=time(11, 0) if i == 0 else time(11, 30),
                status="no_show",
                prepayment_amount=0,
                created_at=now,
                updated_at=now,
                erp_processed=False,
                erp_error_code=None,
                deleted_at=None,
                paid_by_subscription=False,
                notes=None,
                payment_id=None,
            )
        )
    await db_session.commit()

    repo = TaskRepositoryImpl(db_session)
    svc = TaskService(repo)
    runner = AiTaskManagerRunner(db_session, svc, repo)
    created = await runner.run_for_clinic(clinic_id)
    assert created == []

