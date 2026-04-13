"""Заявки с публичного сайта на корпоративный тариф (сбор контактов для отдела продаж)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class EnterpriseLead(Base):
    """Lead form submission from marketing (Enterprise / корпоративный план)."""

    __tablename__ = "enterprise_leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_or_email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="NEW",
    )
    #: ``corporate`` — форма «Обсудить внедрение»; ``sandbox_demo`` — страница /sandbox.
    lead_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="corporate",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
