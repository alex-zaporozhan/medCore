"""
User-facing messages for expected "empty state" errors.

When the backend fails only because required data is missing (no clinic, no patients, etc.),
we return a clear message so the user knows the error will disappear once they add data.
Rule: no code or commands — plain language only for user-facing strings.
"""

EMPTY_DB_NO_CLINIC = (
    "В базе данных нет ни одной клиники. Добавьте клинику в разделе настроек — после этого ошибка исчезнет."
)

# ADR-012: platform subscription refunded / billing revoked for this organization.
ADMIN_ORG_PLATFORM_BILLING_REVOKED = (
    "Доступ приостановлен: подписка платформы отозвана (возврат платежа)."
)
