"""Tests for analyze_attention_for_tasks tool (TASKS_AI_021)."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai.tools_base import ToolContext
from src.application.ai.tools_tasks import AnalyzeAttentionForTasksArgs, AnalyzeAttentionForTasksTool
from src.application.services.booking_service import BookingService
from src.application.services.schedule_service import ScheduleService
from src.core.context import RequestContext


class _FakeSafeClient:
    def __init__(self, content_json: dict):
        self._content = content_json
        self.last_payload: dict | None = None

    def is_configured(self) -> bool:
        return True

    async def complete(self, payload: dict):
        self.last_payload = payload
        # Return provider-like shape
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(self._content, ensure_ascii=False),
                    }
                }
            ]
        }


@pytest.mark.asyncio
async def test_tool_returns_proposed_tasks_from_llm_json(monkeypatch, db_session: AsyncSession, seed_data) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    async def _fake_build_safe_ai_client(clinic_id, session=None):  # noqa: ANN001
        return _FakeSafeClient(
            {
                "tasks": [
                    {
                        "task_class": "booking.no_show_pattern",
                        "title": "LLM task",
                        "description": "desc",
                        "priority": "high",
                        "role_assignee": "manager",
                        "patient_token": f"PATIENT#{patient_id}",
                        "attention_kind": "retention_gap",
                        "attention_ref_token": f"PATIENT#{patient_id}",
                        "requires_confirmation": True,
                    }
                ]
            }
        ), type("Meta", (), {"provider_type": "external", "allow_personal_data": False})()

    monkeypatch.setattr(
        "src.application.ai.tools_tasks.build_safe_ai_client",
        _fake_build_safe_ai_client,
    )

    tool = AnalyzeAttentionForTasksTool()
    ctx = ToolContext(
        db=db_session,
        clinic_id=clinic_id,
        request_context=RequestContext(clinic_id=clinic_id, user_id=None, user_type="system"),
        source="ai_task_manager",
        booking_service=BookingService(db_session),
        schedule_service=ScheduleService(db_session),
        patient_service=None,
    )
    args = AnalyzeAttentionForTasksArgs(
        clinic_id=clinic_id,
        signals={"booking_no_show_counts": {str(patient_id): 2}},
        allowed_task_classes=["booking.no_show_pattern"],
        creation_mode="confirm",
        existing_attention_task_keys=[],
    )
    res = await tool(ctx, args)
    assert res.success is True
    assert len(res.proposed) == 1
    assert res.proposed[0].patient_id == patient_id


@pytest.mark.asyncio
async def test_tool_tokenizes_birth_date_and_does_not_send_raw_value(
    monkeypatch,
    db_session: AsyncSession,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    fake = _FakeSafeClient({"tasks": []})

    async def _fake_build_safe_ai_client(clinic_id, session=None):  # noqa: ANN001
        return fake, type("Meta", (), {"provider_type": "external", "allow_personal_data": False})()

    monkeypatch.setattr(
        "src.application.ai.tools_tasks.build_safe_ai_client",
        _fake_build_safe_ai_client,
    )

    tool = AnalyzeAttentionForTasksTool()
    ctx = ToolContext(
        db=db_session,
        clinic_id=clinic_id,
        request_context=RequestContext(clinic_id=clinic_id, user_id=None, user_type="system"),
        source="ai_task_manager",
        booking_service=BookingService(db_session),
        schedule_service=ScheduleService(db_session),
        patient_service=None,
    )
    args = AnalyzeAttentionForTasksArgs(
        clinic_id=clinic_id,
        signals={
            "patient_profile": {"birth_date": "1990-01-02"},
            "dob": "1990-01-02",
        },
        allowed_task_classes=[],
        creation_mode="confirm",
        existing_attention_task_keys=[],
    )
    res = await tool(ctx, args)
    assert res.success is True
    assert fake.last_payload is not None
    user_msg = fake.last_payload["messages"][1]["content"]
    assert "1990-01-02" not in user_msg
    assert "BIRTHDATE#" in user_msg

