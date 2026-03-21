"""Unit tests for FormStatusService (Paperless PPR-2)."""

import pytest

from src.application.services.form_status_service import FormStatusService
from src.domain.entities.form_status import FormStatus


def test_same_status_always_allowed() -> None:
    svc = FormStatusService()
    assert svc.can_transition(FormStatus.ISSUED, FormStatus.ISSUED)


def test_issued_to_signed_allowed() -> None:
    svc = FormStatusService()
    assert svc.can_transition(FormStatus.ISSUED, FormStatus.SIGNED)


def test_signed_to_revoked_allowed() -> None:
    svc = FormStatusService()
    assert svc.can_transition(FormStatus.SIGNED, FormStatus.REVOKED)


def test_issued_to_revoked_not_allowed() -> None:
    svc = FormStatusService()
    assert not svc.can_transition(FormStatus.ISSUED, FormStatus.REVOKED)


def test_assert_transition_raises() -> None:
    svc = FormStatusService()
    with pytest.raises(ValueError, match="not allowed"):
        svc.assert_transition(FormStatus.ISSUED, FormStatus.REVOKED)


def test_unknown_to_signed_allowed() -> None:
    svc = FormStatusService()
    assert svc.can_transition(FormStatus.UNKNOWN, FormStatus.SIGNED)


def test_unknown_to_revoked_allowed() -> None:
    svc = FormStatusService()
    assert svc.can_transition(FormStatus.UNKNOWN, FormStatus.REVOKED)
