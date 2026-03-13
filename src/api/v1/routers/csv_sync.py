"""CSV import/export API endpoints."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.csv_import_dto import CsvImportJobRead
from src.application.services.csv_import_service import CsvImportService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["csv"])


@router.post(
    "/schedule/import-csv",
    response_model=CsvImportJobRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_schedule_csv(
    file: UploadFile = File(..., media_type="text/csv"),
    session: AsyncSession = Depends(get_session),
):
    """Import doctor schedule from CSV.

    CSV format:
    - Columns: doctor_id,date,time_slots
    - time_slots: JSON array of strings "HH:MM"
    """
    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type, expected text/csv",
        )

    try:
        raw_bytes = await file.read()
        # Support UTF-8 with or without BOM.
        content = raw_bytes.decode("utf-8-sig")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read uploaded CSV file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read CSV file",
        ) from exc

    service = CsvImportService(session)
    try:
        job = await service.import_schedule_from_csv(
            file_name=file.filename or "upload.csv",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during CSV import")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import CSV",
        ) from exc

    return CsvImportJobRead.model_validate(job)


@router.get(
    "/bookings/export-csv",
    response_class=Response,
)
async def export_completed_bookings_csv(
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Export completed bookings as CSV for a date range."""
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be less than or equal to date_to",
        )

    service = CsvImportService(session)
    try:
        csv_text, rows = await service.export_completed_bookings_csv(
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to export bookings CSV")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export CSV",
        ) from exc

    filename = f"bookings_completed_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Export-Rows": str(rows),
    }

    logger.info(
        "Bookings CSV exported",
        extra={
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "rows": rows,
        },
    )

    return Response(content=csv_text, media_type="text/csv", headers=headers)

