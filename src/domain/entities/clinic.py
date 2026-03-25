"""Clinic entity model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, Text, Time, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Clinic(Base):
    """Clinic model."""

    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    workday_start: Mapped[Time] = mapped_column(Time, nullable=False, server_default="09:00:00")
    workday_end: Mapped[Time] = mapped_column(Time, nullable=False, server_default="21:00:00")
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    prepayment_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="500.00"
    )
    prepayment_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    payment_gateway: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="yookassa"
    )
    payment_gateway_custom_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yookassa_shop_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yookassa_secret_key_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    theme_primary_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    theme_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    theme_font_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="stomatology")
    business_type_custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person_label_singular: Mapped[str | None] = mapped_column(String(50), nullable=True)
    person_label_plural: Mapped[str | None] = mapped_column(String(50), nullable=True)
    staff_label_plural: Mapped[str | None] = mapped_column(String(50), nullable=True)
    allow_patient_disable_discount_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    allow_patient_disable_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    allow_patient_disable_all_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    #: Внутренний чат персонала: `clinic_isolated` — только сотрудники этой клиники (строка clinics.id).
    #: `network` зарезервировано под сеть салонов (см. docs/architecture/STAFF_CHAT_MULTITENANCY.md).
    staff_chat_scope: Mapped[str] = mapped_column(String(32), nullable=False, server_default="clinic_isolated")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
