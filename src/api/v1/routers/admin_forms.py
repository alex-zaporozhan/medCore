"""Admin API for managing digital form templates and viewing submissions."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.application.dto.forms_dto import (
    DigitalFormSubmissionListItem,
    DigitalFormSubmissionRead,
    DigitalFormSubmissionWithTemplateAndSignature,
    DigitalFormTemplateCreate,
    DigitalFormTemplateRead,
    DigitalFormTemplateUpdate,
    ESignatureRead,
    SendLinkRequest,
    SendLinkResponse,
)
from src.application.services.forms_service import (
    FormValidationError,
    FormsService,
    SubmitFormInput,
)
from src.core.config import settings
from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.digital_form_submission import DigitalFormSubmission
from src.domain.entities.e_signature import ESignature


logger = logging.getLogger(__name__)

def _form_link_base_url() -> str:
    """Base URL for form fill page (send-link). Prefer form_link_base_url, else first CORS origin."""
    base = (settings.form_link_base_url or "").strip()
    if base:
        return base.rstrip("/")
    origins = getattr(settings, "cors_origins_list", []) or []
    if origins:
        return origins[0].rstrip("/")
    return "http://localhost:5173"

router = APIRouter(
    prefix="/admin/forms",
    tags=["admin-forms"],
    dependencies=[Depends(require_permissions("view_forms"))],
)


@router.get(
    "/export",
)
async def export_forms(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("export_forms")),
) -> dict:
    """Export forms and signatures for patient within clinic.

    Sensitive fields in submission data are masked (***). Audit: who/when/what is logged.
    Response is JSON; client may convert to PDF/ZIP.
    """
    logger.info(
        "forms_export",
        extra={
            "clinic_id": str(admin.clinic_id),
            "patient_id": str(patient_id),
            "admin_user_id": str(admin.user_id) if getattr(admin, "user_id", None) else None,
        },
    )
    submissions_stmt = select(DigitalFormSubmission).where(
        DigitalFormSubmission.clinic_id == admin.clinic_id,
        DigitalFormSubmission.patient_id == patient_id,
    ).order_by(DigitalFormSubmission.submitted_at.asc())
    submissions_result = await session.execute(submissions_stmt)
    submissions = list(submissions_result.scalars().all())

    submission_ids = [s.id for s in submissions]
    signatures: list[ESignature] = []
    if submission_ids:
        sig_stmt = select(ESignature).where(
            ESignature.clinic_id == admin.clinic_id,
            ESignature.digital_form_submission_id.in_(submission_ids),
        )
        sig_result = await session.execute(sig_stmt)
        signatures = list(sig_result.scalars().all())

    templates_ids = {s.template_id for s in submissions}
    templates: list[DigitalFormTemplate] = []
    templates_by_id: dict[UUID, DigitalFormTemplate] = {}
    if templates_ids:
        tmpl_stmt = select(DigitalFormTemplate).where(
            DigitalFormTemplate.id.in_(list(templates_ids)),
        )
        tmpl_result = await session.execute(tmpl_stmt)
        templates = list(tmpl_result.scalars().all())
        templates_by_id = {t.id: t for t in templates}

    submissions_dump = []
    for s in submissions:
        t = templates_by_id.get(s.template_id)
        masked_data = FormsService.mask_sensitive_data(s.data, t.schema if t else {})
        submissions_dump.append(
            DigitalFormSubmissionRead(
                id=s.id,
                clinic_id=s.clinic_id,
                template_id=s.template_id,
                patient_id=s.patient_id,
                booking_id=s.booking_id,
                submitted_at=s.submitted_at,
                submitted_by=s.submitted_by,
                data=masked_data,
                signature_id=s.signature_id,
            ).model_dump()
        )

    return {
        "clinic_id": str(admin.clinic_id),
        "patient_id": str(patient_id),
        "templates": [DigitalFormTemplateRead.model_validate(t).model_dump() for t in templates],
        "submissions": submissions_dump,
        "signatures": [ESignatureRead.model_validate(s).model_dump() for s in signatures],
    }


@router.post(
    "/send-link",
    response_model=SendLinkResponse,
    dependencies=[Depends(require_permissions("manage_forms"))],
)
async def send_form_link(
    body: SendLinkRequest,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("manage_forms")),
) -> SendLinkResponse:
    """Generate a one-time form fill URL and optionally send via WhatsApp/SMS.

    At least one of patient_id or booking_id is required. If send_via is whatsapp/sms
    and the channel is not configured, returns url with sent=false (stub).
    """
    if not body.patient_id and not body.booking_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of patient_id or booking_id is required",
        )

    service = FormsService(session)
    try:
        token_str = await service.create_form_link(
            clinic_id=admin.clinic_id,
            template_id=body.template_id,
            patient_id=body.patient_id,
            booking_id=body.booking_id,
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Form template not found or not active",
        ) from e

    await session.commit()

    base_url = _form_link_base_url()
    url = f"{base_url}/forms/fill?token={token_str}"

    sent = False
    channel: str | None = None
    if body.send_via in ("whatsapp", "sms"):
        channel = body.send_via
        # Stub: no actual outbound integration here; when channel is implemented, call it and set sent=True
        logger.info(
            "form_send_link_stub",
            extra={
                "clinic_id": str(admin.clinic_id),
                "template_id": str(body.template_id),
                "send_via": body.send_via,
                "url_returned": "yes",
            },
        )

    return SendLinkResponse(url=url, sent=sent, channel=channel)


@router.get(
    "/templates",
    response_model=list[DigitalFormTemplateRead],
)
async def list_form_templates(
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_forms")),
) -> list[DigitalFormTemplateRead]:
    """List templates for current clinic."""
    stmt = (
        select(DigitalFormTemplate)
        .where(DigitalFormTemplate.clinic_id == admin.clinic_id)
        .order_by(DigitalFormTemplate.code, DigitalFormTemplate.version.desc())
    )
    result = await session.execute(stmt)
    templates = list(result.scalars().all())
    return [DigitalFormTemplateRead.model_validate(t) for t in templates]


@router.post(
    "/templates",
    response_model=DigitalFormTemplateRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_forms"))],
)
async def create_form_template(
    body: DigitalFormTemplateCreate,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("manage_forms")),
) -> DigitalFormTemplateRead:
    """Create new template version for clinic (auto-increment version per code)."""
    stmt = select(DigitalFormTemplate).where(
        DigitalFormTemplate.clinic_id == admin.clinic_id,
        DigitalFormTemplate.code == body.code,
    )
    result = await session.execute(stmt)
    existing = list(result.scalars().all())
    next_version = 1
    if existing:
        next_version = max(t.version for t in existing) + 1

    template = DigitalFormTemplate(
        clinic_id=admin.clinic_id,
        code=body.code,
        name=body.name,
        description=body.description,
        version=next_version,
        schema=body.schema.model_dump(),
        requires_signature=body.requires_signature,
        active=body.active,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return DigitalFormTemplateRead.model_validate(template)


@router.patch(
    "/templates/{template_id}",
    response_model=DigitalFormTemplateRead,
    dependencies=[Depends(require_permissions("manage_forms"))],
)
async def update_form_template(
    template_id: UUID,
    body: DigitalFormTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("manage_forms")),
) -> DigitalFormTemplateRead:
    """Update selected template fields (no version bump, for minor corrections)."""
    template = await session.get(DigitalFormTemplate, template_id)
    if not template or template.clinic_id != admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found")

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.schema is not None:
        template.schema = body.schema.model_dump()
    if body.requires_signature is not None:
        template.requires_signature = body.requires_signature
    if body.active is not None:
        template.active = body.active

    await session.commit()
    await session.refresh(template)
    return DigitalFormTemplateRead.model_validate(template)


@router.get(
    "/submissions",
    response_model=list[DigitalFormSubmissionListItem],
)
async def list_form_submissions(
    patient_id: UUID | None = Query(None),
    booking_id: UUID | None = Query(None),
    template_code: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_forms")),
) -> list[DigitalFormSubmissionListItem]:
    """List form submissions filtered by patient, booking or template code."""
    stmt = select(DigitalFormSubmission).where(DigitalFormSubmission.clinic_id == admin.clinic_id)
    if patient_id is not None:
        stmt = stmt.where(DigitalFormSubmission.patient_id == patient_id)
    if booking_id is not None:
        stmt = stmt.where(DigitalFormSubmission.booking_id == booking_id)
    if template_code is not None:
        tmpl_ids_stmt = select(DigitalFormTemplate.id).where(
            DigitalFormTemplate.clinic_id == admin.clinic_id,
            DigitalFormTemplate.code == template_code,
        )
        tmpl_ids_result = await session.execute(tmpl_ids_stmt)
        template_ids = [row[0] for row in tmpl_ids_result.all()]
        if template_ids:
            stmt = stmt.where(DigitalFormSubmission.template_id.in_(template_ids))
        else:
            return []

    stmt = stmt.order_by(DigitalFormSubmission.submitted_at.desc())
    result = await session.execute(stmt)
    submissions = list(result.scalars().all())
    if not submissions:
        return []

    template_ids = list({s.template_id for s in submissions})
    tmpl_stmt = select(DigitalFormTemplate).where(DigitalFormTemplate.id.in_(template_ids))
    tmpl_result = await session.execute(tmpl_stmt)
    templates_by_id = {t.id: t for t in tmpl_result.scalars().all()}

    out: list[DigitalFormSubmissionListItem] = []
    for s in submissions:
        t = templates_by_id.get(s.template_id)
        out.append(
            DigitalFormSubmissionListItem(
                **DigitalFormSubmissionRead.model_validate(s).model_dump(),
                template_code=t.code if t else "",
                template_name=t.name if t else "",
            )
        )
    return out


@router.get(
    "/submissions/{submission_id}",
    response_model=DigitalFormSubmissionWithTemplateAndSignature,
)
async def get_form_submission_details(
    submission_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("view_forms")),
) -> DigitalFormSubmissionWithTemplateAndSignature:
    """Get submission with linked template and signature (if exists)."""
    submission = await session.get(DigitalFormSubmission, submission_id)
    if not submission or submission.clinic_id != admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form submission not found")

    template = await session.get(DigitalFormTemplate, submission.template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Template is missing")

    signature: ESignature | None = None
    if submission.signature_id is not None:
        signature = await session.get(ESignature, submission.signature_id)

    masked_data = FormsService.mask_sensitive_data(submission.data, template.schema)
    submission_read = DigitalFormSubmissionRead(
        id=submission.id,
        clinic_id=submission.clinic_id,
        template_id=submission.template_id,
        patient_id=submission.patient_id,
        booking_id=submission.booking_id,
        submitted_at=submission.submitted_at,
        submitted_by=submission.submitted_by,
        data=masked_data,
        signature_id=submission.signature_id,
    )

    return DigitalFormSubmissionWithTemplateAndSignature(
        submission=submission_read,
        template=DigitalFormTemplateRead.model_validate(template),
        signature=ESignatureRead.model_validate(signature) if signature else None,
    )


@router.post(
    "/submissions/test-submit",
    response_model=DigitalFormSubmissionRead,
    dependencies=[Depends(require_permissions("manage_forms"))],
)
async def admin_test_submit_form(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    admin: AdminContext = Depends(require_permissions("manage_forms")),
) -> DigitalFormSubmissionRead:
    """Internal/admin endpoint to quickly test template validation and submission.

    Body format:
        {
            "template_code": "...",
            "patient_id": "... or null",
            "booking_id": "... or null",
            "data": {...},
            "signature_payload": {...} | null,
            "signer_name": "...",
            "signer_role": "patient|admin|doctor|legal_representative"
        }
    """
    service = FormsService(session)
    try:
        submission = await service.submit_form(
            SubmitFormInput(
                clinic_id=admin.clinic_id,
                template_code=body.get("template_code"),
                patient_id=UUID(body["patient_id"]) if body.get("patient_id") else None,
                booking_id=UUID(body["booking_id"]) if body.get("booking_id") else None,
                submitted_by="admin",
                data=body.get("data") or {},
                signature_payload=body.get("signature_payload"),
                signer_name=body.get("signer_name"),
                signer_role=body.get("signer_role"),
            )
        )
    except FormValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors,
        ) from e

    await session.commit()
    await session.refresh(submission)
    return DigitalFormSubmissionRead.model_validate(submission)

