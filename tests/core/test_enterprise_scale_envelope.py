"""0-F1: code-side anchors mirror ENTERPRISE_SAAS_SCALE_ENVELOPE.md §1."""

from src.core.enterprise_scale_envelope import (
    DEFAULT_ADMIN_LIST_PAGE_SIZE_CAP,
    MAX_ACTIVE_ORGANIZATIONS_MARKETING,
)


def test_envelope_constants_are_positive_sane():
    assert MAX_ACTIVE_ORGANIZATIONS_MARKETING == 10_000
    assert DEFAULT_ADMIN_LIST_PAGE_SIZE_CAP >= 50
