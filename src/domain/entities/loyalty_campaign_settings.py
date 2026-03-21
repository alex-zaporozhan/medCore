"""Per-clinic settings for loyalty campaign engine (LOY_AI_014)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class LoyaltyCampaignSettings(Base):
    """Flags, limits and channel toggles for automated loyalty campaigns."""

    __tablename__ = "loyalty_campaign_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True
    )

    expiring_packages_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )
    high_balance_low_activity_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )
    reengagement_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )

    channel_tasks_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )
    channel_omnichannel_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="false"
    )

    skip_expiring_task_if_sms_expiring_sent_today: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )

    max_contacts_per_day_clinic: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="50"
    )
    max_contacts_per_day_patient: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="3"
    )
    max_campaign_touches_per_patient_month: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="12"
    )
    campaign_cooldown_days: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="14"
    )
    reengagement_inactive_days: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="180"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("clinic_id", name="ux_loyalty_campaign_settings_clinic"),
    )
