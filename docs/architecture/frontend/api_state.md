# API-клиент и состояние запросов

## Назначение

Транспорт HTTP и ключи кэша клиента без бизнес-логики в слое fetch.

## Как это работает (запрос и состояние)

1. **URL:** все вызовы идут на относительный базовый префикс `API_BASE` = `/api`; далее путь продолжается как на бэкенде (`/v1/...`). Отдельного хоста в коде клиента нет — его задаёт деплой или Vite proxy.
2. **Авторизация:** перед fetch подмешивается заголовок `Authorization: Bearer ...` из `getAdminToken()` или `getPatientToken()` (`client.ts`). Для админских маршрутов с scope клиники UI держит `adminClinicId` в `localStorage` (`getBoundAdminClinicId` читает storage или декодирует payload JWT без проверки подписи — доверие после успешного логина).
3. **Идемпотентность и отладка:** генерируется `X-Request-Id` (UUID или fallback) для корреляции с логами бэкенда.
4. **Ошибки:** тело ответа разбирается в `parseFastApiErrorBody`: поддерживается единый envelope с `code`, `trace_id`, массив ошибок 422. Для 401 вызывается `shouldClearPatientSessionOn401` — сброс пациентской сессии зависит от пути и того, был ли пациентский токен в запросе (избегаем ложных сбросов).
5. **TanStack Query:** хуки на страницах используют ключи из `queryKeys.ts`; инвалидация после мутации должна ссылаться на те же кортежи, иначе UI «залипнет» на старом кэше. Провайдер и дефолты клиента заданы в `frontend/src/main.tsx` (`QueryClientProvider` вокруг `App`, комментарий в файле про выравнивание с админскими запросами).

## Точки входа

- `frontend/src/api/client.ts` — константа `API_BASE` со значением `/api`, `API_STORAGE_KEYS`, Bearer для админа и пациента, разбор ошибок, заголовок запроса, правила 401 (см. комментарии в файле).
- `frontend/src/api/types.ts` — типы тела ошибок и общие DTO для фронта.
- `frontend/src/queryKeys.ts` — фабрика ключей TanStack Query по доменам: клиники, staff collab, задачи, омни и др.
- Страницы подключают `queryKeys` и функции из `client.ts` или из модулей под `frontend/src/api/`.

## Поток

Браузер обращается к относительному префиксу `/api`; в dev прокси Vite перенаправляет на backend (см. `00_system_runtime.md`). Токены хранятся в `localStorage` по ключам из `API_STORAGE_KEYS`.

## Зависимости

TanStack Query: провайдер в `frontend/src/main.tsx` (`QueryClientProvider`).

## Статус

- Единый префикс `/api`: реализовано.
- Инварианты клиента: частично, тест `frontend/src/__tests__/apiClientShellInvariants.test.ts`.
- Ключи query: тест `frontend/src/__tests__/queryKeys.test.ts`.

## Непонятное

Полный перечень эндпоинтов по каждому хуку здесь не ведётся; смотреть импорты в `admin/pages` и `app/pages`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** токены в `localStorage` — классическая поверхность XSS; для Enterprise часто требуются httpOnly cookies + CSRF-политика (сейчас — Bearer в JS).
- **Средние риски:** `parseAdminJwtClinicId` декодирует payload без проверки подписи (доверие после логина) — осознанный компромисс, но нужен контроль единственного источника истины.
- **Формально / недоделано:** нет встроенного circuit breaker на фронте для каскадных сбоев API.
- **Рекомендуемые доработки:** security review хранения сессий; опционально BFF для чувствительных потоков.

### Соответствие фактам (проверка)

- `client.ts`, `main.tsx`, `API_STORAGE_KEYS`, `shouldClearPatientSessionOn401` — по чтению файлов.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** Bearer в `localStorage` — поверхность XSS; компрометация JS = компрометация сессии админа/пациента.
- **Что усилить:** contract-тесты ответов API для платежей и ошибок 401/403.
- **С нуля:** BFF с httpOnly-cookie — при требованиях security review.
- **БД:** не применимо.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§4).
