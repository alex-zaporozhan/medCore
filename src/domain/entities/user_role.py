"""UserRole entity linking admin users to roles per clinic."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class UserRole(Base):
    """Assignment of roles to admin users within a clinic."""

    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ux_user_roles_user_role_clinic",
            "user_id",
            "role_id",
            "clinic_id",
            unique=True,
        ),
        Index("idx_user_roles_clinic_id", "clinic_id"),
    )

