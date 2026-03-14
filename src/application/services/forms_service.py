"""Forms service for DigitalFormTemplate and DigitalFormSubmission flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.digital_form_submission import DigitalFormSubmission
from src.domain.entities.e_signature import ESignature


class FormValidationError(Exception):
    """Raised when form data does not conform to template schema."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("Form validation failed")
        self.errors = errors


@dataclass
class SubmitFormInput:
    """Input data for submitting a digital form."""

    clinic_id: UUID
    template_code: str
    patient_id: UUID | None
    booking_id: UUID | None
    submitted_by: str  # patient|admin|doctor
    data: dict[str, Any]
    signature_payload: dict[str, Any] | None
    signer_name: str | None
    signer_role: str | None


class FormsService:
    """Service encapsulating operations on digital forms and signatures."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_pending_templates(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        booking_id: UUID | None = None,
    ) -> list[DigitalFormTemplate]:
        """Return active templates (latest version per code) that patient has not yet submitted.

        Pending = no DigitalFormSubmission for this patient for this template (current version).
        If booking_id is given, still returns same pending list; submission can be linked to
        booking when submitting.
        """
        # Active templates, latest version per code
        stmt = (
            select(DigitalFormTemplate)
            .where(
                DigitalFormTemplate.clinic_id == clinic_id,
                DigitalFormTemplate.active.is_(True),
            )
            .order_by(DigitalFormTemplate.code, DigitalFormTemplate.version.desc())
        )
        result = await self.session.execute(stmt)
        all_active = list(result.scalars().all())
        # Dedupe by code (keep first = latest version)
        seen_codes: set[str] = set()
        latest_templates: list[DigitalFormTemplate] = []
        for t in all_active:
            if t.code not in seen_codes:
                seen_codes.add(t.code)
                latest_templates.append(t)

        if not latest_templates:
            return []

        template_ids = [t.id for t in latest_templates]
        # Submissions for this patient and these templates
        submission_stmt = select(DigitalFormSubmission.template_id).where(
            DigitalFormSubmission.clinic_id == clinic_id,
            DigitalFormSubmission.patient_id == patient_id,
            DigitalFormSubmission.template_id.in_(template_ids),
        )
        if booking_id is not None:
            submission_stmt = submission_stmt.where(
                (DigitalFormSubmission.booking_id == booking_id)
                | (DigitalFormSubmission.booking_id.is_(None)),
            )
        sub_result = await self.session.execute(submission_stmt)
        submitted_template_ids = {row[0] for row in sub_result.all()}

        return [t for t in latest_templates if t.id not in submitted_template_ids]

    async def _get_active_template_by_code(
        self,
        clinic_id: UUID,
        template_code: str,
    ) -> DigitalFormTemplate | None:
        stmt = select(DigitalFormTemplate).where(
            DigitalFormTemplate.clinic_id == clinic_id,
            DigitalFormTemplate.code == template_code,
            DigitalFormTemplate.active.is_(True),
        ).order_by(DigitalFormTemplate.version.desc())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _validate_data_against_schema(
        self,
        schema: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        """Minimal JSON-like validation based on fields description in schema.

        Expected schema format (Phase 1, minimal):
            {
                "fields": [
                    {
                        "id": "full_name",
                        "label": "...",
                        "type": "text" | "textarea" | "number" | "select" | "checkbox" | "date",
                        "required": true/false,
                        "options": [...],  # for select/checkbox groups
                        "sensitive": true/false,
                    },
                    ...
                ]
            }
        """
        fields = schema.get("fields") or []
        errors: list[dict[str, Any]] = []

        if not isinstance(data, dict):
            raise FormValidationError(
                [{"field": "__root__", "message": "data must be an object"}]
            )

        for field in fields:
            field_id = field.get("id")
            field_type = field.get("type")
            required = bool(field.get("required"))
            options = field.get("options") or []

            if not field_id or not field_type:
                continue

            present = field_id in data and data[field_id] is not None
            value = data.get(field_id)

            if required and not present:
                errors.append(
                    {"field": field_id, "message": "Field is required"},
                )
                continue

            if not present:
                continue

            if field_type in {"text", "textarea", "date"}:
                if not isinstance(value, str):
                    errors.append(
                        {
                            "field": field_id,
                            "message": f"Expected string for type {field_type}",
                        }
                    )
            elif field_type == "number":
                if not isinstance(value, (int, float)):
                    errors.append(
                        {
                            "field": field_id,
                            "message": "Expected number",
                        }
                    )
            elif field_type == "select":
                if not isinstance(value, str):
                    errors.append(
                        {
                            "field": field_id,
                            "message": "Expected string for select",
                        }
                    )
                elif options and value not in options:
                    errors.append(
                        {
                            "field": field_id,
                            "message": "Value is not in allowed options",
                        }
                    )
            elif field_type == "checkbox":
                # Support both single boolean and list of options.
                if isinstance(value, bool):
                    # no extra validation
                    pass
                elif isinstance(value, list):
                    invalid = [
                        v for v in value if not isinstance(v, str) or (options and v not in options)
                    ]
                    if invalid:
                        errors.append(
                            {
                                "field": field_id,
                                "message": "Some checkbox values are invalid",
                            }
                        )
                else:
                    errors.append(
                        {
                            "field": field_id,
                            "message": "Expected boolean or list for checkbox",
                        }
                    )

        if errors:
            raise FormValidationError(errors)

    @staticmethod
    def mask_sensitive_data(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Return copy of data with sensitive fields (schema.fields[].sensitive) masked as ***."""
        if not data or not schema:
            return dict(data) if data else {}
        fields = schema.get("fields") or []
        sensitive_ids = {f["id"] for f in fields if f.get("id") and f.get("sensitive")}
        out = dict(data)
        for fid in sensitive_ids:
            if fid in out and out[fid] is not None:
                out[fid] = "***"
        return out

    async def submit_form(self, data: SubmitFormInput) -> DigitalFormSubmission:
        """Validate and submit a form, optionally creating an electronic signature.

        Flow:
        - load active template by clinic_id + template_code;
        - validate provided data against template.schema;
        - create DigitalFormSubmission;
        - if template.requires_signature or signature_payload is provided -> create ESignature
          and link it to submission.
        """
        template = await self._get_active_template_by_code(
            clinic_id=data.clinic_id,
            template_code=data.template_code,
        )
        if template is None:
            raise LookupError("Active form template not found")

        self._validate_data_against_schema(template.schema, data.data)

        submission = DigitalFormSubmission(
            clinic_id=data.clinic_id,
            template_id=template.id,
            patient_id=data.patient_id,
            booking_id=data.booking_id,
            submitted_by=data.submitted_by,
            data=data.data,
        )
        self.session.add(submission)
        await self.session.flush()

        if template.requires_signature or data.signature_payload is not None:
            if data.signature_payload is None:
                raise ValueError("Signature payload is required for this form")
            signer_role = data.signer_role or data.submitted_by
            signature = ESignature(
                clinic_id=data.clinic_id,
                patient_id=data.patient_id,
                digital_form_submission_id=submission.id,
                signer_name=data.signer_name,
                signer_role=signer_role,
                signature_type=data.signature_payload.get("type", "drawn"),
                signature_payload=data.signature_payload,
                meta=data.signature_payload.get("meta") if isinstance(data.signature_payload, dict) else None,
            )
            self.session.add(signature)
            await self.session.flush()
            submission.signature_id = signature.id

        await self.session.flush()
        return submission

