"""Multi-tenant helpers: enforce clinic boundaries on domain entities."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.core.patient_messages import BOOKING_NOT_FOUND
from src.core.metrics import multitenancy_clinic_mismatch_total

logger = logging.getLogger(__name__)


class EntityClinicMismatchError(LookupError):
    """Entity does not belong to the requested clinic; treat as not found at API boundary (e.g. schedule guard)."""


class ClinicForbiddenError(Exception):
    """Entity exists but belongs to another clinic — use HTTP 403 on admin routes; 404 on patient routes."""

    def __init__(
        self,
        *,
        entity_label: str,
        expected_clinic_id: UUID,
        entity_clinic_id: UUID | None = None,
        entity_id: UUID | None = None,
        message: str = "Доступ к объекту другой клиники запрещён.",
    ) -> None:
        super().__init__(message)
        self.entity_label = entity_label
        self.expected_clinic_id = expected_clinic_id
        self.entity_clinic_id = entity_clinic_id
        self.entity_id = entity_id
        self.message = message


def assert_entity_belongs_to_clinic(
    entity: Any,
    clinic_id: UUID,
    *,
    entity_label: str = "entity",
    not_found_message: str = BOOKING_NOT_FOUND,
) -> None:
    """Raise EntityClinicMismatchError if entity has no clinic_id; ClinicForbiddenError if wrong clinic."""
    eid = getattr(entity, "clinic_id", None)
    e_uuid = getattr(entity, "id", None)
    if eid is None:
        logger.warning(
            "multitenancy_missing_clinic_id",
            extra={"entity_label": entity_label, "expected_clinic_id": str(clinic_id)},
        )
        try:
            multitenancy_clinic_mismatch_total.labels(source="assert_entity_missing").inc()
        except Exception:
            pass
        raise EntityClinicMismatchError(not_found_message)
    if eid != clinic_id:
        logger.warning(
            "multitenancy_clinic_mismatch",
            extra={
                "entity_label": entity_label,
                "entity_clinic_id": str(eid),
                "expected_clinic_id": str(clinic_id),
            },
        )
        try:
            multitenancy_clinic_mismatch_total.labels(source="assert_entity").inc()
        except Exception:
            pass
        raise ClinicForbiddenError(
            entity_label=entity_label,
            expected_clinic_id=clinic_id,
            entity_clinic_id=eid,
            entity_id=e_uuid if isinstance(e_uuid, UUID) else None,
        )
