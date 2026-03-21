"""Metrics and optional Attention/Task escalation for booking/payment errors (W7 BE4, BE5)."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from src.application.booking_error_codes import normalize_booking_error_code
from src.application.dto.booking_dto import BookingErrorCode
from src.application.services.task_service import TaskService
from src.core.config import settings
from src.core.metrics import booking_errors_total, booking_error_attention_tasks_created_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl

logger = logging.getLogger(__name__)

_BOOKING_TOOL_NAMES = frozenset(
    {"get_available_slots", "create_booking", "cancel_booking", "reschedule_booking"}
)

# Noisy codes: burst Tasks would spam ops (BE5: prefer payment/gateway and system failures).
_EXCLUDED_FROM_BURST: frozenset[BookingErrorCode] = frozenset(
    {
        BookingErrorCode.VALIDATION_ERROR,
        BookingErrorCode.SLOT_UNAVAILABLE,
        BookingErrorCode.CLINIC_MISMATCH,
    }
)


async def record_booking_error_event(
    *,
    clinic_id: UUID,
    code: BookingErrorCode | str,
    source: str,
    trace_id: str | None = None,
    tool_name: str | None = None,
) -> None:
    """Increment ``booking_errors_total``; optional Task after Redis threshold (BE5)."""
    if isinstance(code, str):
        code_enum = normalize_booking_error_code(code)
    else:
        code_enum = code
    booking_errors_total.labels(
        code=code_enum.value,
        clinic_bucket=clinic_bucket_label(clinic_id),
        source=source,
    ).inc()
    logger.info(
        "booking_error_event",
        extra={
            "clinic_id": str(clinic_id),
            "code": code_enum.value,
            "source": source,
            "trace_id": trace_id,
            "tool_name": tool_name,
        },
    )
    if not settings.booking_error_attention_enabled:
        return
    if code_enum in _EXCLUDED_FROM_BURST:
        return
    if source == "ai_tool" and tool_name not in _BOOKING_TOOL_NAMES:
        return
    await _maybe_attention_task_for_burst(clinic_id, code_enum, trace_id)


async def _maybe_attention_task_for_burst(
    clinic_id: UUID,
    code: BookingErrorCode,
    trace_id: str | None,
) -> None:
    """Rate-limited Task when repeated errors exceed threshold (BE5)."""
    try:
        from src.infrastructure.database.redis_client import get_redis

        r = await get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.debug("booking_error_attention_skip_redis", extra={"error": str(exc)})
        return

    window = max(60, settings.booking_error_attention_window_seconds)
    threshold = max(1, settings.booking_error_attention_threshold)
    now = int(time.time())
    bucket = now // window
    key = f"berr:{clinic_id}:{code.value}:{bucket}"
    dedup = f"berr_task:{clinic_id}:{code.value}:{bucket}"

    try:
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, window)
    except Exception as exc:  # noqa: BLE001
        logger.debug("booking_error_attention_redis_failed", extra={"error": str(exc)})
        return

    if n < threshold:
        return

    try:
        ok = await r.set(dedup, "1", nx=True, ex=window)
    except Exception as exc:  # noqa: BLE001
        logger.debug("booking_error_attention_dedup_failed", extra={"error": str(exc)})
        return

    if not ok:
        return

    from src.infrastructure.database.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return

    title = f"Повторяющиеся ошибки записи/оплаты: {code.value}"
    desc = (
        f"Автоматически создано при ≥{threshold} событиях `{code.value}` "
        f"за {window}s (клиника {clinic_id}). Проверьте шлюз оплаты / логи."
    )
    try:
        async with AsyncSessionLocal() as session:
            repo: TaskRepository = TaskRepositoryImpl(session)
            svc = TaskService(repo)
            await svc.create_task(
                clinic_id=clinic_id,
                title=title,
                description=desc,
                priority="high",
                source="system",
                attention_kind="booking_error_burst",
                trace_id=trace_id,
            )
            await session.commit()
        booking_error_attention_tasks_created_total.labels(
            clinic_bucket=clinic_bucket_label(clinic_id),
            code=code.value,
        ).inc()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "booking_error_attention_task_failed",
            extra={"clinic_id": str(clinic_id), "code": code.value, "error": str(exc)},
        )
