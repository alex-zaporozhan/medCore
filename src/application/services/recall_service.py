"""Recall service: segments, campaigns, automations, run campaign."""

from datetime import date, timedelta

from src.core.datetime_utils import utc_now_naive
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.recall_dto import (
    RecallAutomationCreate,
    RecallCampaignCreate,
    RecallSegmentCreate,
    RecallTemplateCreate,
)
from src.application.services.messaging_service import send_recall_message
from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient
from src.domain.entities.recall_automation import RecallAutomation
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.recall_log import RecallLog
from src.domain.entities.recall_segment import RecallSegment
from src.domain.entities.recall_template import RecallTemplate


def _apply_segment_filter(
    session: AsyncSession,
    clinic_id: UUID,
    filter_json: dict | None,
):
    """Return query that selects patient_id satisfying segment filter."""
    if not filter_json or "last_visit_older_than_days" not in filter_json:
        # All patients of clinic
        stmt = select(Patient.id).where(
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
        return stmt

    days = int(filter_json["last_visit_older_than_days"])
    threshold = date.today() - timedelta(days=days)
    # Last completed/no_show visit per patient
    last_visit = (
        select(
            Booking.patient_id,
            func.max(Booking.appointment_date).label("last_date"),
        )
        .where(
            Booking.clinic_id == clinic_id,
            Booking.status.in_(["completed", "no_show"]),
            Booking.deleted_at.is_(None),
        )
        .group_by(Booking.patient_id)
    )
    subq = last_visit.subquery()
    stmt = (
        select(Patient.id)
        .where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
        .outerjoin(subq, Patient.id == subq.c.patient_id)
        .where(
            (subq.c.last_date.is_(None)) | (subq.c.last_date < threshold)
        )
    )
    return stmt


async def get_segment_patient_ids(
    session: AsyncSession,
    clinic_id: UUID,
    segment: RecallSegment,
) -> list[UUID]:
    """Return list of patient IDs in segment."""
    stmt = _apply_segment_filter(session, clinic_id, segment.filter_json)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_segment_patient_count(
    session: AsyncSession,
    clinic_id: UUID,
    segment_id: UUID,
) -> int:
    """Return number of patients in segment."""
    result = await session.execute(
        select(RecallSegment).where(
            RecallSegment.id == segment_id,
            RecallSegment.clinic_id == clinic_id,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        return 0
    stmt = _apply_segment_filter(session, clinic_id, segment.filter_json)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    r = await session.execute(count_stmt)
    return r.scalar() or 0


async def create_segment(
    session: AsyncSession,
    clinic_id: UUID,
    body: RecallSegmentCreate,
) -> RecallSegment:
    seg = RecallSegment(
        clinic_id=clinic_id,
        name=body.name,
        filter_json=body.filter_json,
    )
    session.add(seg)
    await session.flush()
    await session.refresh(seg)
    return seg


async def create_template(
    session: AsyncSession,
    clinic_id: UUID,
    body: RecallTemplateCreate,
) -> RecallTemplate:
    t = RecallTemplate(
        clinic_id=clinic_id,
        name=body.name,
        channel=body.channel,
        subject=body.subject,
        body_template=body.body_template,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


async def create_campaign(
    session: AsyncSession,
    clinic_id: UUID,
    body: RecallCampaignCreate,
) -> RecallCampaign:
    c = RecallCampaign(
        clinic_id=clinic_id,
        segment_id=body.segment_id,
        template_id=body.template_id,
        name=body.name,
        status=body.status,
        scheduled_at=body.scheduled_at,
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c


async def create_automation(
    session: AsyncSession,
    clinic_id: UUID,
    body: RecallAutomationCreate,
) -> RecallAutomation:
    a = RecallAutomation(
        clinic_id=clinic_id,
        name=body.name,
        trigger_type=body.trigger_type,
        trigger_config_json=body.trigger_config_json,
        segment_id=body.segment_id,
        template_id=body.template_id,
        enabled=body.enabled,
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a


def _render_body(template: str, context: dict) -> str:
    """Simple placeholder replace: {{name}} -> context['name']."""
    out = template
    for k, v in context.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


async def run_campaign(
    session: AsyncSession,
    clinic_id: UUID,
    campaign_id: UUID,
) -> tuple[int, int]:
    """
    Run campaign: resolve segment, send via template to each patient, write RecallLog.
    Returns (sent_count, failed_count).
    """
    result = await session.execute(
        select(RecallCampaign, RecallSegment, RecallTemplate)
        .join(RecallSegment, RecallCampaign.segment_id == RecallSegment.id)
        .join(RecallTemplate, RecallCampaign.template_id == RecallTemplate.id)
        .where(
            RecallCampaign.id == campaign_id,
            RecallCampaign.clinic_id == clinic_id,
        )
    )
    row = result.one_or_none()
    if not row:
        return 0, 0
    campaign, segment, template = row
    if campaign.status not in ("draft", "scheduled"):
        return 0, 0

    campaign.status = "running"
    campaign.started_at = utc_now_naive()
    await session.flush()

    patient_ids = await get_segment_patient_ids(session, clinic_id, segment)
    sent, failed = 0, 0
    for patient_id in patient_ids:
        log = RecallLog(
            clinic_id=clinic_id,
            campaign_id=campaign_id,
            automation_id=None,
            patient_id=patient_id,
            channel=template.channel,
            status="pending",
            sent_at=None,
            error=None,
        )
        session.add(log)
        await session.flush()

        body = _render_body(template.body_template, {"patient_id": str(patient_id)})
        success, err = await send_recall_message(
            session,
            clinic_id=clinic_id,
            patient_id=patient_id,
            channel=template.channel,
            message=body,
            subject=template.subject,
            template=f"recall_campaign_{campaign_id}",
        )
        now = utc_now_naive()
        if success:
            log.status = "sent"
            log.sent_at = now
            sent += 1
        else:
            log.status = "failed"
            log.sent_at = now
            log.error = (err or "unknown")[:1000]
            failed += 1
        await session.flush()

    campaign.status = "completed"
    campaign.completed_at = utc_now_naive()
    await session.flush()
    return sent, failed
