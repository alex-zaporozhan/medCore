"""Tests for Paperless FormsService (reuse, gates)."""

from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select

from src.application.services.forms_service import FormsService
from src.domain.entities.digital_form_submission import DigitalFormSubmission
from src.domain.entities.digital_form_template import DigitalFormTemplate
from src.domain.entities.form_link_token import FormLinkToken
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_create_form_link_reuses_non_expired_issued_submission(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    code = f"reuse_test_{seed_data['clinic_id'].hex[:8]}"
    try:
        async with db_base.AsyncSessionLocal() as session:
            tmpl = DigitalFormTemplate(
                clinic_id=clinic_id,
                code=code,
                name="Reuse",
                description=None,
                version=1,
                schema={"fields": []},
                requires_signature=False,
                required_for_visit_completion=False,
                active=True,
            )
            session.add(tmpl)
            await session.commit()
            await session.refresh(tmpl)

            svc = FormsService(session)
            await svc.create_form_link(
                clinic_id=clinic_id,
                template_id=tmpl.id,
                patient_id=patient_id,
                booking_id=None,
                ttl_hours=24,
            )
            await session.commit()
            await svc.create_form_link(
                clinic_id=clinic_id,
                template_id=tmpl.id,
                patient_id=patient_id,
                booking_id=None,
                ttl_hours=24,
            )
            await session.commit()

            cnt = await session.execute(
                select(func.count()).select_from(DigitalFormSubmission).where(
                    DigitalFormSubmission.template_id == tmpl.id,
                    DigitalFormSubmission.patient_id == patient_id,
                )
            )
            assert cnt.scalar_one() == 1
    finally:
        async with db_base.AsyncSessionLocal() as session:
            template_ids = (
                await session.execute(
                    select(DigitalFormTemplate.id).where(
                        DigitalFormTemplate.clinic_id == clinic_id,
                        DigitalFormTemplate.code == code,
                    )
                )
            ).scalars().all()
            if template_ids:
                await session.execute(
                    delete(FormLinkToken).where(FormLinkToken.template_id.in_(template_ids))
                )
                await session.execute(
                    delete(DigitalFormSubmission).where(
                        DigitalFormSubmission.template_id.in_(template_ids)
                    )
                )
            await session.execute(
                delete(DigitalFormTemplate).where(
                    DigitalFormTemplate.clinic_id == clinic_id,
                    DigitalFormTemplate.code == code,
                )
            )
            await session.commit()
