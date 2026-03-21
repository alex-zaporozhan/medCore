from __future__ import annotations

import uuid

import pytest

from src.application.services.lead_stage_state_machine import LeadStageStateMachine


@pytest.mark.parametrize(
    "from_code,to_code,allowed",
    [
        ("start", "scheduled", True),
        ("scheduled", "won", True),
        ("scheduled", "lost", True),
        ("won", "lost", False),
        ("lost", "won", False),
        ("start", "start", True),
    ],
)
def test_state_machine_can_transition(from_code: str, to_code: str, allowed: bool):
    sm = LeadStageStateMachine()
    assert sm.can_transition_semantic(from_code, to_code) is allowed


def test_state_machine_assert_transition_raises_for_invalid():
    sm = LeadStageStateMachine()
    with pytest.raises(ValueError):
        sm.assert_transition_semantic("won", "scheduled")

