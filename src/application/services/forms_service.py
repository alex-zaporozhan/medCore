"""Forms service for DigitalFormTemplate and DigitalFormSubmission (Paperless / FormInstance).

filled_data lives in submission.data; do not send raw field values to external AI without
AiSanitizer/tokenization (see ``src/core/ai_sanitizer.py``).
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.form_status_service import FormStatusService
from src.core.prometheus_labels import clinic_bucket_label
from src.core.metrics import (
    paperless_form_issue_to_sign_seconds,
    paperless_form_operations_total,
    paperless_form_status_transitions_total,
)
from src.domain.entities.booking import Booking
from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.digital_form_submission import DigitalFormSubmission
from src.domain.entities.e_signature import ESignature
from src.domain.entities.form_audit_entry import FormAuditEntry
from src.domain.entities.form_link_token import FormLinkToken
from src.domain.entities.form_status import FormStatus

logger = logging.getLogger(__name__)


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
        self._status = FormStatusService()

    async def _audit(
        self,
        submission_id: UUID,
        action: str,
        actor: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        entry = FormAuditEntry(
            digital_form_submission_id=submission_id,
            action=action,
            actor=actor,
            meta=meta,
        )
        self.session.add(entry)
        await self.session.flush()

    def _record_transition_metric(self, clinic_id: UUID, from_s: FormStatus, to_s: FormStatus) -> None:
        paperless_form_status_transitions_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            from_status=from_s.value,
            to_status=to_s.value,
        ).inc()

    def _observe_issue_to_sign_latency(
        self,
        clinic_id: UUID,
        prev: FormStatus,
        submission: DigitalFormSubmission,
        signed_at: datetime,
    ) -> None:
        if prev not in (FormStatus.ISSUED, FormStatus.IN_PROGRESS, FormStatus.UNKNOWN):
            return
        created = submission.created_at
        if created is None:
            return
        delta = (signed_at - created).total_seconds()
        if delta >= 0:
            paperless_form_issue_to_sign_seconds.labels(clinic_bucket=clinic_bucket_label(clinic_id)).observe(delta)

    async def get_pending_templates(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        booking_id: UUID | None = None,
    ) -> list[DigitalFormTemplate]:
        """Active templates (latest per code) without a qualifying signed submission for this patient."""
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
        seen_codes: set[str] = set()
        latest_templates: list[DigitalFormTemplate] = []
        for t in all_active:
            if t.code not in seen_codes:
                seen_codes.add(t.code)
                latest_templates.append(t)

        if not latest_templates:
            return []

        codes_signed_stmt = (
            select(DigitalFormTemplate.code)
            .join(DigitalFormSubmission, DigitalFormSubmission.template_id == DigitalFormTemplate.id)
            .where(
                DigitalFormSubmission.clinic_id == clinic_id,
                DigitalFormSubmission.patient_id == patient_id,
                DigitalFormSubmission.status == FormStatus.SIGNED.value,
            )
        )
        if booking_id is not None:
            codes_signed_stmt = codes_signed_stmt.where(
                or_(
                    DigitalFormSubmission.booking_id == booking_id,
                    DigitalFormSubmission.booking_id.is_(None),
                )
            )
        codes_result = await self.session.execute(codes_signed_stmt.distinct())
        signed_codes = {row[0] for row in codes_result.all()}

        return [t for t in latest_templates if t.code not in signed_codes]

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

    async def _find_open_submission_for_submit(
        self,
        clinic_id: UUID,
        template_id: UUID,
        patient_id: UUID | None,
        booking_id: UUID | None,
    ) -> DigitalFormSubmission | None:
        stmt = (
            select(DigitalFormSubmission)
            .where(
                DigitalFormSubmission.clinic_id == clinic_id,
                DigitalFormSubmission.template_id == template_id,
                DigitalFormSubmission.patient_id == patient_id,
                DigitalFormSubmission.status.in_(
                    (
                        FormStatus.DRAFT.value,
                        FormStatus.ISSUED.value,
                        FormStatus.IN_PROGRESS.value,
                    )
                ),
            )
            .order_by(DigitalFormSubmission.created_at.desc())
        )
        if booking_id is not None:
            stmt = stmt.where(
                or_(
                    DigitalFormSubmission.booking_id == booking_id,
                    DigitalFormSubmission.booking_id.is_(None),
                )
            )
        else:
            stmt = stmt.where(DigitalFormSubmission.booking_id.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _validate_data_against_schema(
        self,
        schema: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
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
                if isinstance(value, bool):
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
        if not data or not schema:
            return dict(data) if data else {}
        fields = schema.get("fields") or []
        sensitive_ids = {f["id"] for f in fields if f.get("id") and f.get("sensitive")}
        out = dict(data)
        for fid in sensitive_ids:
            if fid in out and out[fid] is not None:
                out[fid] = "***"
        return out

    async def mark_expired_submissions(
        self,
        clinic_id: UUID,
        booking_id: UUID | None = None,
    ) -> int:
        """Move issued/in_progress forms past expires_at to expired. Returns count updated."""
        now = datetime.now(timezone.utc)
        stmt = select(DigitalFormSubmission).where(
            DigitalFormSubmission.clinic_id == clinic_id,
            DigitalFormSubmission.status.in_(
                (FormStatus.ISSUED.value, FormStatus.IN_PROGRESS.value)
            ),
            DigitalFormSubmission.expires_at.isnot(None),
            DigitalFormSubmission.expires_at < now,
        )
        if booking_id is not None:
            stmt = stmt.where(DigitalFormSubmission.booking_id == booking_id)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        n = 0
        for sub in rows:
            prev = FormStatus.from_str(sub.status)
            self._status.assert_transition(prev, FormStatus.EXPIRED)
            sub.status = FormStatus.EXPIRED.value
            sub.updated_by = "system"
            n += 1
            self._record_transition_metric(clinic_id, prev, FormStatus.EXPIRED)
            await self._audit(sub.id, "expired", "system", {"from": prev.value})
            paperless_form_operations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), action="expire"
            ).inc()
        if n:
            await self.session.flush()
        return n

    async def _latest_required_template_codes(self, clinic_id: UUID) -> list[str]:
        """Distinct template codes (latest version row per code) with required_for_visit_completion."""
        stmt = (
            select(DigitalFormTemplate)
            .where(
                DigitalFormTemplate.clinic_id == clinic_id,
                DigitalFormTemplate.active.is_(True),
                DigitalFormTemplate.required_for_visit_completion.is_(True),
            )
            .order_by(DigitalFormTemplate.code, DigitalFormTemplate.version.desc())
        )
        result = await self.session.execute(stmt)
        all_req = list(result.scalars().all())
        seen: set[str] = set()
        required_codes: list[str] = []
        for t in all_req:
            if t.code not in seen:
                seen.add(t.code)
                required_codes.append(t.code)
        return required_codes

    async def list_missing_required_signed_template_codes(
        self,
        clinic_id: UUID,
        booking_id: UUID,
    ) -> list[str]:
        """Template codes required for visit completion without a signed submission for this booking."""

        await self.mark_expired_submissions(clinic_id, booking_id)

        booking = await self.session.get(Booking, booking_id)
        if not booking or booking.clinic_id != clinic_id:
            return []

        required_codes = await self._latest_required_template_codes(clinic_id)
        if not required_codes:
            return []

        # Fail-closed: без пациента на записи нельзя подтвердить набор обязательных форм.
        if booking.patient_id is None:
            return list(required_codes)

        missing: list[str] = []
        for code in required_codes:
            signed_exists = await self.session.execute(
                select(DigitalFormSubmission.id)
                .join(DigitalFormTemplate, DigitalFormTemplate.id == DigitalFormSubmission.template_id)
                .where(
                    DigitalFormSubmission.clinic_id == clinic_id,
                    DigitalFormSubmission.booking_id == booking_id,
                    DigitalFormSubmission.patient_id == booking.patient_id,
                    DigitalFormTemplate.code == code,
                    DigitalFormSubmission.status == FormStatus.SIGNED.value,
                )
                .limit(1)
            )
            if signed_exists.scalar_one_or_none() is None:
                missing.append(code)
        return missing

    async def submit_form(self, data: SubmitFormInput) -> DigitalFormSubmission:
        template = await self._get_active_template_by_code(
            clinic_id=data.clinic_id,
            template_code=data.template_code,
        )
        if template is None:
            raise LookupError("Active form template not found")

        self._validate_data_against_schema(template.schema, data.data)

        now = datetime.now(timezone.utc)
        existing = await self._find_open_submission_for_submit(
            data.clinic_id,
            template.id,
            data.patient_id,
            data.booking_id,
        )

        if existing is not None:
            prev = FormStatus.from_str(existing.status)
            self._status.assert_transition(prev, FormStatus.SIGNED)
            existing.status = FormStatus.SIGNED.value
            existing.data = data.data
            existing.submitted_at = now
            existing.signed_at = now
            existing.submitted_by = data.submitted_by
            existing.updated_by = data.submitted_by
            submission = existing
            self._record_transition_metric(data.clinic_id, prev, FormStatus.SIGNED)
            self._observe_issue_to_sign_latency(data.clinic_id, prev, submission, now)
            await self._audit(submission.id, "signed", data.submitted_by, None)
        else:
            submission = DigitalFormSubmission(
                clinic_id=data.clinic_id,
                template_id=template.id,
                patient_id=data.patient_id,
                booking_id=data.booking_id,
                status=FormStatus.SIGNED.value,
                submitted_by=data.submitted_by,
                data=data.data,
                submitted_at=now,
                signed_at=now,
                created_by=data.submitted_by,
                updated_by=data.submitted_by,
            )
            self.session.add(submission)
            await self.session.flush()
            self._record_transition_metric(data.clinic_id, FormStatus.DRAFT, FormStatus.SIGNED)
            await self._audit(submission.id, "signed", data.submitted_by, None)

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

        logger.info(
            "paperless_form_signed",
            extra={
                "form_id": str(submission.id),
                "template_code": template.code,
                "patient_id": str(data.patient_id) if data.patient_id else None,
                "booking_id": str(data.booking_id) if data.booking_id else None,
                "clinic_id": str(data.clinic_id),
            },
        )
        paperless_form_operations_total.labels(
            clinic_bucket=clinic_bucket_label(data.clinic_id), action="sign"
        ).inc()
        return submission

    async def _find_reusable_issued_submission(
        self,
        clinic_id: UUID,
        template_id: UUID,
        patient_id: UUID | None,
        booking_id: UUID | None,
        min_expires_after: datetime,
    ) -> DigitalFormSubmission | None:
        """Reuse non-expired issued/in_progress instance for same template + patient + booking context."""
        stmt = (
            select(DigitalFormSubmission)
            .where(
                DigitalFormSubmission.clinic_id == clinic_id,
                DigitalFormSubmission.template_id == template_id,
                DigitalFormSubmission.status.in_(
                    (FormStatus.ISSUED.value, FormStatus.IN_PROGRESS.value)
                ),
                DigitalFormSubmission.expires_at.isnot(None),
                DigitalFormSubmission.expires_at > min_expires_after,
            )
            .order_by(DigitalFormSubmission.created_at.desc())
        )
        if patient_id is not None:
            stmt = stmt.where(DigitalFormSubmission.patient_id == patient_id)
        else:
            stmt = stmt.where(DigitalFormSubmission.patient_id.is_(None))
        if booking_id is not None:
            stmt = stmt.where(DigitalFormSubmission.booking_id == booking_id)
        else:
            stmt = stmt.where(DigitalFormSubmission.booking_id.is_(None))
        result = await self.session.execute(stmt.limit(1))
        return result.scalars().first()

    async def create_form_link(
        self,
        clinic_id: UUID,
        template_id: UUID,
        patient_id: UUID | None = None,
        booking_id: UUID | None = None,
        ttl_hours: int = 24,
    ) -> str:
        template = await self.session.get(DigitalFormTemplate, template_id)
        if not template or template.clinic_id != clinic_id or not template.active:
            raise LookupError("Form template not found or not active")

        token_str = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        submission = await self._find_reusable_issued_submission(
            clinic_id, template_id, patient_id, booking_id, min_expires_after=now
        )
        if submission is not None:
            submission.expires_at = expires_at
            submission.updated_by = "system"
            await self.session.flush()
            await self._audit(submission.id, "reissued", "system", None)
            paperless_form_operations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), action="reissue"
            ).inc()
        else:
            submission = DigitalFormSubmission(
                clinic_id=clinic_id,
                template_id=template_id,
                patient_id=patient_id,
                booking_id=booking_id,
                status=FormStatus.ISSUED.value,
                submitted_by="system",
                data={},
                submitted_at=None,
                expires_at=expires_at,
                created_by="system",
                updated_by="system",
            )
            self.session.add(submission)
            await self.session.flush()

            await self._audit(submission.id, "issued", "system", None)
            self._record_transition_metric(clinic_id, FormStatus.DRAFT, FormStatus.ISSUED)
            paperless_form_operations_total.labels(
                clinic_bucket=clinic_bucket_label(clinic_id), action="issue"
            ).inc()

        link = FormLinkToken(
            token=token_str,
            clinic_id=clinic_id,
            template_id=template_id,
            digital_form_submission_id=submission.id,
            patient_id=patient_id,
            booking_id=booking_id,
            expires_at=expires_at,
        )
        self.session.add(link)
        await self.session.flush()

        logger.info(
            "paperless_form_issued",
            extra={
                "form_id": str(submission.id),
                "template_code": template.code,
                "patient_id": str(patient_id) if patient_id else None,
                "booking_id": str(booking_id) if booking_id else None,
                "clinic_id": str(clinic_id),
            },
        )
        return token_str

    async def revoke_submission(
        self,
        *,
        submission_id: UUID,
        clinic_id: UUID,
        actor: str,
    ) -> DigitalFormSubmission:
        submission = await self.session.get(DigitalFormSubmission, submission_id)
        if not submission or submission.clinic_id != clinic_id:
            raise LookupError("Form submission not found")
        prev = FormStatus.from_str(submission.status)
        self._status.assert_transition(prev, FormStatus.REVOKED)
        submission.status = FormStatus.REVOKED.value
        submission.updated_by = actor
        self._record_transition_metric(clinic_id, prev, FormStatus.REVOKED)
        await self._audit(submission.id, "revoked", actor, None)
        await self.session.flush()
        logger.info(
            "paperless_form_revoked",
            extra={
                "form_id": str(submission.id),
                "clinic_id": str(clinic_id),
            },
        )
        paperless_form_operations_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), action="revoke"
        ).inc()
        return submission

    async def cancel_submission(
        self,
        *,
        submission_id: UUID,
        clinic_id: UUID,
        actor: str,
    ) -> DigitalFormSubmission:
        submission = await self.session.get(DigitalFormSubmission, submission_id)
        if not submission or submission.clinic_id != clinic_id:
            raise LookupError("Form submission not found")
        prev = FormStatus.from_str(submission.status)
        self._status.assert_transition(prev, FormStatus.CANCELLED)
        submission.status = FormStatus.CANCELLED.value
        submission.updated_by = actor
        self._record_transition_metric(clinic_id, prev, FormStatus.CANCELLED)
        await self._audit(submission.id, "cancelled", actor, None)
        await self.session.flush()
        paperless_form_operations_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id), action="cancel"
        ).inc()
        return submission
