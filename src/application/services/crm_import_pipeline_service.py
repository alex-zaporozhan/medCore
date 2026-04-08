"""CRM import §25.0 pipeline: ingest → validate → clean → staging → commit (Phase 3+)."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.crm_import_job_audit import CrmImportJobAudit
from src.domain.entities.crm_import_staging_job import CrmImportStagingJob
from src.application.services.lead_service import LeadService


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D+", "", raw)
    if len(digits) < 10:
        return None
    return digits


def validate_and_clean_contact_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (cleaned_rows, validation_errors)."""
    errors: list[str] = []
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            errors.append(f"row {i}: object expected")
            continue
        name = (r.get("name") or "").strip()
        if not name:
            errors.append(f"row {i}: name is required")
            continue
        if len(name) > 255:
            errors.append(f"row {i}: name too long")
            continue
        email = (r.get("email") or "").strip() or None
        phone = _normalize_phone((r.get("phone") or "").strip() or None)
        out.append(
            {
                "name": name[:255],
                "email": email[:255] if email else None,
                "phone": phone,
            }
        )
    return out, errors


async def log_import_audit(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    actor_admin_id: uuid.UUID | None,
    step: str,
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(
        CrmImportJobAudit(
            id=uuid.uuid4(),
            job_id=job_id,
            actor_admin_id=actor_admin_id,
            step=step,
            meta=meta,
        )
    )
    await session.flush()


async def commit_crm_import_job(
    session: AsyncSession,
    *,
    job: CrmImportStagingJob,
    clinic_id: uuid.UUID,
    actor_admin_id: uuid.UUID | None,
) -> tuple[int, list[uuid.UUID]]:
    """
    Create CRM leads from staged cleaned rows in payload_summary['cleaned_rows'].
    Returns (created_count, lead_ids).
    """
    summary = job.payload_summary or {}
    rows = summary.get("cleaned_rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("nothing_to_commit")

    lead_service = LeadService(session)
    created_ids: list[uuid.UUID] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = (row.get("name") or "").strip() or "Импорт CRM"
        lead = await lead_service.create_lead_from_contact(
            clinic_id=clinic_id,
            omnichannel_contact_id=None,
            patient_id=None,
            title=title[:255],
            source="crm_import_csv_contacts_v1",
            estimated_value=Decimal("0.00"),
        )
        created_ids.append(lead.id)

    job.status = "committed"
    job.payload_summary = {
        **summary,
        "committed_lead_ids": [str(x) for x in created_ids],
        "committed_count": len(created_ids),
    }
    job.last_error = None
    await session.flush()
    await log_import_audit(
        session,
        job_id=job.id,
        actor_admin_id=actor_admin_id,
        step="commit",
        meta={"created": len(created_ids)},
    )
    return len(created_ids), created_ids
