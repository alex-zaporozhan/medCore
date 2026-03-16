"""Omni-Vault: Export Builder, Full Backup. B5.5."""

from __future__ import annotations

import json
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.api.v1.dependencies import require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.messaging.tasks.export_tasks import run_export

router = APIRouter(prefix="/admin", tags=["admin-vault"])

EXPORT_STATUS_KEY_PREFIX = "export:status:"
EXPORT_STORAGE_PATH = os.environ.get("EXPORT_STORAGE_PATH", os.path.join(os.getcwd(), "data", "exports"))


# --- Export Builder ---
class ExportRequest(BaseModel):
    columns: list[str] = Field(default_factory=list)
    format: str = Field("csv", description="excel | csv")
    entity_type: str = Field(..., description="patients | bookings | ...")


class ExportResponse(BaseModel):
    task_id: str | None = None
    status: str = "pending"
    download_url: str | None = None
    message: str = "Export queued"


class ExportStatusResponse(BaseModel):
    task_id: str
    status: str
    download_url: str | None = None
    error: str | None = None


@router.post("/export", response_model=ExportResponse)
async def request_export(
    body: ExportRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("view_crm")),
) -> ExportResponse:
    """Request export (columns, format, entity_type). Enqueues Celery task; use GET /export/status?task_id= for result."""
    if body.format not in ("excel", "csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be excel or csv")
    if not current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context required")
    task_id = str(uuid4())
    run_export.delay(
        task_id=task_id,
        clinic_id=str(current_admin.clinic_id),
        columns=body.columns,
        format_type=body.format,
        entity_type=body.entity_type,
        admin_id=str(current_admin.id),
    )
    return ExportResponse(task_id=task_id, status="pending", message="Export queued")


@router.get("/export/status", response_model=ExportStatusResponse)
async def export_status(
    task_id: str = Query(..., alias="task_id"),
    _: AdminUser = Depends(get_current_admin),
) -> ExportStatusResponse:
    """Return export task status and download_url when completed. 404 if task_id unknown."""
    redis = await get_redis()
    key = f"{EXPORT_STATUS_KEY_PREFIX}{task_id}"
    raw = await redis.get(key)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or expired")
    data = json.loads(raw)
    return ExportStatusResponse(
        task_id=task_id,
        status=data.get("status", "pending"),
        download_url=data.get("download_url"),
        error=data.get("error"),
    )


@router.get("/export/download/{task_id}")
async def export_download(
    task_id: str,
    _: AdminUser = Depends(get_current_admin),
    __=Depends(require_permissions("view_crm")),
):
    """Stream export file. 404 if not found or expired."""
    for ext in ("csv", "xlsx"):
        path = os.path.join(EXPORT_STORAGE_PATH, f"{task_id}.{ext}")
        if os.path.isfile(path):
            return FileResponse(path, filename=f"export_{task_id}.{ext}")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or expired")


# --- Full Backup ---
BACKUP_STATUS_KEY_PREFIX = "backup:status:"
BACKUP_STORAGE_PATH = os.environ.get("BACKUP_STORAGE_PATH", os.path.join(os.getcwd(), "data", "backups"))


class BackupRequestResponse(BaseModel):
    task_id: str
    status: str = "pending"


class BackupStatusResponse(BaseModel):
    task_id: str
    status: str
    download_url: str | None = None
    error: str | None = None


@router.post("/backup/request", response_model=BackupRequestResponse)
async def request_backup(
    current_admin: AdminUser = Depends(get_current_admin),
    __=Depends(require_permissions("view_crm")),
) -> BackupRequestResponse:
    """Request full backup (Celery). Returns task_id; use GET /backup/status?task_id= for result."""
    if not current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context required")
    task_id = str(uuid4())
    from src.infrastructure.messaging.tasks.backup_tasks import run_full_backup
    run_full_backup.delay(task_id=task_id, clinic_id=str(current_admin.clinic_id))
    return BackupRequestResponse(task_id=task_id, status="pending")


@router.get("/backup/status", response_model=BackupStatusResponse)
async def backup_status(
    task_id: str = Query(..., alias="task_id"),
    _: AdminUser = Depends(get_current_admin),
) -> BackupStatusResponse:
    """Backup task status and download_url when ready. 404 if task_id unknown."""
    redis = await get_redis()
    key = f"{BACKUP_STATUS_KEY_PREFIX}{task_id}"
    raw = await redis.get(key)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or expired")
    data = json.loads(raw)
    return BackupStatusResponse(
        task_id=task_id,
        status=data.get("status", "pending"),
        download_url=data.get("download_url"),
        error=data.get("error"),
    )


@router.get("/backup/download/{task_id}")
async def backup_download(
    task_id: str,
    _: AdminUser = Depends(get_current_admin),
    __=Depends(require_permissions("view_crm")),
):
    """Stream backup file. 404 if not found or expired."""
    path = os.path.join(BACKUP_STORAGE_PATH, f"{task_id}.json")
    if os.path.isfile(path):
        return FileResponse(path, filename=f"backup_{task_id}.json")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or expired")
