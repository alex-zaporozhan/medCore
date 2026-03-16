"""Celery tasks: Export Builder — generate file, store, expose status + download (B5.5)."""

import asyncio
import csv
import json
import logging
import os
from uuid import UUID

from sqlalchemy import select

from src.core.config import settings
from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)

EXPORT_MAX_ROWS = 10_000
EXPORT_STATUS_KEY_PREFIX = "export:status:"
EXPORT_STATUS_TTL = 86400 * 2  # 2 days
# Storage: local dir; set EXPORT_STORAGE_PATH env or use default
EXPORT_STORAGE_PATH = os.environ.get("EXPORT_STORAGE_PATH", os.path.join(os.getcwd(), "data", "exports"))


def _get_redis_sync():
    import redis
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


def _set_export_status(task_id: str, status: str, download_url: str | None = None, error: str | None = None) -> None:
    r = _get_redis_sync()
    payload = {"status": status}
    if download_url:
        payload["download_url"] = download_url
    if error:
        payload["error"] = error
    r.setex(
        f"{EXPORT_STATUS_KEY_PREFIX}{task_id}",
        EXPORT_STATUS_TTL,
        json.dumps(payload),
    )


async def _run_export_async(
    task_id: str,
    clinic_id: str,
    columns: list[str],
    format_type: str,
    entity_type: str,
    admin_id: str,
) -> None:
    os.makedirs(EXPORT_STORAGE_PATH, exist_ok=True)
    ext = "xlsx" if format_type == "excel" else "csv"
    filename = f"{task_id}.{ext}"
    filepath = os.path.join(EXPORT_STORAGE_PATH, filename)
    clinic_uuid = UUID(clinic_id)

    try:
        async with AsyncSessionLocal() as session:
            if entity_type == "patients":
                stmt = (
                    select(Patient)
                    .where(Patient.clinic_id == clinic_uuid, Patient.deleted_at.is_(None))
                    .limit(EXPORT_MAX_ROWS + 1)
                )
                result = await session.execute(stmt)
                rows_orm = result.scalars().all()
                cols = columns or ["id", "full_name", "phone", "email", "created_at"]
                rows = []
                for p in rows_orm[:EXPORT_MAX_ROWS]:
                    row = {}
                    for c in cols:
                        row[c] = getattr(p, c, None)
                        if hasattr(row[c], "isoformat"):
                            row[c] = str(row[c])
                        elif row[c] is not None:
                            row[c] = str(row[c])
                    rows.append(row)
            elif entity_type == "bookings":
                stmt = (
                    select(Booking)
                    .where(Booking.clinic_id == clinic_uuid, Booking.deleted_at.is_(None))
                    .limit(EXPORT_MAX_ROWS + 1)
                )
                result = await session.execute(stmt)
                rows_orm = result.scalars().all()
                cols = columns or ["id", "patient_id", "doctor_id", "service_id", "appointment_date", "appointment_time", "status"]
                rows = []
                for b in rows_orm[:EXPORT_MAX_ROWS]:
                    row = {}
                    for c in cols:
                        row[c] = getattr(b, c, None)
                        if hasattr(row.get(c), "isoformat"):
                            row[c] = str(row[c])
                        elif row[c] is not None:
                            row[c] = str(row[c])
                    rows.append(row)
            else:
                _set_export_status(task_id, "failed", error=f"Unsupported entity_type: {entity_type}")
                return

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not rows:
                writer = csv.writer(f)
                writer.writerow(cols)
            else:
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

        download_url = f"/api/v1/admin/export/download/{task_id}"
        _set_export_status(task_id, "completed", download_url=download_url)
        logger.info("export completed", extra={"task_id": task_id, "rows": len(rows)})
    except Exception as e:
        logger.exception("export failed", extra={"task_id": task_id})
        _set_export_status(task_id, "failed", error=str(e))
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass


EXPORT_CLEANUP_DAYS = 2
BACKUP_CLEANUP_DAYS = 3


@celery_app.task(name="export_tasks.cleanup_old_exports_and_backups")
def cleanup_old_exports_and_backups() -> None:
    """Remove export and backup files older than N days (optional policy)."""
    import time
    now = time.time()
    for folder, days in (
        (EXPORT_STORAGE_PATH, EXPORT_CLEANUP_DAYS),
        (os.environ.get("BACKUP_STORAGE_PATH", os.path.join(os.getcwd(), "data", "backups")), BACKUP_CLEANUP_DAYS),
    ):
        if not os.path.isdir(folder):
            continue
        cutoff = now - (days * 86400)
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    logger.info("cleanup_old_exports_and_backups: removed %s", path)
            except OSError as e:
                logger.warning("cleanup_old_exports_and_backups: failed to remove %s: %s", path, e)


@celery_app.task(name="export_tasks.run_export", bind=True)
def run_export(
    self,
    task_id: str,
    clinic_id: str,
    columns: list[str],
    format_type: str,
    entity_type: str,
    admin_id: str,
) -> None:
    """Generate export file and store status in Redis. format_type: excel | csv (both produce CSV for now)."""
    asyncio.run(
        _run_export_async(task_id, clinic_id, columns or [], format_type, entity_type, admin_id)
    )
