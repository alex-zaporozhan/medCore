# Аудит RAG: добросовестность @LEAD и доработки @QA_ARCH

> **Версия:** 2026-04-03  
> **Роль:** @QA_ARCH — проверка полноты, противоречий и операционной пригодности слоя S и канона.

---

## 1. Вердикт по работе @LEAD

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| Разделение фактов и «доработок» | ✅ | Отдельный `RAG_NECESSARY_IMPROVEMENTS.md` соблюдён. |
| Шесть отдельных паспортов | ✅ | Явные файлы, вход через `INDEX.md`. |
| Привязка к коду | ✅ | Роутеры, `App.tsx`, compose, стек из `pyproject`/`package.json`. |
| Скромность / пробелы | ⚠️ было | Не были синхронизированы `RAG_CANON.md`, `DOC_TOPOLOGY.md`, политика, README; в коде остались мёртвые ссылки на `documentation/*.md`. Исправлено в том же волне @QA_ARCH. |
| Учёт удаления `artifacts/` | ✅ | В `RAG_NECESSARY_IMPROVEMENTS.md` зафиксировано намерение; канон ранее всё ещё тянул слой W — **переписан**. |

---

## 2. Что сделано @QA_ARCH (этот проход)

1. **`docs/RAG_CANON.md`** — переписан: приоритет код → `product_state` → P; слой W и `documentation/` помечены как отсутствующие; таблица маршрутизации вопросов ведёт в конкретные паспорта.  
2. **`docs/DOC_TOPOLOGY.md`** — переписан под фактическое дерево; убраны обязательные `artifacts/`, `documentation/`.  
3. **`DOCUMENTATION_POLICY.md`** — `docs/` + `product_state`; запрет ссылок на `*.md` из `src/` и `frontend/src/`.  
4. **`README.md`** — актуальные входы, без `documentation/`.  
5. **Мёртвые ссылки в коде** — удалены все упоминания `*.md` и `documentation/` в прикладных исходниках, тестах, конфигах фронта; скрипты переведены на пути под `docs/product_state/`.  
6. **CI** — workflow проверки ссылок переведён с `documentation/` на `docs/`.  
7. **Deploy-as-code** — комментарии в Grafana JSON и Prometheus указывают на существующие `docs/RUN_SERVICES.md` / `deploy/grafana/README.md`.  
8. **Baseline RBAC** — инвентарь прав перенесён в `docs/product_state/baselines/rbac_router_permissions.txt` (генерация: `python scripts/audit_rbac_endpoints.py --write`).  
9. **Автоген поверхности API** — вывод скрипта: `docs/product_state/generated/router_surface/INDEX.md` (без ссылок на несуществующие manifest из шаблона).

---

## 3. Правило «нет ссылок на markdown в прикладном коде»

**Зачем:** ссылки вида `documentation/FOO.md` в комментариях быстро гниют и провоцируют галлюцинации RAG («документ существует»).

**Норма:**

- Канон маршрутов SPA — **`frontend/src/routePaths.ts`**, **`frontend/src/App.tsx`**.  
- Канон API — **`src/api/v1/router.py`**, паспорт **`BACKEND_PASSPORT.md`** (читается снаружи кода).  
- Редакция Box/Enterprise — **`src/core/edition.py`**, **`frontend/src/config/edition.ts`**, переменные в **`.env.example`**.  
- RBAC-коды — **`src/application/rbac_matrix.py`**, baseline в **`docs/product_state/baselines/`**.  
- Тема UI — **`frontend/src/theme.ts`**, **`frontend/src/index.css`**.

**Исключения:** корневой `README`, всё под `docs/`, workflow, сообщения линтеров **могут** называть файлы политики, если это не прикладной runtime-код (по желанию команды — в `eslint-restricted-ui-imports.mjs` сообщения без имён `.md`).

---

## 4. Рекомендации на следующие спринты

| Приоритет | Действие |
|-----------|----------|
| P1 | Прогнать `python scripts/generate_router_surface_docs.py` и закоммитить `docs/product_state/generated/router_surface/INDEX.md` при следующем изменении роутеров. |
| P1 | Включить в pre-commit или CI проверку `grep` на `\documentation/` и на `\.md` внутри `src/` и `frontend/src/` (с allowlist для редких исключений). |
| P2 | OpenAPI snapshot в CI → артефакт или файл под `product_state/generated/`. |
| P2 | Смягчить тело ответа `GET /health/replica` при ошибке (без утечки `str(exc)` наружу). |

---

## 5. Связанные файлы

- [INDEX.md](./INDEX.md)  
- [RAG_NECESSARY_IMPROVEMENTS.md](./RAG_NECESSARY_IMPROVEMENTS.md)  
- [../RAG_CANON.md](../RAG_CANON.md)

---

Reference: grep по репозиторию на `documentation/` и `\.md` в `src/`, `frontend/src` после правок.
