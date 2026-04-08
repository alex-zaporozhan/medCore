"""Admin API: patient medical record (visits/diagnoses/files)."""

from __future__ import annotations

import json
import hashlib
import hashlib as _hashlib
import logging
import os
import tempfile
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.clinic_scope import assert_clinic_in_scope
from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.api.v1.industry_gate_dependencies import require_dental_medical_clinic
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.patient_medical_dto import (
    PatientDiagnosisCreate,
    PatientDiagnosisRead,
    PatientMedicalFileRead,
    PatientMedicalVisitCreate,
    PatientMedicalVisitRead,
)
from src.domain.entities.booking import Booking
from src.domain.entities.doctor import Doctor
from src.domain.entities.patient import Patient
from src.domain.entities.patient_diagnosis import PatientDiagnosis
from src.domain.entities.patient_medical_file import PatientMedicalFile
from src.domain.entities.patient_medical_visit import PatientMedicalVisit
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.medical_file_audit_log import MedicalFileAuditLog
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.database import base as db_base
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter
from src.infrastructure.storage.s3_storage import MedicalFilesStorage
from src.core.config import settings
from src.core.metrics import (
    medical_file_download_token_issued_total,
    medical_file_download_security_denials_total,
    medical_download_security_denials_by_admin_total,
    medical_download_streams_started_total,
    medical_download_tokens_issued_total,
    medical_file_stream_bytes_sent_total,
    medical_file_stream_completed_total,
    medical_file_stream_started_total,
)
from src.core.prometheus_labels import admin_bucket_label, clinic_bucket_label
from src.core.request_ip import resolve_client_ip

router = APIRouter(prefix="/admin/clinics", tags=["admin-patient-medical"])

logger = logging.getLogger(__name__)

