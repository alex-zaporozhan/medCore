"""DTOs for loyalty campaign settings and run results (LOY_AI_014)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoyaltyCampaignSettingsRead(BaseModel):
    clinic_id: UUID
    expiring_packages_enabled: bool
    high_balance_low_activity_enabled: bool
    reengagement_enabled: bool
    channel_tasks_enabled: bool
    channel_omnichannel_enabled: bool
    skip_expiring_task_if_sms_expiring_sent_today: bool
    max_contacts_per_day_clinic: int = Field(ge=1, le=10_000)
    max_contacts_per_day_patient: int = Field(ge=1, le=100)
    max_campaign_touches_per_patient_month: int = Field(ge=1, le=100)
    campaign_cooldown_days: int = Field(ge=1, le=365)
    reengagement_inactive_days: int = Field(ge=30, le=730)
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class LoyaltyCampaignSettingsUpdate(BaseModel):
    expiring_packages_enabled: bool | None = None
    high_balance_low_activity_enabled: bool | None = None
    reengagement_enabled: bool | None = None
    channel_tasks_enabled: bool | None = None
    channel_omnichannel_enabled: bool | None = None
    skip_expiring_task_if_sms_expiring_sent_today: bool | None = None
    max_contacts_per_day_clinic: int | None = Field(default=None, ge=1, le=10_000)
    max_contacts_per_day_patient: int | None = Field(default=None, ge=1, le=100)
    max_campaign_touches_per_patient_month: int | None = Field(
        default=None, ge=1, le=100
    )
    campaign_cooldown_days: int | None = Field(default=None, ge=1, le=365)
    reengagement_inactive_days: int | None = Field(default=None, ge=30, le=730)


class LoyaltyCampaignRunResult(BaseModel):
    clinic_id: UUID
    created_expiring: int = 0
    created_high_balance: int = 0
    created_reengagement: int = 0
    skipped_limits: int = 0
    skipped_cooldown: int = 0
    skipped_cross_campaign: int = 0
    skipped_sms_duplicate: int = 0
    skipped_opt_out: int = 0


def default_loyalty_campaign_settings_read(clinic_id: UUID) -> LoyaltyCampaignSettingsRead:
    """API defaults when no row exists yet (GET without side effects)."""
    return LoyaltyCampaignSettingsRead(
        clinic_id=clinic_id,
        expiring_packages_enabled=True,
        high_balance_low_activity_enabled=True,
        reengagement_enabled=True,
        channel_tasks_enabled=True,
        channel_omnichannel_enabled=False,
        skip_expiring_task_if_sms_expiring_sent_today=True,
        max_contacts_per_day_clinic=50,
        max_contacts_per_day_patient=3,
        max_campaign_touches_per_patient_month=12,
        campaign_cooldown_days=14,
        reengagement_inactive_days=180,
        updated_at=None,
    )
