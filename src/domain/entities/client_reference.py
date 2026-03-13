"""Single-row entity: client reference (problems and scenarios) for handover to client."""

import uuid
from datetime import datetime

from sqlalchemy import Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ClientReference(Base):
    """One row: editable client reference content (Markdown/text)."""

    __tablename__ = "client_reference"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text(), nullable=False, server_default="")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
