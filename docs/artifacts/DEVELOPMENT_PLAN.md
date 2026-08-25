# DEVELOPMENT_PLAN — текущий фокус

> **Версия:** 2026-04-02  
> **Правило:** один активный план; завершённые фазы — одна строка `✅` с датой. Детальная история — git.

## Сейчас

- **Волна A ✅ (2026-08-24):** EN-chrome + craft Q1–Q13 закрыты. Отчёты: `QA_REPORT_*`, `QA_TEST_*`, `VISUAL_QA_REPORT_*`. Канон тестов: `npm run test:wave-a` (frontend). Долги: `FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`.  
- Стабилизация **SaaS / Enterprise** на текущей кодовой базе: соблюдение tenant, NFR коробки (`SME_BOX_NFR_CHECKLIST.md`), выравнивание документации с кодом.  
- Следующие крупные эпики — по задаче @LEAD (ссылка на issue/ветку).

## Завершённые этапы (сводка)

- P1 Staff Core / единая лента на `/admin` — по факту в репозитории (см. историю `PRODUCT_OPERATING_CORPUS_2026` и коммиты).

## Решения @LEAD (краткий журнал)

| Дата | Решение |
|------|---------|
| 2026-04-02 | Консолидация `docs/artifacts/`: архитектура — `SAAS_ARCHITECTURE_SPINE_2026.md`, продукт — `PRODUCT_OPERATING_CORPUS_2026.md`; удалены мёртвые промпты и дубли для качества RAG. |
| 2026-04-02 | Корневой `docs/DEVELOPMENT_PLAN.md` сведён к указателю; бэклог направлений перенесён сюда (без ссылок на удалённые файлы). |

## Бэклог направлений (наследие, приоритет задаёт @LEAD)

Свод идей, ранее привязанный к отдельным markdown; детали — issue / эпик / сессия @ARCH.

1. Отчёты по врачам и администраторам (часы, суммы за период).
2. Интеграции: 1С, qMS, Битрикс24 (контракты обмена).
3. Чат, мессенджеры, единая история переписок, задел под AI.
4. Web Push в PWA (VAPID, собственный backend).
5. Универсализация под типы бизнеса (клиника / салон и т.д.).

**Техдолг (зафиксировать до hardening):** мажор `vite-plugin-pwa` 0.21 → 1.x (Workbox/SW) — отдельная задача QA/production. `npm audit` по frontend (prod, high+) закрыт точечными апдейтами (Vite 6.4, Vitest 3.2, react-router-dom 7.18, Playwright 1.62) **без** `npm audit fix --force`. Полный `npm run security:audit:all` — перед релизом. Не поднимать `--force` без решения @LEAD.

---

Reference: `docs/ENGINEERING_PLAN.md` · `docs/artifacts/PRODUCT_OPERATING_CORPUS_2026.md` · `docs/DOC_TOPOLOGY.md`
