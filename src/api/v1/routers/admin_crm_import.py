"""CRM import pipeline (ADR-010, Phase 3+): §25.0 ingest → validate → clean → staging → commit.

SaaS entitlement: ``import.crm_v1`` (enforced in ``get_crm_import_organization_id``).
"""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.crm_import_dependencies import get_crm_import_organization_id
from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.crm_import_pipeline_service import (
    commit_crm_import_job,
    log_import_audit,
    validate_and_clean_contact_rows,
)
from src.core.metrics import crm_import_operations_total
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.crm_import_staging_job import CrmImportStagingJob

ALLOWED_CRM_IMPORT_SOURCE_PROFILES: frozenset[str] = frozenset(
    {
        "csv_contacts_v1",
        "bitrix24_contacts_v1",
    }
)

router = APIRouter(
    prefix="/admin/organization/crm-import",
    tags=["admin-crm-import"],
    dependencies=[Depends(require_permissions("manage_crm"))],
)


class CrmImportContactRow(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=64)
    email: str | None = Field(None, max_length=255)


class CrmImportDryRunRequest(BaseModel):
    source_profile: str = Field(
        ...,
        max_length=64,
        description="Профиль источника, напр. csv_contacts_v1, bitrix24_contacts_v1",
    )
    idempotency_key: str | None = Field(None, max_length=255)
    rows: list[CrmImportContactRow] | None = Field(
        None,
        description="Опционально: строки контактов для полного dry-run (validate/clean/staging).",
    )


class CrmImportDryRunResponse(BaseModel):
    job_id: str
    organization_id: str
    status: str
    source_profile: str
    rows_validated: int
    message: str
    validation_errors: list[str] = Field(default_factory=list)


class CrmImportJobListItem(BaseModel):
    job_id: str
    status: str
    source_profile: str
    created_at: str


class CrmImportCommitResponse(BaseModel):
    job_id: str
    committed_count: int
    lead_ids: list[str]


def _rows_as_dicts(rows: list[CrmImportContactRow] | None) -> list[dict]:
    if not rows:
        return []
    return [r.model_dump() for r in rows]


