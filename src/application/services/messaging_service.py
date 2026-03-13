"""Messaging service: send via channel with preferences and fallback."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.notification_service import send_with_fallback
from src.domain.entities.patient import Patient
from src.domain.entities.patient_communication_preferences import (
    PatientCommunicationPreferences,
)

logger = logging.getLogger(__name__)


async def send_recall_message(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    patient_id: UUID,
    channel: str,
    message: str,
    subject: str | None = None,
    template: str = "recall",
) -> tuple[bool, str | None]:
    """
    Send one recall message to patient. Respects PatientCommunicationPreferences.
    Returns (success, error_message).
    """
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return False, "patient_not_found"

    pref_result = await session.execute(
        select(PatientCommunicationPreferences).where(
            PatientCommunicationPreferences.patient_id == patient_id,
            PatientCommunicationPreferences.channel == channel,
        )
    )
    pref = pref_result.scalar_one_or_none()
    if pref is not None and not pref.enabled:
        return False, "opt_out"

    preferred = getattr(patient, "preferred_channel", None) or "sms"
    success, err = await send_with_fallback(
        chat_id=patient.telegram_chat_id,
        phone=patient.phone,
        email=patient.email,
        message=message,
        template=template,
        meta={"clinic_id": str(clinic_id), "subject": subject or ""},
        preferred_channel=channel if channel in ("telegram", "sms", "email") else preferred,
    )
    return success, err
