"""Commerce import job persistence and idempotent replay (4-F5)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.commerce_store_service import CommerceCsvImportResult
from src.domain.entities.commerce_import_job import CommerceImportJob

COMMERCE_IMPORT_STATUS_COMMITTED = "committed"
COMMERCE_IMPORT_STATUS_FAILED = "failed"


class CommerceImportJobError(Exception):
    """Domain error for import job / idempotency."""


def _scopes_match(
    job: CommerceImportJob,
    *,
    source_profile: str,
    clinic_id: UUID,
    stock_location_id: UUID | None,
) -> bool:
    if job.source_profile != source_profile:
        return False
    if job.clinic_id != clinic_id:
        return False
    jloc = job.stock_location_id
    if (jloc or None) != (stock_location_id or None):
        return False
    return True


def build_commerce_import_payload_summary(
    *,
    source_profile: str,
    file_name: str | None,
    result: CommerceCsvImportResult,
) -> dict[str, Any]:
    return {
        "profile": source_profile,
        "file_name": file_name,
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "errors": list(result.errors),
    }


def result_from_summary(source_profile: str, summary: dict[str, Any] | None) -> CommerceCsvImportResult:
    if not summary:
        return CommerceCsvImportResult(created=0, updated=0, skipped=0, errors=[])
    return CommerceCsvImportResult(
        created=int(summary.get("created", 0)),
        updated=int(summary.get("updated", 0)),
        skipped=int(summary.get("skipped", 0)),
        errors=list(summary.get("errors") or []),
    )


async def get_import_job_by_org_and_key(
    session: AsyncSession,
    organization_id: UUID,
    idempotency_key: str,
) -> CommerceImportJob | None:
    res = await session.execute(
        select(CommerceImportJob).where(
            CommerceImportJob.organization_id == organization_id,
            CommerceImportJob.idempotency_key == idempotency_key,
        )
    )
    return res.scalar_one_or_none()


async def try_replay_committed_import(
    session: AsyncSession,
    organization_id: UUID,
    idempotency_key: str | None,
    *,
    source_profile: str,
    clinic_id: UUID,
    stock_location_id: UUID | None,
) -> CommerceCsvImportResult | None:
    """If a committed job exists for the key and scope matches, return stored result (no DB writes)."""
    if not idempotency_key:
        return None
    job = await get_import_job_by_org_and_key(session, organization_id, idempotency_key)
    if job is None:
        return None
    if job.status != COMMERCE_IMPORT_STATUS_COMMITTED:
        return None
    if not _scopes_match(
        job,
        source_profile=source_profile,
        clinic_id=clinic_id,
        stock_location_id=stock_location_id,
    ):
        raise CommerceImportJobError("idempotency_scope_mismatch")
    return result_from_summary(source_profile, job.payload_summary)


async def upsert_import_job_record(
    session: AsyncSession,
    *,
    organization_id: UUID,
    clinic_id: UUID,
    stock_location_id: UUID | None,
    source_profile: str,
    idempotency_key_stored: str,
    file_name: str | None,
    created_by_admin_id: UUID | None,
    status: str,
    payload_summary: dict[str, Any] | None,
    last_error: str | None,
) -> CommerceImportJob:
    job = await get_import_job_by_org_and_key(session, organization_id, idempotency_key_stored)
    if job is None:
        job = CommerceImportJob(
            id=uuid.uuid4(),
            organization_id=organization_id,
            clinic_id=clinic_id,
            stock_location_id=stock_location_id,
            source_profile=source_profile,
            status=status,
            idempotency_key=idempotency_key_stored,
            file_name=file_name,
            payload_summary=payload_summary,
            created_by_admin_id=created_by_admin_id,
            last_error=last_error,
        )
        session.add(job)
    else:
        job.clinic_id = clinic_id
        job.stock_location_id = stock_location_id
        job.source_profile = source_profile
        job.status = status
        job.file_name = file_name
        job.payload_summary = payload_summary
        job.last_error = last_error
        job.created_by_admin_id = created_by_admin_id
    await session.flush()
    return job


async def list_import_jobs_for_clinic(
    session: AsyncSession,
    *,
    organization_id: UUID,
    clinic_id: UUID,
    limit: int = 50,
) -> list[CommerceImportJob]:
    lim = max(1, min(limit, 100))
    res = await session.execute(
        select(CommerceImportJob)
        .where(
            CommerceImportJob.organization_id == organization_id,
            CommerceImportJob.clinic_id == clinic_id,
        )
        .order_by(CommerceImportJob.created_at.desc())
        .limit(lim)
    )
    return list(res.scalars().all())
