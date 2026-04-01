"""Low-cardinality label helpers for Prometheus (OBS / QA_ARCH)."""

from __future__ import annotations

import zlib
from uuid import UUID

# Fixed 32 buckets — same order of magnitude as Redis DB index in many setups; avoids unbounded `clinic_id` series.
_CLINIC_BUCKET_MOD = 32


def clinic_bucket_label(clinic_id: UUID | str | None) -> str:
    """Map tenant id to one of 32 buckets for histogram/counter labels (not for logs)."""
    if clinic_id is None:
        return "unknown"
    raw = str(clinic_id).encode("utf-8")
    return str(zlib.crc32(raw) % _CLINIC_BUCKET_MOD)


def account_bucket_label(account_id: UUID | str | None) -> str:
    """Same bucketing for omnichannel `business_account_id` (avoids per-tenant series explosion)."""
    return clinic_bucket_label(account_id)


def admin_bucket_label(admin_id: UUID | str | None) -> str:
    """Map admin id to one of 32 buckets (low-cardinality SOC signals)."""
    return clinic_bucket_label(admin_id)
