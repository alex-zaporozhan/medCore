"""Patient entity model."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Patient(Base):
    """Patient model."""

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vk_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    yandex_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vk_screen_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    yandex_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_channel: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="sms"
    )  # sms/telegram/email
    consent_pd_at: Mapped[datetime | None] = mapped_column(nullable=True)
    consent_mailing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    disable_discount_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    disable_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    disable_all_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "phone", name="ux_patients_clinic_phone"),
        Index("idx_patients_clinic_id", "clinic_id"),
        Index("idx_patients_vk_id", "vk_id"),
        Index("idx_patients_yandex_id", "yandex_id"),
        UniqueConstraint("clinic_id", "vk_id", name="ux_patients_clinic_vk_id"),
        UniqueConstraint("clinic_id", "yandex_id", name="ux_patients_clinic_yandex_id"),
    )
