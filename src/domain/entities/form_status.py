"""Lifecycle status for digital form instances (Paperless / FormInstance)."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class FormStatus(str, Enum):
    """Unified form instance statuses (PPR-2)."""

    DRAFT = "draft"
    ISSUED = "issued"
    IN_PROGRESS = "in_progress"
    SIGNED = "signed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REVOKED = "revoked"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str | None) -> FormStatus:
        """Parse DB value; unknown/invalid strings map to UNKNOWN (logged), never raise."""
        if not value:
            return cls.SIGNED
        try:
            return cls(value)
        except ValueError:
            logger.warning(
                "paperless_invalid_status_in_db",
                extra={"raw_status": value[:64] if isinstance(value, str) else str(value)},
            )
            return cls.UNKNOWN
