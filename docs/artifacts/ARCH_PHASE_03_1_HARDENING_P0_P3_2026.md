# ARCH_PHASE_03_1_HARDENING_P0_P3_2026 — P3.1 Hardening / Gate closure (@ARCH)

> **Назначение:** промежуточная волна после P3, когда на QA_ARCH/CI всплывают критичные “контрактные” дыры P0–P3.
> Цель P3.1: стабилизировать контрактный слой (RBAC/tenant/context/errors/PII/устойчивость) и только потом продолжать к `P4` и выше.

---

## 1. Что в P3.1 обязательно

Закрываются только те пробелы, которые влияют на корректность/безопасность/жизнеспособность базового контура P0–P3:

## 2. Ключевые acceptance criteria (минимум)

1. `scripts/audit_rbac_endpoints.py --check` возвращает `exit code 0`.
2. `pytest` проходит без падений на security/core/contract тестах (минимальный набор):
   - `tests/core/test_request_context.py`
   - `tests/core/test_ai_sanitizer.py`
   - `tests/application/test_sec_rbac_router_permissions_inventory.py`
   - (опционально расширить на ближайшие API/RBAC тесты, если QA_ARCH требует)
3. `get_request_context` не ломает dependency injection (FastAPI) и допускает fallback-сценарий без token’ов.
4. `AiSanitizer` при `allow_personal_data=False` маскирует телефоны/почту, но **не** ломает “стабильные” AI tokens формата `PATIENT#<uuid>` / `BOOKING#<uuid>`.
5. `ErpVisitNodeService` в legacy-пути не “роняет” ноду — исключения приводятся к стабильному `ErpVisitNodeResult` (DTO контракт), а не к падению выполнения.

---

## 3. Code “anchors” (куда смотреть)

- `src/api/v1/dependencies.py` — `get_request_context` (fallback и совместимость со статическим/инъекционным вызовом).
- `src/core/ai_sanitizer.py` — `PHONE_RE` / порядок маскирования относительно tokens.
- `src/application/services/erp_node_service.py` — legacy fallback: обработка `Exception` в node-level контракте.
- `docs/artifacts/sec_rbac_router_permissions.txt` — inventory: должен соответствовать текущему коду (`require_permissions(...)` в admin routers).

---

## 4. Быстрый “re-run” сценарий (как перезапустить контур)

1. Убедиться, что inventory RBAC актуален:
   - `python scripts/audit_rbac_endpoints.py --check`
2. Прогнать минимальный pytest набор из §2.2.
3. Если что-то упало/несовпало — правки в “anchors” из §3, затем повторить п.1–2.
4. После зелёных гейтов: продолжать стандартно по `P4 → P5 → P6 → P7`.

---

## 5. Текущий статус (для истории)

На текущем состоянии репозитория критичные гейты P0–P3 были закрыты (request-context, AI sanitizer token preserve, RBAC inventory, устойчивость legacy ERP node).

---

## 6. История

| Дата | Изменение |
|------|-----------|
| 2026-03-25 | Создан артефакт P3.1 для повторного запуска hardening/acceptance P0–P3 |

