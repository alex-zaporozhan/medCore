"""Low-cardinality Prometheus label helpers."""

from uuid import UUID

from src.core.prometheus_labels import clinic_bucket_label


def test_clinic_bucket_label_stable_for_uuid() -> None:
    u = UUID("550e8400-e29b-41d4-a716-446655440000")
    a = clinic_bucket_label(u)
    b = clinic_bucket_label(str(u))
    assert a == b
    assert a in {str(i) for i in range(32)}


def test_clinic_bucket_label_unknown() -> None:
    assert clinic_bucket_label(None) == "unknown"
