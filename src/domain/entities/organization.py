"""Organization: groups multiple clinics (network / enterprise tenant boundary)."""

import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Organization(Base):
    """One business may own many clinics; strict data isolation remains per clinic_id."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
