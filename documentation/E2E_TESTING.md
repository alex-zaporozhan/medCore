# E2E (Playwright)

> **Версия:** 2026-04-02  
> **Источник в коде:** `frontend/playwright.config.ts`, `frontend/e2e/`, `frontend/package.json`, при необходимости `.github/workflows/` для CI.

## Назначение

Сквозные браузерные проверки фронтенда на **Chromium** после production-сборки (preview-сервер).

## Конфигурация

- Файл: **`frontend/playwright.config.ts`**.  
- Каталог тестов: **`frontend/e2e/`**.  
- По умолчанию **`baseURL`**: `http://127.0.0.1:4173` (или `process.env.BASE_URL`).  
- Локально `webServer` поднимает **`npm run preview`** на `127.0.0.1:4173` (если не задан `E2E_EXTERNAL_BASE_URL`).  
- В CI обычно сначала **`npm run build`**, затем прогон Playwright — см. workflow репозитория.

## Переменные окружения

Пример без секретов: **`frontend/.env.e2e.example`** (копировать в `.env.e2e.local`, не коммитить).  
Для сценариев с живым API в будущем может понадобиться, например, `E2E_API_URL` — комментарии в том же файле.

## Команды

Из каталога **`frontend`**:

```bash
npm run test:e2e:install   # один раз: браузер Chromium
npm run build
npm run test:e2e
```

Сборка обязательна перед preview, если вы не переиспользуете уже собранный `dist`.

## Связь с документацией

Фиксированные маршруты для регрессии — **`ALL_PUBLIC_APP_PATHS`** в `frontend/src/routePaths.ts`; полный канон зон и **динамические** шаблоны (например профиль врача) — **`documentation/PRODUCT_KNOWLEDGE_BASE.md` §5–5.4**.

## См. также

- [DEVELOPMENT.md](./DEVELOPMENT.md) — порты API и фронта, тестовая БД
