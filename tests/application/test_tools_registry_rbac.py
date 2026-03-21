"""RBAC filtering for AI tool registry (QA_ARCH W4.1 C7)."""

from uuid import uuid4

import pytest

from src.application.ai.tools_base import ToolContext
from src.application.ai.tools_registry import list_tools_for_context
from src.application.services.booking_service import BookingService
from src.application.services.patient_service import PatientService
from src.application.services.schedule_service import ScheduleService
from src.core.context import RequestContext
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_list_tools_omni_requires_booking_ai_permission(init_db, seed_data, redis_client):
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        bs = BookingService(session)
        ss = ScheduleService(session)
        ps = PatientService(session)
        empty = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                permissions=set(),
                roles=set(),
            ),
            source="omni_chat",
            booking_service=bs,
            schedule_service=ss,
            patient_service=ps,
        )
        granted = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                permissions={"booking.ai_tools.use"},
                roles=set(),
            ),
            source="omni_chat",
            booking_service=bs,
            schedule_service=ss,
            patient_service=ps,
        )
        assert "get_available_slots" not in list_tools_for_context(empty, source="omni_chat")
        assert "get_available_slots" in list_tools_for_context(granted, source="omni_chat")


@pytest.mark.asyncio
async def test_list_tools_analyze_attention_requires_ai_tasks_run(init_db, seed_data, redis_client):
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        bs = BookingService(session)
        ss = ScheduleService(session)
        ps = PatientService(session)
        no_run = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=uuid4(),
                user_type="admin",
                permissions={"booking.ai_tools.use"},
                roles={"manager"},
            ),
            source="admin_ui",
            booking_service=bs,
            schedule_service=ss,
            patient_service=ps,
        )
        with_run = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=uuid4(),
                user_type="admin",
                permissions={"booking.ai_tools.use", "ai.tasks.run"},
                roles={"manager"},
            ),
            source="admin_ui",
            booking_service=bs,
            schedule_service=ss,
            patient_service=ps,
        )
        assert "analyze_attention_for_tasks" not in list_tools_for_context(no_run, source="admin_ui")
        assert "analyze_attention_for_tasks" in list_tools_for_context(with_run, source="admin_ui")