ALLOWED_MEDICAL_FILE_TYPES: set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _sniff_content_type(prefix: bytes) -> str | None:
    p = prefix or b""
    if p.startswith(b"%PDF-"):
        return "application/pdf"
    if p.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(p) >= 3 and p[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if p.startswith(b"RIFF") and b"WEBP" in p[8:16]:
        return "image/webp"
    return None


def _sanitize_content_disposition_filename(name: str) -> str:
    # Prevent header injection and keep it readable.
    safe = (name or "file").replace("\r", "").replace("\n", "").strip()
    safe = safe.replace('"', "'")
    return safe[:180] or "file"


def _download_token_key(token: str) -> str:
    return f"medical:download_token:{token}"


def _ua_hash(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return _hashlib.sha256(user_agent.encode("utf-8", errors="ignore")).hexdigest()


async def _assert_patient_in_clinic(session: AsyncSession, clinic_id: UUID, patient_id: UUID) -> None:
    res = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")


async def _assert_doctor_in_clinic(session: AsyncSession, clinic_id: UUID, doctor_id: UUID) -> None:
    res = await session.execute(
        select(Doctor).where(
            Doctor.id == doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.deleted_at.is_(None),
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Врач не найден")


async def _assert_booking_in_clinic_patient(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    booking_id: UUID,
) -> None:
    res = await session.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.clinic_id == clinic_id,
            Booking.patient_id == patient_id,
            Booking.deleted_at.is_(None),
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")


async def _assert_visit_in_patient(
    session: AsyncSession,
    clinic_id: UUID,
    patient_id: UUID,
    visit_id: UUID,
) -> None:
    res = await session.execute(
        select(PatientMedicalVisit).where(
            PatientMedicalVisit.id == visit_id,
            PatientMedicalVisit.clinic_id == clinic_id,
            PatientMedicalVisit.patient_id == patient_id,
            PatientMedicalVisit.deleted_at.is_(None),
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Визит не найден")


@router.get(
    "/{clinic_id}/patients/{patient_id}/medical/visits",
    response_model=list[PatientMedicalVisitRead],
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def list_medical_visits(
    clinic_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PatientMedicalVisitRead]:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    res = await session.execute(
        select(PatientMedicalVisit)
        .where(
            PatientMedicalVisit.clinic_id == clinic_id,
            PatientMedicalVisit.patient_id == patient_id,
            PatientMedicalVisit.deleted_at.is_(None),
        )
        .order_by(PatientMedicalVisit.visit_date.desc(), PatientMedicalVisit.created_at.desc())
    )
    return [PatientMedicalVisitRead.model_validate(x) for x in res.scalars().all()]


@router.post(
    "/{clinic_id}/patients/{patient_id}/medical/visits",
    response_model=PatientMedicalVisitRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("patients.medical.write")),
        Depends(require_dental_medical_clinic),
    ],
)
async def create_medical_visit(
    clinic_id: UUID,
    patient_id: UUID,
    data: PatientMedicalVisitCreate,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PatientMedicalVisitRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    if data.doctor_id is not None:
        await _assert_doctor_in_clinic(session, clinic_id, data.doctor_id)
    if data.booking_id is not None:
        await _assert_booking_in_clinic_patient(session, clinic_id, patient_id, data.booking_id)
    row = PatientMedicalVisit(
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=data.doctor_id,
        booking_id=data.booking_id,
        visit_date=data.visit_date,
        notes_md=data.notes_md,
        created_by_admin_id=current_admin.id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return PatientMedicalVisitRead.model_validate(row)


@router.get(
    "/{clinic_id}/patients/{patient_id}/medical/diagnoses",
    response_model=list[PatientDiagnosisRead],
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def list_diagnoses(
    clinic_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PatientDiagnosisRead]:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    res = await session.execute(
        select(PatientDiagnosis)
        .where(
            PatientDiagnosis.clinic_id == clinic_id,
            PatientDiagnosis.patient_id == patient_id,
            PatientDiagnosis.deleted_at.is_(None),
        )
        .order_by(PatientDiagnosis.diagnosis_date.desc(), PatientDiagnosis.created_at.desc())
    )
    return [PatientDiagnosisRead.model_validate(x) for x in res.scalars().all()]


@router.post(
    "/{clinic_id}/patients/{patient_id}/medical/diagnoses",
    response_model=PatientDiagnosisRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("patients.medical.write")),
        Depends(require_dental_medical_clinic),
    ],
)
async def create_diagnosis(
    clinic_id: UUID,
    patient_id: UUID,
    data: PatientDiagnosisCreate,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PatientDiagnosisRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    if data.visit_id is not None:
        await _assert_visit_in_patient(session, clinic_id, patient_id, data.visit_id)
    row = PatientDiagnosis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        visit_id=data.visit_id,
        diagnosis_date=data.diagnosis_date,
        icd10_code=data.icd10_code,
        title=data.title,
        description=data.description,
        author_admin_id=current_admin.id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return PatientDiagnosisRead.model_validate(row)


@router.get(
    "/{clinic_id}/patients/{patient_id}/medical/files",
    response_model=list[PatientMedicalFileRead],
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def list_medical_files(
    clinic_id: UUID,
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[PatientMedicalFileRead]:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    res = await session.execute(
        select(PatientMedicalFile)
        .where(
            PatientMedicalFile.clinic_id == clinic_id,
            PatientMedicalFile.patient_id == patient_id,
            PatientMedicalFile.deleted_at.is_(None),
        )
        .order_by(PatientMedicalFile.created_at.desc())
    )
    return [PatientMedicalFileRead.model_validate(x) for x in res.scalars().all()]


@router.post(
    "/{clinic_id}/patients/{patient_id}/medical/files:upload",
    response_model=PatientMedicalFileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("patients.medical.write")),
        Depends(require_dental_medical_clinic),
    ],
)
async def upload_medical_file(
    clinic_id: UUID,
    patient_id: UUID,
    file: UploadFile = File(...),
    visit_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> PatientMedicalFileRead:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    if visit_id is not None:
        await _assert_visit_in_patient(session, clinic_id, patient_id, visit_id)

    file_id = uuid4()
    storage = MedicalFilesStorage()
    key = storage.build_key(
        clinic_id=str(clinic_id),
        patient_id=str(patient_id),
        file_id=str(file_id),
        filename=file.filename,
    )

    # Stream upload: avoid loading entire file into memory.
    hasher = hashlib.sha256()
    size = 0
    prefix = b""
    max_bytes = 50 * 1024 * 1024

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = tmp.name
    try:
        # Read first bytes to sniff type.
        first = await file.read(32)
        if not first:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")
        prefix = first
        ct_sniffed = _sniff_content_type(prefix)
        if not ct_sniffed or ct_sniffed not in ALLOWED_MEDICAL_FILE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый тип файла")

        hasher.update(first)
        tmp.write(first)
        size += len(first)
        if size > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")

        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
            hasher.update(chunk)
            tmp.write(chunk)

        tmp.flush()
        tmp.seek(0)

        try:
            storage.put_fileobj(key=key, fileobj=tmp, content_type=ct_sniffed)
        except RuntimeError as e:
            if str(e) == "s3_not_configured":
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Хранилище не настроено") from e
            raise
    finally:
        try:
            await file.close()
        except Exception:
            pass
        try:
            tmp.close()
        except Exception:
            pass
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    sha = hasher.hexdigest()
    logger.info(
        "medical_file_uploaded",
        extra={
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id),
            "file_id": str(file_id),
            "size_bytes": size,
            "content_type": ct_sniffed,
            "admin_id": str(current_admin.id),
        },
    )
    row = PatientMedicalFile(
        id=file_id,
        clinic_id=clinic_id,
        patient_id=patient_id,
        visit_id=visit_id,
        s3_key=key,
        file_name=(file.filename or "file").strip()[:255],
        content_type=ct_sniffed[:120],
        size_bytes=size,
        sha256=sha,
        uploaded_by_admin_id=current_admin.id,
    )
    session.add(row)
    await session.flush()
    session.add(
        MedicalFileAuditLog(
            clinic_id=clinic_id,
            patient_id=patient_id,
            file_id=file_id,
            actor_admin_id=current_admin.id,
            action="upload",
            meta={
                "size_bytes": size,
                "content_type": ct_sniffed,
                "sha256": sha,
                "visit_id": str(visit_id) if visit_id else None,
            },
            ip_address=None,
            user_agent=None,
        )
    )
    await session.refresh(row)
    return PatientMedicalFileRead.model_validate(row)


@router.get(
    "/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download",
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def download_medical_file(
    clinic_id: UUID,
    patient_id: UUID,
    file_id: UUID,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    # Deprecated: enterprise режим не выдаёт прямые ссылки на storage.
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Используйте :download-token и :stream")


@router.post(
    "/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download-token",
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def issue_medical_file_download_token(
    clinic_id: UUID,
    patient_id: UUID,
    file_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)
    res = await session.execute(
        select(PatientMedicalFile).where(
            PatientMedicalFile.id == file_id,
            PatientMedicalFile.clinic_id == clinic_id,
            PatientMedicalFile.patient_id == patient_id,
            PatientMedicalFile.deleted_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")

    try:
        await limiter.check_or_raise(
            key=f"rl:admin:{current_admin.id}:medical_download_token",
            limit=30,
            window=60,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded (limit={e.limit}, window={e.window})",
        ) from e

    token = str(uuid4())
    ttl = int(settings.medical_download_token_ttl_seconds or 120)
    client_ip = resolve_client_ip(
        request,
        trusted_proxy_cidrs=settings.medical_trusted_proxy_cidrs,
        allow_forwarded=bool(settings.medical_resolve_client_ip_from_forwarded),
    )
    payload = {
        "admin_id": str(current_admin.id),
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "file_id": str(file_id),
        "trace_id": getattr(ctx, "trace_id", None),
        "ip": client_ip,
        "ua_hash": _ua_hash(request.headers.get("user-agent")),
    }
    try:
        redis = await get_redis()
        await redis.setex(_download_token_key(token), ttl, json.dumps(payload))
    except Exception as e:  # noqa: BLE001
        # Fail-close: PHI download without token storage is forbidden.
        medical_file_download_token_issued_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            result="redis_unavailable",
        ).inc()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Token storage unavailable") from e

    logger.info(
        "medical_file_download_token_issued",
        extra={
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id),
            "file_id": str(file_id),
            "admin_id": str(current_admin.id),
        },
    )
    medical_file_download_token_issued_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        result="ok",
    ).inc()
    medical_download_tokens_issued_total.labels(
        admin_bucket=admin_bucket_label(current_admin.id),
    ).inc()
    session.add(
        MedicalFileAuditLog(
            clinic_id=clinic_id,
            patient_id=patient_id,
            file_id=file_id,
            actor_admin_id=current_admin.id,
            action="download_token_issued",
            meta={"expires_in_seconds": ttl},
            ip_address=getattr(request.client, "host", None),
            user_agent=request.headers.get("user-agent"),
        )
    )
    await session.flush()
    return {"token": token, "expires_in_seconds": ttl}


@router.get(
    "/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:stream",
    dependencies=[
        Depends(require_permissions("patients.medical.read")),
        Depends(require_dental_medical_clinic),
    ],
)
async def stream_medical_file(
    clinic_id: UUID,
    patient_id: UUID,
    file_id: UUID,
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    ctx: AdminContext = Depends(get_request_context),
    current_admin: AdminUser = Depends(get_current_admin),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    await assert_clinic_in_scope(session, current_admin, clinic_id)
    await _assert_patient_in_clinic(session, clinic_id, patient_id)

    # Consume token (one-time).
    try:
        redis = await get_redis()
        key = _download_token_key(token)
        raw: str | None
        try:
            raw = await redis.execute_command("GETDEL", key)
        except Exception:
            raw = await redis.get(key)
            if raw:
                await redis.delete(key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Token storage unavailable") from e

    if not raw:
        medical_file_download_security_denials_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            reason="token_missing",
        ).inc()
        medical_download_security_denials_by_admin_total.labels(
            admin_bucket=admin_bucket_label(current_admin.id),
            reason="token_missing",
        ).inc()
        logger.warning(
            "medical_download_token_validation_failed",
            extra={
                "reason": "token_missing",
                "clinic_id": str(clinic_id),
                "patient_id": str(patient_id),
                "file_id": str(file_id),
                "admin_id": str(current_admin.id),
                "trace_id": getattr(ctx, "trace_id", None),
            },
        )
        medical_file_stream_started_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            result="token_missing",
        ).inc()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired or already used")
    try:
        payload = json.loads(raw)
    except Exception:
        medical_file_download_security_denials_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            reason="token_invalid",
        ).inc()
        medical_download_security_denials_by_admin_total.labels(
            admin_bucket=admin_bucket_label(current_admin.id),
            reason="token_invalid",
        ).inc()
        logger.warning(
            "medical_download_token_validation_failed",
            extra={
                "reason": "token_invalid",
                "clinic_id": str(clinic_id),
                "patient_id": str(patient_id),
                "file_id": str(file_id),
                "admin_id": str(current_admin.id),
                "trace_id": getattr(ctx, "trace_id", None),
            },
        )
        medical_file_stream_started_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            result="token_invalid",
        ).inc()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invalid token") from None
    if (
        payload.get("admin_id") != str(current_admin.id)
        or payload.get("clinic_id") != str(clinic_id)
        or payload.get("patient_id") != str(patient_id)
        or payload.get("file_id") != str(file_id)
    ):
        medical_file_download_security_denials_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            reason="token_mismatch",
        ).inc()
        medical_download_security_denials_by_admin_total.labels(
            admin_bucket=admin_bucket_label(current_admin.id),
            reason="token_mismatch",
        ).inc()
        logger.warning(
            "medical_download_token_validation_failed",
            extra={
                "reason": "token_mismatch",
                "clinic_id": str(clinic_id),
                "patient_id": str(patient_id),
                "file_id": str(file_id),
                "admin_id": str(current_admin.id),
                "trace_id": getattr(ctx, "trace_id", None),
            },
        )
        medical_file_stream_started_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            result="token_mismatch",
        ).inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Enterprise binding: UA (default on) + optional IP enforcement (tolerant under proxies by default).
    if settings.medical_download_token_bind_ua:
        if payload.get("ua_hash") != _ua_hash(request.headers.get("user-agent")):
            medical_file_download_security_denials_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                reason="ua_mismatch",
            ).inc()
            medical_download_security_denials_by_admin_total.labels(
                admin_bucket=admin_bucket_label(current_admin.id),
                reason="ua_mismatch",
            ).inc()
            logger.warning(
                "medical_download_token_validation_failed",
                extra={
                    "reason": "ua_mismatch",
                    "clinic_id": str(clinic_id),
                    "patient_id": str(patient_id),
                    "file_id": str(file_id),
                    "admin_id": str(current_admin.id),
                    "trace_id": getattr(ctx, "trace_id", None),
                },
            )
            medical_file_stream_started_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                result="ua_mismatch",
            ).inc()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if settings.medical_download_token_enforce_ip:
        client_ip = resolve_client_ip(
            request,
            trusted_proxy_cidrs=settings.medical_trusted_proxy_cidrs,
            allow_forwarded=bool(settings.medical_resolve_client_ip_from_forwarded),
        )
        if payload.get("ip") and payload.get("ip") != client_ip:
            medical_file_download_security_denials_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                reason="ip_mismatch",
            ).inc()
            medical_download_security_denials_by_admin_total.labels(
                admin_bucket=admin_bucket_label(current_admin.id),
                reason="ip_mismatch",
            ).inc()
            logger.warning(
                "medical_download_token_validation_failed",
                extra={
                    "reason": "ip_mismatch",
                    "clinic_id": str(clinic_id),
                    "patient_id": str(patient_id),
                    "file_id": str(file_id),
                    "admin_id": str(current_admin.id),
                    "trace_id": getattr(ctx, "trace_id", None),
                },
            )
            medical_file_stream_started_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                result="ip_mismatch",
            ).inc()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        await limiter.check_or_raise(
            key=f"rl:admin:{current_admin.id}:medical_download_stream",
            limit=60,
            window=60,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded (limit={e.limit}, window={e.window})",
        ) from e

    res = await session.execute(
        select(PatientMedicalFile).where(
            PatientMedicalFile.id == file_id,
            PatientMedicalFile.clinic_id == clinic_id,
            PatientMedicalFile.patient_id == patient_id,
            PatientMedicalFile.deleted_at.is_(None),
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")

    storage = MedicalFilesStorage()
    range_header = request.headers.get("range")
    try:
        obj = storage.get_object_stream(key=row.s3_key, range_header=range_header)
    except RuntimeError as e:
        if str(e) == "s3_not_configured":
            medical_file_stream_started_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                result="s3_not_configured",
            ).inc()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Хранилище не настроено") from e
        raise

    filename = _sanitize_content_disposition_filename(row.file_name)
    headers: dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
    }
    if obj.content_range:
        headers["Content-Range"] = obj.content_range

    status_code = 206 if obj.content_range else 200

    logger.info(
        "medical_file_stream_started",
        extra={
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id),
            "file_id": str(file_id),
            "admin_id": str(current_admin.id),
            "range": range_header,
            "trace_id": getattr(ctx, "trace_id", None),
        },
    )
    medical_file_stream_started_total.labels(
        clinic_bucket=clinic_bucket_label(clinic_id),
        result="ok",
    ).inc()
    medical_download_streams_started_total.labels(
        admin_bucket=admin_bucket_label(current_admin.id),
    ).inc()
    session.add(
        MedicalFileAuditLog(
            clinic_id=clinic_id,
            patient_id=patient_id,
            file_id=file_id,
            actor_admin_id=current_admin.id,
            action="download_stream_started",
            meta={"range": range_header},
            ip_address=getattr(request.client, "host", None),
            user_agent=request.headers.get("user-agent"),
        )
    )
    await session.flush()

    stream_stats: dict[str, int] = {"bytes_sent": 0, "failed": 0}

    def _iter_chunks():
        # botocore StreamingBody yields bytes via iter_chunks
        body = obj.body
        try:
            it = getattr(body, "iter_chunks", None)
            if callable(it):
                for chunk in it(chunk_size=1024 * 1024):
                    if chunk:
                        stream_stats["bytes_sent"] += len(chunk)
                        yield chunk
                return
            while True:
                b = body.read(1024 * 1024)
                if not b:
                    break
                stream_stats["bytes_sent"] += len(b)
                yield b
        except Exception:  # noqa: BLE001
            stream_stats["failed"] = 1
            raise

    async def _audit_stream_done() -> None:
        bytes_sent = int(stream_stats.get("bytes_sent", 0))
        failed = bool(stream_stats.get("failed", 0))
        try:
            if bytes_sent > 0:
                medical_file_stream_bytes_sent_total.labels(
                    clinic_bucket=clinic_bucket_label(clinic_id),
                ).inc(bytes_sent)
            medical_file_stream_completed_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id),
                result="failed" if failed else "ok",
            ).inc()
        except Exception:
            pass

        # DB audit event after streaming completed.
        try:
            async with db_base.AsyncSessionLocal() as audit_sess:
                audit_sess.add(
                    MedicalFileAuditLog(
                        clinic_id=clinic_id,
                        patient_id=patient_id,
                        file_id=file_id,
                        actor_admin_id=current_admin.id,
                        action="download_failed" if failed else "download_stream_completed",
                        meta={"range": range_header, "bytes_sent": bytes_sent, "status_code": status_code},
                        ip_address=getattr(request.client, "host", None),
                        user_agent=request.headers.get("user-agent"),
                    )
                )
                await audit_sess.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("medical_file_stream_audit_failed", extra={"error": str(exc)})

    return StreamingResponse(
        _iter_chunks(),
        status_code=status_code,
        media_type=row.content_type or obj.content_type,
        headers=headers,
        background=_audit_stream_done,
    )

