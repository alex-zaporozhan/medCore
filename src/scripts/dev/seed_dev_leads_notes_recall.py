"""
DEV ONLY: Fill CRM leads, lead notes, and recall campaign data so UI is not empty.

Requires: seed_demo_data and seed_dev_full_demo already run (clinic, admin, patients, bookings).

Run:
  poetry run python -m src.scripts.dev.seed_dev_leads_notes_recall
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.clinic import Clinic
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.patient import Patient
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_note import LeadNote
from src.domain.entities.recall_segment import RecallSegment
from src.domain.entities.recall_template import RecallTemplate
from src.domain.entities.recall_campaign import RecallCampaign
from src.domain.entities.recall_log import RecallLog


DEMO_NOTES = [
    "Позвонил, договорились на среду.",
    "Клиент просил перезвонить после праздников.",
    "Оформили предоплату, ждём визит.",
    "Уточнить время приезда за день до приёма.",
    "Интересует имплантация — отправил прайс.",
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1))
        clinic = res.scalar_one_or_none()
        if not clinic:
            print("Error: no clinic. Run seed_demo_data then seed_dev_full_demo first.")
            return

        res = await session.execute(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic.id,
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        admin = res.scalar_one_or_none()
        if not admin:
            print("Error: no admin. Run seed_demo_data.")
            return

        res = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.deleted_at.is_(None),
            ).order_by(Patient.phone).limit(15)
        )
        patients = list(res.scalars().all())
        if not patients:
            print("Error: no patients.")
            return

        clinic_id = clinic.id
        admin_id = admin.id

        # --- Lead pipeline + stages (if missing) ---
        res = await session.execute(
            select(LeadPipeline).where(LeadPipeline.clinic_id == clinic_id).limit(1)
        )
        pipeline = res.scalar_one_or_none()
        if not pipeline:
            pipeline = LeadPipeline(
                clinic_id=clinic_id,
                name="Продажи",
                description="Основная воронка",
                is_default=True,
            )
            session.add(pipeline)
            await session.flush()
            for order, (code, name, prob, color) in enumerate(
                [
                    ("new", "Новая заявка", 10, "#888"),
                    ("contact", "Контакт", 30, "#4a90d9"),
                    ("meeting", "Запись", 60, "#7ed321"),
                    ("won", "Успех", 100, "#50e3c2"),
                ],
                1,
            ):
                st = LeadStage(
                    clinic_id=clinic_id,
                    pipeline_id=pipeline.id,
                    order=order,
                    code=code,
                    name=name,
                    probability=prob,
                    color=color,
                )
                session.add(st)
            await session.flush()
            res = await session.execute(
                select(LeadStage).where(
                    LeadStage.clinic_id == clinic_id,
                    LeadStage.pipeline_id == pipeline.id,
                ).order_by(LeadStage.order)
            )
            stages = list(res.scalars().all())
        else:
            res = await session.execute(
                select(LeadStage).where(
                    LeadStage.clinic_id == clinic_id,
                    LeadStage.pipeline_id == pipeline.id,
                ).order_by(LeadStage.order)
            )
            stages = list(res.scalars().all())
        if not stages:
            print("No pipeline stages - skipping leads.")
        else:
            # --- Lead cards + notes ---
            stage_new = next((s for s in stages if s.code == "new"), stages[0])
            stage_contact = next((s for s in stages if s.code == "contact"), stages[min(1, len(stages) - 1)])
            existing_leads = await session.execute(
                select(LeadCard).where(LeadCard.clinic_id == clinic_id)
            )
            existing_count = len(existing_leads.scalars().all())
            for i, patient in enumerate(patients[:8]):
                if existing_count + i >= 8:
                    break
                lead = LeadCard(
                    clinic_id=clinic_id,
                    pipeline_id=pipeline.id,
                    stage_id=stage_contact.id if i % 2 == 0 else stage_new.id,
                    patient_id=patient.id,
                    title=f"Заявка от {patient.full_name or patient.phone}",
                    source="site",
                    utm_source="yandex",
                    estimated_value=Decimal("5000.00"),
                    actual_value=Decimal("0.00"),
                    status="open",
                )
                session.add(lead)
                await session.flush()
                for j, note_text in enumerate(DEMO_NOTES[(i % len(DEMO_NOTES)) : (i % len(DEMO_NOTES)) + 2]):
                    session.add(
                        LeadNote(
                            clinic_id=clinic_id,
                            lead_id=lead.id,
                            author_admin_id=admin_id,
                            text=note_text,
                        )
                    )
            await session.flush()

        # --- Recall: segment, template, campaign, logs (if missing) ---
        res = await session.execute(
            select(RecallSegment).where(RecallSegment.clinic_id == clinic_id).limit(1)
        )
        segment = res.scalar_one_or_none()
        if not segment:
            segment = RecallSegment(
                clinic_id=clinic_id,
                name="Все активные",
                filter_json={},
            )
            session.add(segment)
            await session.flush()

        res = await session.execute(
            select(RecallTemplate).where(RecallTemplate.clinic_id == clinic_id).limit(1)
        )
        template = res.scalar_one_or_none()
        if not template:
            template = RecallTemplate(
                clinic_id=clinic_id,
                name="Напоминание о визите",
                channel="sms",
                body_template="Добрый день! Напоминаем о записи на {{date}} в {{time}}. Подтвердите, пожалуйста.",
            )
            session.add(template)
            await session.flush()

        res = await session.execute(
            select(RecallCampaign).where(RecallCampaign.clinic_id == clinic_id).limit(1)
        )
        campaign = res.scalar_one_or_none()
        if not campaign:
            campaign = RecallCampaign(
                clinic_id=clinic_id,
                segment_id=segment.id,
                template_id=template.id,
                name="Мартовское напоминание",
                status="completed",
                started_at=datetime.utcnow() - timedelta(days=5),
                completed_at=datetime.utcnow() - timedelta(days=2),
            )
            session.add(campaign)
            await session.flush()

        res = await session.execute(
            select(RecallLog).where(RecallLog.clinic_id == clinic_id).limit(1)
        )
        if res.scalar_one_or_none() is None:
            for patient in patients[:5]:
                session.add(
                    RecallLog(
                        clinic_id=clinic_id,
                        campaign_id=campaign.id,
                        patient_id=patient.id,
                        channel="sms",
                        status="sent",
                        sent_at=datetime.utcnow() - timedelta(days=3),
                    )
                )
            await session.flush()

        await session.commit()
        print("DEV leads/notes/recall: pipeline, leads with notes, recall campaign with logs. Done.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
