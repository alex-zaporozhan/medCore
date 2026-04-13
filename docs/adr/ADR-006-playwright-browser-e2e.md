# ADR-006 — Браузерный E2E: Playwright, CI и логистика стека Dental Booking

**Status:** accepted  
**Date:** 2026-03-21  
**Context:** запрос @QA_ARCH на фиксацию инструмента и контура CI; продуктовые детали E2E — `docs/TESTING_CANON.md` и код `e2e/`.

## Decision

1. **Инструмент:** **Playwright Test** (`@playwright/test`) — единый раннер браузерного E2E для SPA (`frontend/`). Cypress/WebDriver не вводятся параллельно без нового ADR.

2. **Расположение в репозитории**
   - Конфиг: `frontend/playwright.config.ts`
   - Спеки: `frontend/e2e/**/*.spec.ts`
   - Скрипты: `npm run test:e2e`, `npm run test:e2e:install` (Chromium)
   - Пример переменных: `frontend/.env.e2e.example`

3. **Порты и окружения (логистика сайта)**
   | Сервис | Типичный порт (локально) | Примечание |
   |--------|---------------------------|------------|
   | Vite dev | `5175` | `frontend/vite.config.ts` (`server.port`) |
   | Vite preview (E2E) | `4173` | `playwright.config.ts` + `vite preview` |
   | API (uvicorn на хосте) | `8000` | прокси Vite: `/api` → `http://localhost:8000` |
   | API (docker-compose `backend`) | `8010` → 8000 в контейнере | см. `docker-compose.yml` |
   | Пользовательский dev | иной (напр. `3010`) | задаётся вручную; E2E по умолчанию не зависит от dev-порта |

   **BASE_URL** для Playwright: `http://127.0.0.1:4173` (preview после `npm run build`). Публичный smoke **не требует** бэкенда.

4. **Уровни сценариев**
   - **Уровень A:** лендинг `/` без API (`e2e/smoke-public.spec.ts`).
   - **Уровень B-0:** shell публичных маршрутов без сессии — `/`, `/admin/login`, `/login` (`e2e/smoke-routes.spec.ts`).
   - **Уровень B-1 (эпик):** Postgres/Redis/API (docker-compose или CI `services`), seed, логин админа → `AdminLayout`, сценарии по `ROUTE_PATHS` §2.
   - **Уровень B-2:** пациентский поток (SMS/код) — тестовый Redis/моки по согласованию с бэкендом.
   - **Уровень C:** полный регресс journey — при готовности фикстур и бюджета CI.

   Дорожная карта PAW и визуала: `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md`, `docs/artifacts/BUSINESS_ROUTES.md`.

5. **CI:** workflow `.github/workflows/e2e.yml` — build фронта, установка Chromium, `npm run test:e2e`. Уровни A + B-0 **не требуют** бэкенда. B-1+ — отдельный job или матрица.

6. **Связь с техпаспортом:** новые маршруты в E2E дублируют канон `frontend/src/routePaths.ts` и `docs/artifacts/BUSINESS_ROUTES.md`.

## Consequences

- Разработчики запускают локально: `npm run build && npm run test:e2e` (preview поднимается автоматически).
- Расширение на админку/пациента требует секретов тестовых учёток и стабильного API — отдельные задачи, не блокирующие merge smoke уровня A.
- Дублирование с Vitest: E2E не заменяет юнит-тесты; пирамида — см. enterprise-док по E2E.

## Связанные файлы

- `frontend/playwright.config.ts`, `frontend/e2e/`
- `.github/workflows/e2e.yml`
- `docs/TESTING_CANON.md`
