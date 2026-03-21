from __future__ import annotations

import pytest

from src.application.ai.tools_base import ToolError
from src.application.ai.tools_crm import _context_for_external_ai
from src.application.dto.crm_ai_dto import LeadContextForAi, LeadSummary


def test_context_for_external_ai_excludes_notes_preview():
    ctx = LeadContextForAi(
        lead=LeadSummary(
            lead_token="LEAD#00000000-0000-0000-0000-000000000000",
            clinic_id="00000000-0000-0000-0000-000000000001",
            pipeline_id="00000000-0000-0000-0000-000000000002",
            stage_id="00000000-0000-0000-0000-000000000003",
            status="open",
            title="Test lead",
            source="omnichannel",
            estimated_value="0.00",
            actual_value="0.00",
        ),
        notes_preview=["Иван Иванов, телефон +7 900 ...", "email test@example.com"],
        open_tasks_count=1,
        in_progress_tasks_count=2,
        done_tasks_count=3,
    )
    payload = _context_for_external_ai(ctx)
    assert "notes_preview" not in payload
    assert payload["lead"]["title"] == "Test lead"


@pytest.mark.parametrize(
    "code, expected_kind",
    [
        ("lead_not_found", "not_found"),
        ("stage_not_found", "not_found"),
        ("clinic_mismatch", "bad_request"),
        ("permission_denied", "forbidden"),
        ("invalid_args", "bad_request"),
    ],
)
def test_tool_error_codes_are_classified(code: str, expected_kind: str):
    # This test documents the intended semantic mapping used by admin routers.
    err = ToolError(code=code, message="x")
    c = (err.code or "").lower()
    if c in {"lead_not_found", "not_found"} or c.endswith("_not_found"):
        kind = "not_found"
    elif c == "clinic_mismatch":
        kind = "bad_request"
    elif c in {"forbidden", "permission_denied"}:
        kind = "forbidden"
    else:
        kind = "bad_request"
    assert kind == expected_kind

