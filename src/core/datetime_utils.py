"""
Единая работа с временем в проекте. Все серверные метки времени — UTC.

Правила:
- Хранилище: в БД колонки бывают TIMESTAMP WITH TIME ZONE (TIMESTAMPTZ) и
  TIMESTAMP WITHOUT TIME ZONE (naive). Для TIMESTAMPTZ передаём aware UTC
  (utc_now()). Для naive-колонок передаём naive UTC (utc_now_naive()), чтобы
  не зависеть от session timezone.
- Внешние API (Telegram, ЮKassa, 1C, CSV, и т.д.): при передаче дат/времени
  используем ISO 8601 с суффиксом Z (UTC), например to_iso8601_utc(dt).
- Логи, сериализация в JSON: UTC, формат ISO 8601 с Z.
- Celery: уже настроен timezone="UTC", enable_utc=True.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Текущее время в UTC (timezone-aware). Для записи в TIMESTAMPTZ и для сравнений."""
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """Текущее время в UTC без tzinfo (naive). Для колонок TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_iso8601_utc(dt: datetime | None) -> str | None:
    """Сериализация в ISO 8601 с суффиксом Z (для API и JSON)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
