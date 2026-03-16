"""Celery tasks: Full Backup — dump critical data, store, expose status + download (B5.5)."""

import asyncio
import json
import logging
import os
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from src.core.config import settings
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)

BACKUP_STATUS_KEY_PREFIX = "backup:status:"
BACKUP_STATUS_TTL = 86400 * 3  # 3 days
BACKUP_STORAGE_PATH = os.environ.get("BACKUP_STORAGE_PATH", os.path.join(os.getcwd(), "data", "backups"))


def _get_redis_sync():
    import redis
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _set_backup_status(task_id: str, status: str, download_url: str | None = None, error: str | None = None) -> None:
    r = _get_redis_sync()
    payload = {"status": status}
    if download_url:
        payload["download_url"] = download_url
    if error:
        payload["error"] = error
    r.setex(
        f"{BACKUP_STATUS_KEY_PREFIX}{task_id}",
        BACKUP_STATUS_TTL,
        json.dumps(payload),
    )


def _serialize(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(type(obj))


async def _run_full_backup_async(task_id: str, clinic_id: str) -> None:
    os.makedirs(BACKUP_STORAGE_PATH, exist_ok=True)
    filename = f"{task_id}.json"
    filepath = os.path.join(BACKUP_STORAGE_PATH, filename)
    clinic_uuid = UUID(clinic_id)

    try:
        async with AsyncSessionLocal() as session:
            # Clinics
            clinic_result = await session.execute(select(Clinic).where(Clinic.id == clinic_uuid))
            clinic = clinic_result.scalar_one_or_none()
            if not clinic:
                _set_backup_status(task_id, "failed", error="Clinic not found")
                return

            clinics_data = [{"id": str(clinic.id), "name": clinic.name}]

            # Patients (critical)
            patients_result = await session.execute(
                select(Patient).where(Patient.clinic_id == clinic_uuid, Patient.deleted_at.is_(None))
            )
            patients = patients_result.scalars().all()
            patients_data = []
            for p in patients:
                patients_data.append({
                    "id": str(p.id),
                    "clinic_id": str(p.clinic_id),
                    "phone": p.phone,
                    "full_name": p.full_name,
                    "email": p.email,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })

            # Bookings (critical)
            bookings_result = await session.execute(
                select(Booking).where(Booking.clinic_id == clinic_uuid, Booking.deleted_at.is_(None))
            )
            bookings = bookings_result.scalars().all()
            bookings_data = []
            for b in bookings:
                bookings_data.append({
                    "id": str(b.id),
                    "clinic_id": str(b.clinic_id),
                    "patient_id": str(b.patient_id),
                    "doctor_id": str(b.doctor_id),
                    "service_id": str(b.service_id),
                    "appointment_date": b.appointment_date.isoformat() if b.appointment_date else None,
                    "appointment_time": str(b.appointment_time) if b.appointment_time else None,
                    "status": b.status,
                })

            backup = {
                "task_id": task_id,
                "clinic_id": clinic_id,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "clinics": clinics_data,
                "patients": patients_data,
                "bookings": bookings_data,
            }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2, default=_serialize)

        download_url = f"/api/v1/admin/backup/download/{task_id}"
        _set_backup_status(task_id, "completed", download_url=download_url)
        logger.info("backup completed", extra={"task_id": task_id})
    except Exception as e:
        logger.exception("backup failed", extra={"task_id": task_id})
        _set_backup_status(task_id, "failed", error=str(e))
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass


@celery_app.task(name="backup_tasks.run_full_backup", bind=True)
def run_full_backup(self, task_id: str, clinic_id: str) -> None:
    """Create backup archive for clinic and store status in Redis."""
    asyncio.run(_run_full_backup_async(task_id, clinic_id))
