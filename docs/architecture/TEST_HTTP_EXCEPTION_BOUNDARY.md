# Тесты и граница HTTP: сырой `HTTPException.detail` vs JSON ответа

> **Назначение (10-Q3 / §28):** явно разделить тесты, которые проверяют **исключение до** глобального handler в `main.py`, и тесты, которые ходят по HTTP и видят **нормализованный** JSON (`code` в `snake_case`, `trace_id` наверху).

## Правило для новых тестов

- **Предпочтительно:** `AsyncClient` + `assert response.json()["code"] == "…"` — контракт как у клиента.
- **Допустимо:** `pytest.raises(HTTPException)` для **unit** зависимостей/хелперов, если исключение **не проходит** через `http_exception_handler`. Тогда в `detail["code"]` используйте **уже каноничный** `snake_case` в коде приложения (как в роутерах после выравнивания omni-кодов).

## Инвентаризация (grep `pytest.raises(HTTPException)`)

| Файл | Назначение |
|------|------------|
| `tests/application/test_organization_entitlement_access.py` | Проверка гейта: `detail["code"] == "entitlement_required"` |
| `tests/api/test_admin_lead_logs_stats.py` | Хелпер `_resolve_chat_to_lead_log_task`: `detail["code"] == "omni_chat_active_lease"` |
| `tests/core/test_http_exception_envelope.py` | Прямой вызов `http_exception_handler` — контракт handler |

Других вхождений `pytest.raises(HTTPException)` в `tests/` на момент заведения документа нет.

## Связанные документы

- [API_PUBLIC_ERROR_CODES.md](./API_PUBLIC_ERROR_CODES.md)
- [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md)
