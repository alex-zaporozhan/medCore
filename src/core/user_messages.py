"""
User-facing messages for expected "empty state" errors.

When the backend fails only because required data is missing (no clinic, no patients, etc.),
we return a clear message so the user knows the error will disappear once they add data.
Rule: no code or commands — plain language only (docs/TESTING_CANON.md §3.1).
"""

EMPTY_DB_NO_CLINIC = (
    "В базе данных нет ни одной клиники. Добавьте клинику в разделе настроек — после этого ошибка исчезнет."
)
