from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class LeadStageTransitionRule:
    """
    A single transition rule between logical stage codes.

    We intentionally define rules by `LeadStage.code` (stable identifiers),
    not by DB ids, so that pipelines can be reconfigured per clinic while
    preserving expected lifecycle semantics.
    """

    from_codes: tuple[str, ...]
    to_codes: tuple[str, ...]


def _norm(code: str | None) -> str:
    return (code or "").strip().lower()


class LeadStageStateMachine:
    """
    Centralized state-machine for lead stage transitions (CRM_EVENTS_007).

    v1 policy:
    - AI/event-driven transitions must follow the ruleset below.
    - Manual transitions (Kanban drag&drop) remain possible even when non-standard,
      but are flagged by caller for audit/metrics.

    NOTE: Pipelines may use different codes; therefore we support groups of codes
    for the same semantic states (e.g. booked/scheduled/appointment).
    """

    # Stable semantic codes (see LeadStageSemanticsService).
    SEM_START = "start"
    SEM_SCHEDULED = "scheduled"
    SEM_STALE = "stale"
    SEM_WON = "won"
    SEM_LOST = "lost"

    _rules: tuple[LeadStageTransitionRule, ...] = (
        LeadStageTransitionRule(from_codes=(SEM_START,), to_codes=(SEM_SCHEDULED, SEM_STALE, SEM_LOST)),
        LeadStageTransitionRule(from_codes=(SEM_SCHEDULED,), to_codes=(SEM_WON, SEM_LOST, SEM_STALE)),
        LeadStageTransitionRule(from_codes=(SEM_STALE,), to_codes=(SEM_SCHEDULED, SEM_WON, SEM_LOST)),
        LeadStageTransitionRule(from_codes=(SEM_WON,), to_codes=(SEM_WON,)),
        LeadStageTransitionRule(from_codes=(SEM_LOST,), to_codes=(SEM_LOST,)),
    )

    def can_transition_semantic(self, from_semantic: str | None, to_semantic: str | None) -> bool:
        f = _norm(from_semantic)
        t = _norm(to_semantic)
        if not f or not t:
            return False
        if f == t:
            return True
        for rule in self._rules:
            if f in rule.from_codes and t in rule.to_codes:
                return True
        return False

    def assert_transition_semantic(self, from_semantic: str | None, to_semantic: str | None) -> None:
        if not self.can_transition_semantic(from_semantic, to_semantic):
            raise ValueError(f"LeadStage transition {_norm(from_semantic)} -> {_norm(to_semantic)} is not allowed")

