"""Domain-level error counters for Grafana (QA_ARCH observability)."""

from __future__ import annotations

from uuid import UUID

from src.core.metrics import domain_errors_total
from src.core.prometheus_labels import clinic_bucket_label


def record_domain_error(
    *,
    domain: str,
    code: str,
    clinic_id: UUID | None,
) -> None:
    """Increment ``domain_errors_total`` (patients, bookings, …)."""
    bucket = clinic_bucket_label(clinic_id) if clinic_id else "unknown"
    domain_errors_total.labels(domain=domain, code=code, clinic_bucket=bucket).inc()
