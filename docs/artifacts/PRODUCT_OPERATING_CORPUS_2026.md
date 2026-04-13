# PRODUCT_OPERATING_CORPUS_2026 — продукт, дорожная карта, операционный контекст

> **Версия:** 2026-04-02  
> **Слой:** W (ориентир для @LEAD, @BIZ, @QA_ARCH, @SCRIBE; **не** замена `docs/product_state/` после прогона @SCRIBE).  
> **RAG:** один файл вместо разрозненных `MASTER_*`, `PRODUCT_*`, `LEAD_*` планов в корне artifacts.

---

## 1. Принципы продукта

1. **Одна кодовая база**: издания Box и Enterprise через RBAC, конфиг клиники, feature flags — без форка.  
2. **Социальный слой сотрудников** (лента, чат, календарь, kanban) — общий для Box и Enterprise.  
3. **Контуры**: персонал / клиент (омниканал + PWA) / маркетинг — разные поверхности, единый RBAC.  
4. **Коробка**: простая аналитика без LTV/ROI; расширенная аналитика и часть лояльности — Enterprise.  
5. **AI в коробке**: в основном ассистент в чате с клиентом; тяжёлая RAG-аналитика — не обязательна для v1 Box.

---

## 2. Карта фаз (сводка)

| Фаза | Содержание |
|------|------------|
| P0 | NFR baseline, CI, DR, RBAC-аудит критичных путей |
| P1 | Staff: лента `/admin`, мессенджер, календарь, kanban |
| P2 | Клиенты и расписание: слоты, карточки, запись |
| P3 | Omni-чат как рабочее место админа |
| P4 | Маркетинг Box: recall, скидки, баннеры PAW |
| P5 | Аналитика и финансы Box |
| P6 | Владелец, гранулярный RBAC |
| P7 | Enterprise: лиды, retention, расширенные сценарии |
| Box cut | Заморозка scope, профиль BOX, приёмка по SME NFR |

Архитектурный каркас фаз и модулей: **`docs/artifacts/SAAS_ARCHITECTURE_SPINE_2026.md`**.

---

## 3. Маршруты и навигация

- **HTTP API и SPA:** единая актуальная карта — **`docs/artifacts/BUSINESS_ROUTES.md`** (источник правды при расхождении — `src/api/v1/router.py`, `frontend/src/App.tsx`).  
- IA/RBAC уровня «какие экраны и роли» при необходимости восстанавливаются @SCRIBE в `docs/product_state/PRODUCT_KNOWLEDGE_BASE.md` из кода и этого корпуса.

---

## 4. NFR коробки и Enterprise

- **Минимум для коммерческой коробки:** `docs/artifacts/SME_BOX_NFR_CHECKLIST.md`.  
- **Полный scorecard:** `docs/NONFUNCTIONAL_SCORECARD.md`.  
- Программа 8.5+ и чеклисты «из коробки в SaaS» — по мере появления фиксировать **короткими** дополнениями в SME/scorecard, не отдельной «полкой» из десятков файлов.

---

## 5. Бизнес-логика и рынок

- Стабильные правила для @DEV: **`docs/artifacts/BUSINESS_LOGIC.md`**.  
- Конкурентный контекст и KILL SIGNAL: **`docs/artifacts/MARKET_AUDIT.md`** (обновляет @BIZ по триггеру).

---

## 6. Текущий фокус разработки

- **`docs/artifacts/DEVELOPMENT_PLAN.md`** — один активный план; завершённые фазы — одна строка со статусом.

---

## 7. Решения и история

- Журналы волн и старые QA-бэклоги удалены из репозитория как шум для RAG; при необходимости — **git history**.  
- Новые зафиксированные решения @LEAD: раздел в конце `DEVELOPMENT_PLAN.md` или ADR в `docs/adr/` (если заведена папка).

---

Reference: `docs/LEAD_PRODUCT_GATE_PROTOCOL.md` · `docs/ENGINEERING_PLAN.md` · `docs/artifacts/BUSINESS_ROUTES.md` · `docs/artifacts/SAAS_ARCHITECTURE_SPINE_2026.md`
