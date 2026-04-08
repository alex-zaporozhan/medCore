"""YooKassa Payment semantics for contour B (`GET /v3/payments/{{id}}`).

Official OpenAPI **PaymentStatus** enum (YAML `PaymentStatus`): ``pending``,
``waiting_for_capture``, ``succeeded``, ``canceled`` — см.
https://yookassa.ru/developers/api/yookassa-openapi-specification.yaml

Поле ``refunded_amount`` на объекте Payment описывает возвраты; при полном возврате
часто сохраняется ``status=succeeded`` с ``refunded_amount`` ≥ ``amount``.

Строки вроде ``refunded`` в ``status`` в строгом enum не перечислены; в интеграциях и
логах иногда встречаются расширения — держим алиасы как **defensive** (и тесты).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# Не входят в OpenAPI enum, но встречаются в тестах/логах — оставляем для отзыва биллинга.
_REFUND_REVOCATION_STATUS_ALIASES = frozenset(
    (
        "refunded",
        "chargeback",
        "charged_back",
        "disputed",
        "dispute_lost",
    )
)


def _decimal_amount(obj: Any) -> Decimal | None:
    if not isinstance(obj, dict):
        return None
    raw = obj.get("value")
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None


def yookassa_payment_payload_indicates_full_refund_revocation(data: dict[str, Any]) -> bool:
    """
    Нужно ли применить ADR-012 revocation (refund/chargeback-подобный исход).

    1) Алиасные статусы (см. модуль).
    2) Канон по API: ``status=succeeded`` и ``refunded_amount`` ≥ ``amount`` (полный возврат).
    """
    status = (data.get("status") or "").strip().lower()
    if status in _REFUND_REVOCATION_STATUS_ALIASES:
        return True
    if status != "succeeded":
        return False
    amt = _decimal_amount(data.get("amount"))
    ref = _decimal_amount(data.get("refunded_amount"))
    if amt is None or ref is None or amt <= 0:
        return False
    return ref >= amt
