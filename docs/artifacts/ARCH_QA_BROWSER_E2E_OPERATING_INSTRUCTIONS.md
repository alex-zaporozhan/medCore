# Операционные инструкции: браузерный E2E @QA_ARCH

> **Назначение:** практические шаги для `@DEV` и `@QA_ARCH`.  
> **Канон стратегии:** `docs/artifacts/ARCH_QA_BROWSER_E2E_ENTERPRISE.md`  
> **ADR:** `docs/adr/ADR-006-playwright-browser-e2e.md`  
> **Визуал + PAW + уровни E2E:** `docs/artifacts/ARCH_FRONTEND_VISUAL_UNIFICATION_AND_E2E_ROADMAP.md`

**Статус инструментов в репозитории:** Playwright подключён (`frontend/playwright.config.ts`, `npm run test:e2e`), CI: `.github/workflows/e2e.yml`. Уровень **A** и **B-0** реализованы спеками в `frontend/e2e/`.

---

## 1) Быстрый старт (локально)

1. `cd frontend`
2. Один раз: `npm run test:e2e:install` (Chromium)
3. `npm run build && npm run test:e2e` — поднимется `vite preview` на **4173** (см. `playwright.config.ts`).

Переменная **`BASE_URL`** по умолчанию `http://127.0.0.1:4173`. Для dev-сервера на другом порту (например **3010**):  
`$env:BASE_URL="http://127.0.0.1:3010"; npm run test:e2e` (PowerShell).

---

## 2) Переменные окружения

| Переменная | Пример | Назначение |
|------------|--------|------------|
| `BASE_URL` | `http://127.0.0.1:4173` | Origin SPA (preview или dev) |
| `E2E_API_URL` | `http://127.0.0.1:8000` | Будущие спеки: seed/login через API |
| Секреты учёток | `.env.e2e.local` (не в git) | Только уровень **B-1+** |

Шаблон: `frontend/.env.e2e.example`.

---

## 3) Структура репозитория (факт)

```
frontend/
  e2e/
    smoke-public.spec.ts    # уровень A: лендинг /
    smoke-routes.spec.ts    # уровень B-0: /, /admin/login, /login
  playwright.config.ts
```

Дальше: `e2e/fixtures/`, `e2e/pages/` — по эпику B-1.

---

## 4) Минимальный smoke-набор (приёмка)

| ID | Сценарий | Статус |
|----|----------|--------|
| E2E-SMOKE-01 | Лендинг `/`, CTA | ✓ `smoke-public.spec.ts` |
| E2E-SMOKE-01b | `/admin/login`, `/login` — виден shell | ✓ `smoke-routes.spec.ts` |
| E2E-SMOKE-02 | Логин админа → `AdminLayout` | эпик B-1 (API + seed) |
| E2E-SMOKE-03 | Пациент `/app/*` без 401-петли | эпик B-2 |
| E2E-SMOKE-04 | Критический экран после логина — не белый экран | эпик B + §11 |

---

## 5) Селекторы и устойчивость

1. Предпочитать **`data-testid`** на стабильных контейнерах.
2. Избегать хрупких XPath.
3. Текстовые селекторы — для стабильных копирайтов; учитывать i18n.
4. **Смена темы / дизайн‑токены:** не привязываться к классам Mantine (`.mantine-Button-root`) и к цвету в CSS; для регрессий после смены палитры — см. §6 `docs/artifacts/ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md` (роли, `getByRole`, `data-testid`).

---

## 6) Разбор падений (runbook)

1. HTML report / trace (`npx playwright show-report`).
2. Network в trace: 401/500, CORS, неверный `BASE_URL`.
3. Локально воспроизвести с тем же `BASE_URL`.
4. CI-only: viewport, timezone, параллель.
5. Классификация: баг продукта | flake | хрупкий тест.

---

## 7) Pull Request — чеклист для E2E

- [ ] Journey ID или ссылка на тикет.
- [ ] Маршруты = `ROUTE_PATHS` / техпаспорт §2.
- [ ] Нет секретов в коде.
- [ ] Документация при смене уровня (A / B-0 / B-1).

---

## 8) Ночной / post-merge

- PR: smoke (A + B-0).
- Nightly: расширение + мульти-браузер — по бюджету @OPS.

---

## 9) Cypress / WebDriver

Стратегия слоёв та же; раннер — Playwright по ADR-006.

---

## 10) История версий

| Версия | Изменение |
|--------|-----------|
| 1.0 | Первые операционные инструкции. |
| 1.1 | Синхронизация с ADR-006, порты, команды. |
| 2.0 | Актуализация: Playwright внедрён; уровни A / B-0 / B-1; ссылка на PAW-дорожную карту; убран устаревший текст «не подключён». |

*Текущая версия: **2.0**.*
