# Поверхность тестов (связь с API и UI)

> **Версия:** 2026-04-02 | **Назначение:** единая точка входа для вопросов «где тесты» и «что покрыто роутером».

## Backend (pytest)

| Зона | Путь | Комментарий |
|------|------|-------------|
| API / HTTP | `tests/api/` | Основной корпус против FastAPI |
| Безопасность | `tests/security/` | Чаты, RBAC и др. |
| Сервисы | `tests/services/` | Прикладная логика без полного HTTP-стека |
| Прочее | `tests/application/`, `tests/core/`, `tests/unit/` | По имени модуля |

**Связка с роутером:** для каждого модуля `src/api/v1/routers/<name>.py` откройте блок **`## N. \`<name>\``** в **[router_surface/INDEX.md](./router_surface/INDEX.md)** — там перечислены pytest-файлы (имя файла + импорт из `src.api.v1.routers`).

## E2E

- Каталог: `tests/e2e/` (Playwright).
- Регламент запуска: [E2E_TESTING.md](./E2E_TESTING.md).

## Frontend

| Тип | Где искать |
|-----|------------|
| Vitest / RTL | `frontend/src/**/__tests__/**/*.test.tsx` (и рядом с страницами) |
| Playwright (если настроен отдельно от корневого e2e) | конфиги и каталоги в `frontend/` |

Поиск по фиче: `rg "<segment>" frontend/src --glob "*.ts*"` (сегмент из `routePaths.ts`).

## Что делать при пробелах

Если INDEX показывает «автопокрытие отсутствует» — в USER_DOCS и питче **не** утверждать наличие регрессионных тестов; завести задачу на тест или пометить как ручную проверку.

---

Reference: [DEVELOPMENT.md](./DEVELOPMENT.md) · [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md)
