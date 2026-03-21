"""Create operational signals when admins repeatedly hit multi-tenant boundaries."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.multitenancy import ClinicForbiddenError
from src.application.services.task_service import TaskService
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.database.redis_client import get_redis
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl

logger = logging.getLogger(__name__)

_MISMATCH_WINDOW_SECONDS = 3600
_THRESHOLD = 3
_TASK_DEDUP_SECONDS = 86400


async def record_admin_clinic_boundary_event(
    session: AsyncSession,
    admin: AdminUser,
    *,
    exc: ClinicForbiddenError | None = None,
    reason: str | None = None,
) -> None:
    """Increment Redis counter for this admin; after threshold, create one Task (dedup per day)."""
    try:
        redis = await get_redis()
    except Exception as e:
        logger.warning("multitenancy_alert_redis_skip", extra={"error": str(e)})
        return

    admin_key = f"multitenancy:mismatch:admin:{admin.id}"
    task_key = f"multitenancy:mismatch:task:{admin.id}"

    try:
        n = await redis.incr(admin_key)
        if n == 1:
            await redis.expire(admin_key, _MISMATCH_WINDOW_SECONDS)
    except Exception as e:
        logger.warning("multitenancy_alert_incr_failed", extra={"error": str(e)})
        return

    if n < _THRESHOLD:
        return

    try:
        created = await redis.set(task_key, "1", ex=_TASK_DEDUP_SECONDS, nx=True)
    except Exception:
        created = None
    if not created:
        return

    if exc is not None:
        desc = (
            f"Администратор {admin.id} ({getattr(admin, 'email', '') or ''}) достиг порога "
            f"{_THRESHOLD} за час при обращении к {exc.entity_label}. "
            f"Ожидаемая клиника: {exc.expected_clinic_id}, "
            f"клиника сущности: {exc.entity_clinic_id}, id: {exc.entity_id}."
        )
    else:
        desc = (
            f"Администратор {admin.id} ({getattr(admin, 'email', '') or ''}) достиг порога "
            f"{_THRESHOLD} за час. Событие: {reason or 'clinic boundary'}."
        )

    try:
        task_svc = TaskService(TaskRepositoryImpl(session))
        await task_svc.create_task(
            clinic_id=admin.clinic_id,
            title="Повторные попытки доступа к чужой клинике (multi-tenant)",
            description=desc,
            status="open",
            priority="high",
            creator_id=None,
            assignee_id=None,
            role_assignee="owner",
            source="system",
            attention_kind="security.multitenancy_mismatch",
            attention_ref_id=exc.entity_id if exc is not None else None,
        )
        await session.flush()
        logger.info(
            "multitenancy_alert_task_created",
            extra={"admin_id": str(admin.id), "clinic_id": str(admin.clinic_id)},
        )
    except Exception as e:
        logger.warning("multitenancy_alert_task_failed", extra={"error": str(e)})


async def record_multitenancy_mismatch_for_admin(
    session: AsyncSession,
    admin: AdminUser,
    exc: ClinicForbiddenError,
) -> None:
    """Backward-compatible name: record boundary event with structured exception."""
    await record_admin_clinic_boundary_event(session, admin, exc=exc)
