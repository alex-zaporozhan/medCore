"""Platform operator (Основатель SaaS) — separate from tenant AdminUser (ADR-007, 1a-E2)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PlatformFounderUser(Base):
    """Credentials for `/platform/auth/login`; JWT `sub` must match an active row."""

    __tablename__ = "platform_founder_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="true")
    #: Fernet ciphertext of TOTP shared secret (base32); set during enroll, cleared only by break-glass / replace.
    totp_secret_ciphertext: Mapped[str | None] = mapped_column(Text(), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
