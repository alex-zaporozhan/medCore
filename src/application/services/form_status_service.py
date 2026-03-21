"""Centralized validation of Paperless form status transitions (PPR-2)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.form_status import FormStatus


@dataclass(frozen=True)
class FormStatusTransitionRule:
    from_statuses: tuple[FormStatus, ...]
    to_status: FormStatus


class FormStatusService:
    """State machine for DigitalFormSubmission.status."""

    _rules: tuple[FormStatusTransitionRule, ...] = (
        FormStatusTransitionRule(
            from_statuses=(FormStatus.DRAFT,),
            to_status=FormStatus.ISSUED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.DRAFT,),
            to_status=FormStatus.CANCELLED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.ISSUED, FormStatus.IN_PROGRESS),
            to_status=FormStatus.IN_PROGRESS,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.ISSUED, FormStatus.IN_PROGRESS, FormStatus.DRAFT),
            to_status=FormStatus.SIGNED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.ISSUED, FormStatus.IN_PROGRESS),
            to_status=FormStatus.CANCELLED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.ISSUED, FormStatus.IN_PROGRESS),
            to_status=FormStatus.EXPIRED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.SIGNED,),
            to_status=FormStatus.REVOKED,
        ),
        # Legacy/corrupt rows: allow signing or closing without crashing the pipeline.
        FormStatusTransitionRule(
            from_statuses=(FormStatus.UNKNOWN,),
            to_status=FormStatus.SIGNED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.UNKNOWN,),
            to_status=FormStatus.REVOKED,
        ),
        FormStatusTransitionRule(
            from_statuses=(FormStatus.UNKNOWN,),
            to_status=FormStatus.CANCELLED,
        ),
    )

    def can_transition(self, from_status: FormStatus, to_status: FormStatus) -> bool:
        if from_status == to_status:
            return True
        for rule in self._rules:
            if from_status in rule.from_statuses and rule.to_status == to_status:
                return True
        return False

    def assert_transition(self, from_status: FormStatus, to_status: FormStatus) -> None:
        if not self.can_transition(from_status, to_status):
            raise ValueError(f"Form transition {from_status.value} -> {to_status.value} is not allowed")
