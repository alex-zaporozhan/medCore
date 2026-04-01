"""Tests for Tasks & Attention integration (AttentionFeedService + TaskService)."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.attention_feed_service import AttentionFeedService
from src.application.services.task_service import TaskService
from src.application.dto.attention_feed_dto import AttentionItemRead
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.booking import Booking
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.core.datetime_utils import utc_now, utc_now_naive


@pytest.fixture
def task_service(db_session: AsyncSession) -> TaskService:
    repo: TaskRepository = TaskRepositoryImpl(db_session)
    return TaskService(repo)


async def _get_feed_item_for(
    service: AttentionFeedService,
    clinic_id: uuid.UUID,
    kind: str,
) -> AttentionItemRead | None:
    feed = await service.get_feed(clinic_id)
    items: list[AttentionItemRead] = []
    if kind == "follow_up":
        items = feed.follow_up
    elif kind == "retention_gap":
        items = feed.retention_gap
    elif kind == "conflict":
        items = feed.conflicts
    return items[0] if items else None


@pytest.mark.asyncio
async def test_attention_follow_up_status_changes_with_tasks(
    db_session: AsyncSession,
    task_service: TaskService,
    seed_data,
) -> None:
    """Scenario 1: follow_up Attention -> one task -> status transitions new -> in_progress -> resolved."""
    clinic_id: uuid.UUID = seed_data["clinic_id"]
    patient_id: uuid.UUID = seed_data["patient_id"]

    # Seed follow_up chat message
    now = utc_now_naive()
    conv_id = uuid.uuid4()
    from src.domain.entities.conversation import Conversation

    db_session.add(
        Conversation(
            id=conv_id,
            clinic_id=clinic_id,
            patient_id=patient_id,
            assigned_admin_id=None,
        )
    )
    await db_session.flush()
    msg = ChatMessage(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        conversation_id=conv_id,
        body="Перезвонить пациенту",
        sender_type="patient",
        follow_up_at=now,
        follow_up_closed=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(msg)
    await db_session.flush()

    attention_service = AttentionFeedService(db_session)

    # Initially: no tasks -> Attention should be new
    item = await _get_feed_item_for(attention_service, clinic_id, "follow_up")
    assert item is not None
    assert item.kind == "follow_up"
    assert item.status == "new"
    assert item.tasks_total == 0

    # Create a task linked to this Attention
    task = await task_service.create_task(
        clinic_id=clinic_id,
        title="Позвонить пациенту",
        description="Связаться по поводу отмены",
        priority="medium",
        creator_id=None,
        assignee_id=None,
        role_assignee=None,
        due_at=utc_now(),
        patient_id=patient_id,
        source="from_attention",
        attention_kind="follow_up",
        attention_ref_id=msg.id,
    )
    assert task.attention_kind == "follow_up"
    assert task.attention_ref_id == msg.id

    # After task creation: still open -> Attention should be in_progress
    item = await _get_feed_item_for(attention_service, clinic_id, "follow_up")
    assert item is not None
    assert item.tasks_total == 1
    assert item.tasks_open + item.tasks_in_progress == 1
    assert item.status == "in_progress"

    # Mark task as done -> Attention should become resolved
    await task_service.update_task_fields(task_id=task.id, checklist_done=True)
    await task_service.update_task_status(
        task_id=task.id,
        status="done",
        completed_at=datetime.utcnow(),
    )

    item = await _get_feed_item_for(attention_service, clinic_id, "follow_up")
    assert item is not None
    assert item.tasks_total == 1
    assert item.tasks_done == 1
    assert item.status == "resolved"


@pytest.mark.asyncio
async def test_attention_retention_and_conflict_status_aggregation(
    db_session: AsyncSession,
    task_service: TaskService,
    seed_data,
) -> None:
    """Scenario 2: retention_gap/conflict Attention with multiple tasks and mixed statuses."""
    clinic_id: uuid.UUID = seed_data["clinic_id"]
    patient_id: uuid.UUID = seed_data["patient_id"]
    doctor_id: uuid.UUID = seed_data["doctor_id"]
    service_id: uuid.UUID = seed_data["service_id"]

    # Seed a booking to appear in retention_gap (simplified: directly create a Booking old enough)
    old_date = (utc_now() - timedelta(days=365)).date()
    booking = Booking(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        service_id=service_id,
        appointment_date=old_date,
        appointment_time=datetime.utcnow().time(),
        status="completed",
        prepayment_amount=1000,
        payment_id=None,
        paid_by_subscription=False,
        notes=None,
        erp_processed=False,
        erp_error_code=None,
        created_at=utc_now_naive(),
        updated_at=utc_now_naive(),
        deleted_at=None,
    )
    db_session.add(booking)
    await db_session.flush()

    attention_service = AttentionFeedService(db_session)
    item = await _get_feed_item_for(attention_service, clinic_id, "retention_gap")
    assert item is not None
    assert item.kind == "retention_gap"

    # Case A: one open + one done -> in_progress
    task1 = await task_service.create_task(
        clinic_id=clinic_id,
        title="Позвонить про возврат",
        description=None,
        priority="high",
        creator_id=None,
        assignee_id=None,
        role_assignee=None,
        due_at=None,
        patient_id=patient_id,
        source="from_attention",
        attention_kind="retention_gap",
        attention_ref_id=item.id,
    )
    task2 = await task_service.create_task(
        clinic_id=clinic_id,
        title="Отправить письмо с предложением",
        description=None,
        priority="medium",
        creator_id=None,
        assignee_id=None,
        role_assignee=None,
        due_at=None,
        patient_id=patient_id,
        source="from_attention",
        attention_kind="retention_gap",
        attention_ref_id=item.id,
    )
    await task_service.update_task_fields(task_id=task2.id, checklist_done=True)
    await task_service.update_task_status(
        task_id=task2.id,
        status="done",
        completed_at=datetime.utcnow(),
    )

    item = await _get_feed_item_for(attention_service, clinic_id, "retention_gap")
    assert item is not None
    assert item.tasks_total == 2
    assert item.tasks_in_progress + item.tasks_open >= 1
    assert item.status == "in_progress"

    # Case B: все задачи done/cancelled -> resolved
    await task_service.update_task_status(
        task_id=task1.id,
        status="cancelled",
        completed_at=datetime.utcnow(),
    )
    item = await _get_feed_item_for(attention_service, clinic_id, "retention_gap")
    assert item is not None
    assert item.tasks_done + item.tasks_cancelled == item.tasks_total
    assert item.status == "resolved"


@pytest.mark.asyncio
async def test_attention_task_mapping_by_kind_and_ref_id(
    db_session: AsyncSession,
    task_service: TaskService,
    seed_data,
) -> None:
    """Scenario 3: multiple tasks mapped to a single (attention_kind, attention_ref_id)."""
    clinic_id: uuid.UUID = seed_data["clinic_id"]

    # Create synthetic Attention-like id for conflict kind
    attention_id = uuid.uuid4()

    # Create several tasks pointing to the same key
    for i in range(3):
        await task_service.create_task(
            clinic_id=clinic_id,
            title=f"Конфликт #{i+1}",
            description=None,
            priority="medium",
            creator_id=None,
            assignee_id=None,
            role_assignee=None,
            due_at=None,
            source="from_attention",
            attention_kind="conflict",
            attention_ref_id=attention_id,
        )

    # Manually build one AttentionItemRead and call the private enrichment to validate mapping
    service = AttentionFeedService(db_session)
    item = AttentionItemRead(
        id=attention_id,
        clinic_id=clinic_id,
        patient_id=seed_data["patient_id"],
        kind="conflict",
        title="Конфликтный пациент",
        description="Тестовое внимание",
        priority=95,
        due_at=None,
        created_at=utc_now(),
        updated_at=utc_now(),
        patient_full_name=None,
        patient_phone="",
        patient_tags=[],
        status="new",
        assigned_admin_id=None,
        assigned_admin_name=None,
        has_comment=False,
        last_comment_preview=None,
        conversation_id=None,
        tasks_total=0,
        tasks_open=0,
        tasks_in_progress=0,
        tasks_done=0,
        tasks_cancelled=0,
    )

    await service._enrich_with_tasks_and_status(clinic_id, [item])  # type: ignore[attr-defined]

    assert item.tasks_total == 3
    assert item.status in ("new", "in_progress")

