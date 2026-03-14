"""Patient API for viewing and submitting pending digital forms."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_session
from src.application.dto.forms_dto import DigitalFormSubmissionRead, DigitalFormTemplateRead
from src.application.services.forms_service import FormValidationError, FormsService, SubmitFormInput
from src.domain.entities.patient import Patient


router = APIRouter(
    prefix="/patient/forms",
    tags=["patient-forms"],
)


@router.get(
    "/pending",
    response_model=list[DigitalFormTemplateRead],
)
async def list_pending_forms(
    session: AsyncSession = Depends(get_session),
    current_patient: Patient = Depends(get_current_patient),
    booking_id: UUID | None = Query(None, description="Optional booking to link forms to visit"),
) -> list[DigitalFormTemplateRead]:
    """Return list of templates that patient must fill before visit (not yet submitted).

    Only active templates (latest version per code) without existing submission for this
    patient are returned. When booking_id is provided, submissions can be linked to that visit.
    """
    service = FormsService(session)
    templates = await service.get_pending_templates(
        clinic_id=current_patient.clinic_id,
        patient_id=current_patient.id,
        booking_id=booking_id,
    )
    return [DigitalFormTemplateRead.model_validate(t) for t in templates]


@router.post(
    "/{template_code}/submit",
    response_model=DigitalFormSubmissionRead,
)
async def submit_form(
    template_code: str,
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    current_patient: Patient = Depends(get_current_patient),
) -> DigitalFormSubmissionRead:
    """Submit filled form and optional signature for current patient."""
    service = FormsService(session)
    booking_id_raw = body.get("booking_id")
    try:
        booking_id = UUID(booking_id_raw) if booking_id_raw else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid booking_id") from None

    try:
        submission = await service.submit_form(
            SubmitFormInput(
                clinic_id=current_patient.clinic_id,
                template_code=template_code,
                patient_id=current_patient.id,
                booking_id=booking_id,
                submitted_by="patient",
                data=body.get("data") or {},
                signature_payload=body.get("signature_payload"),
                signer_name=body.get("signer_name"),
                signer_role="patient",
            )
        )
    except FormValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=e.errors,
        ) from e

    await session.commit()
    await session.refresh(submission)
    return DigitalFormSubmissionRead.model_validate(submission)