@router.post("/dry-run", response_model=CrmImportDryRunResponse)
async def create_dry_run_job(
    body: CrmImportDryRunRequest,
    response: Response,
    org_id: UUID = Depends(get_crm_import_organization_id),
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
) -> CrmImportDryRunResponse:
    profile = body.source_profile.strip()[:64]
    if profile not in ALLOWED_CRM_IMPORT_SOURCE_PROFILES:
        crm_import_operations_total.labels(endpoint="dry_run", outcome="invalid_profile").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_source_profile",
                "message": "Неизвестный профиль источника импорта.",
                "allowed": sorted(ALLOWED_CRM_IMPORT_SOURCE_PROFILES),
            },
        )

    key = (body.idempotency_key or "").strip() or str(uuid.uuid4())
    existing = (
        await session.execute(
            select(CrmImportStagingJob).where(
                CrmImportStagingJob.organization_id == org_id,
                CrmImportStagingJob.idempotency_key == key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        crm_import_operations_total.labels(endpoint="dry_run", outcome="idempotent").inc()
        summary = existing.payload_summary or {}
        return CrmImportDryRunResponse(
            job_id=str(existing.id),
            organization_id=str(org_id),
            status=existing.status,
            source_profile=existing.source_profile,
            rows_validated=int(summary.get("rows_validated", 0)),
            message="Существующая заявка по idempotency_key",
            validation_errors=list(summary.get("validation_errors", []) or []),
        )

    raw_rows = _rows_as_dicts(body.rows)
    if profile == "bitrix24_contacts_v1" and not raw_rows:
        job = CrmImportStagingJob(
            id=uuid.uuid4(),
            organization_id=org_id,
            clinic_id=admin.clinic_id,
            source_profile=profile,
            status="ingested",
            idempotency_key=key[:255],
            payload_summary={
                "phase": "3_pipeline",
                "connector": "bitrix24_stub",
                "rows_validated": 0,
                "message": "Коннектор без тела запроса — зафиксирован шаг ingest.",
            },
            created_by_admin_id=admin.id,
        )
        session.add(job)
        await session.flush()
        await log_import_audit(
            session,
            job_id=job.id,
            actor_admin_id=admin.id,
            step="ingest",
            meta={"profile": profile},
        )
        response.status_code = status.HTTP_201_CREATED
        crm_import_operations_total.labels(endpoint="dry_run", outcome="created").inc()
        return CrmImportDryRunResponse(
            job_id=str(job.id),
            organization_id=str(org_id),
            status=job.status,
            source_profile=job.source_profile,
            rows_validated=0,
            message="Ingest для внешнего коннектора (строки добавьте в следующем запросе или отдельном эндпоинте).",
        )

    if not raw_rows:
        job = CrmImportStagingJob(
            id=uuid.uuid4(),
            organization_id=org_id,
            clinic_id=admin.clinic_id,
            source_profile=profile,
            status="ingested",
            idempotency_key=key[:255],
            payload_summary={
                "phase": "3_pipeline",
                "rows_validated": 0,
                "message": "Нет строк в запросе — зафиксирован шаг ingest (заглушка конвейера).",
            },
            created_by_admin_id=admin.id,
        )
        session.add(job)
        await session.flush()
        await log_import_audit(
            session,
            job_id=job.id,
            actor_admin_id=admin.id,
            step="ingest",
            meta={"profile": profile, "empty_payload": True},
        )
        response.status_code = status.HTTP_201_CREATED
        crm_import_operations_total.labels(endpoint="dry_run", outcome="created").inc()
        return CrmImportDryRunResponse(
            job_id=str(job.id),
            organization_id=str(org_id),
            status=job.status,
            source_profile=job.source_profile,
            rows_validated=0,
            message="Ingest без строк данных; передайте rows для validate/clean/staging.",
        )

    cleaned, val_errors = validate_and_clean_contact_rows(raw_rows)
    job_id = uuid.uuid4()

    if not cleaned:
        job = CrmImportStagingJob(
            id=job_id,
            organization_id=org_id,
            clinic_id=admin.clinic_id,
            source_profile=profile,
            status="validation_failed",
            idempotency_key=key[:255],
            payload_summary={
                "rows_validated": 0,
                "validation_errors": val_errors,
                "phase": "3_pipeline",
            },
            created_by_admin_id=admin.id,
            last_error="validation_failed",
        )
        session.add(job)
        await session.flush()
        await log_import_audit(
            session,
            job_id=job.id,
            actor_admin_id=admin.id,
            step="validate",
            meta={"input_rows": len(raw_rows), "valid_rows": 0},
        )
        await log_import_audit(
            session,
            job_id=job.id,
            actor_admin_id=admin.id,
            step="staging",
            meta={"outcome": "validation_failed"},
        )
        response.status_code = status.HTTP_201_CREATED
        crm_import_operations_total.labels(endpoint="dry_run", outcome="validation_failed").inc()
        return CrmImportDryRunResponse(
            job_id=str(job.id),
            organization_id=str(org_id),
            status=job.status,
            source_profile=job.source_profile,
            rows_validated=0,
            message="Валидация не прошла",
            validation_errors=val_errors,
        )

    job = CrmImportStagingJob(
        id=job_id,
        organization_id=org_id,
        clinic_id=admin.clinic_id,
        source_profile=profile,
        status="staged",
        idempotency_key=key[:255],
        payload_summary={
            "rows_validated": len(cleaned),
            "validation_errors": val_errors,
            "cleaned_rows": cleaned,
            "phase": "3_pipeline",
        },
        created_by_admin_id=admin.id,
    )
    session.add(job)
    await session.flush()
    await log_import_audit(
        session,
        job_id=job.id,
        actor_admin_id=admin.id,
        step="ingest",
        meta={"input_rows": len(raw_rows)},
    )
    await log_import_audit(
        session,
        job_id=job.id,
        actor_admin_id=admin.id,
        step="validate",
        meta={"valid_rows": len(cleaned), "errors": len(val_errors)},
    )
    await log_import_audit(session, job_id=job.id, actor_admin_id=admin.id, step="clean", meta={})
    await log_import_audit(
        session,
        job_id=job.id,
        actor_admin_id=admin.id,
        step="staging",
        meta={"rows": len(cleaned)},
    )
    response.status_code = status.HTTP_201_CREATED
    crm_import_operations_total.labels(endpoint="dry_run", outcome="created").inc()
    return CrmImportDryRunResponse(
        job_id=str(job.id),
        organization_id=str(org_id),
        status=job.status,
        source_profile=job.source_profile,
        rows_validated=len(cleaned),
        message="Строки провалидированы и очищены; готово к commit",
        validation_errors=val_errors,
    )


@router.post("/jobs/{job_id}/commit", response_model=CrmImportCommitResponse)
async def commit_import_job(
    job_id: uuid.UUID,
    org_id: UUID = Depends(get_crm_import_organization_id),
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
) -> CrmImportCommitResponse:
    job = await session.get(CrmImportStagingJob, job_id)
    if job is None or job.organization_id != org_id:
        crm_import_operations_total.labels(endpoint="commit", outcome="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "crm_import_job_not_found", "message": "Задача импорта не найдена"},
        )
    if job.status != "staged":
        crm_import_operations_total.labels(endpoint="commit", outcome="invalid_state").inc()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "crm_import_job_not_staged",
                "message": "Commit доступен только для задач в статусе staged",
            },
        )

    clinic = await session.get(Clinic, admin.clinic_id)
    if clinic is None or clinic.organization_id != org_id:
        crm_import_operations_total.labels(endpoint="commit", outcome="clinic_org_mismatch").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "crm_import_clinic_org_mismatch",
                "message": "Клиника администратора не принадлежит организации импорта.",
            },
        )

    try:
        n, ids = await commit_crm_import_job(
            session,
            job=job,
            clinic_id=admin.clinic_id,
            actor_admin_id=admin.id,
        )
    except ValueError:
        crm_import_operations_total.labels(endpoint="commit", outcome="nothing_to_commit").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "crm_import_nothing_to_commit", "message": "Нет очищенных строк для commit"},
        ) from None

    await session.commit()
    crm_import_operations_total.labels(endpoint="commit", outcome="success").inc()
    return CrmImportCommitResponse(
        job_id=str(job.id),
        committed_count=n,
        lead_ids=[str(i) for i in ids],
    )


@router.get("/jobs", response_model=list[CrmImportJobListItem])
async def list_import_jobs(
    org_id: UUID = Depends(get_crm_import_organization_id),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
) -> list[CrmImportJobListItem]:
    res = await session.execute(
        select(CrmImportStagingJob)
        .where(CrmImportStagingJob.organization_id == org_id)
        .order_by(CrmImportStagingJob.created_at.desc())
        .limit(limit)
    )
    out: list[CrmImportJobListItem] = []
    for row in res.scalars():
        out.append(
            CrmImportJobListItem(
                job_id=str(row.id),
                status=row.status,
                source_profile=row.source_profile,
                created_at=row.created_at.isoformat(),
            )
        )
    crm_import_operations_total.labels(endpoint="list_jobs", outcome="success").inc()
    return out
