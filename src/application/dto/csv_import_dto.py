"""DTOs for CSV import/export operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CsvImportJobRead(BaseModel):
    """Read DTO for CsvImportJob."""

    id: UUID
    clinic_id: UUID
    file_name: str
    status: str
    total_rows: int | None = None
    processed_rows: int | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

