# Пациентское приложение (`/app`)

## Назначение

Личный кабинет пациента: домашняя лента, запись, история, лояльность, формы, чат с клиникой, профиль, опционально **витрина магазина** (`/app/store`).

## Как это работает

1. **Контекст:** `PatientAuthProvider` держит состояние входа; дочерние страницы в `app/pages` запрашивают данные с Bearer пациентского JWT.
2. **Маршруты:** пути фиксированы в `ROUTE_PATHS.patient` (`/app`, `/app/booking`, `/app/store`, `/app/chat`, …); при смене их нужно синхронно обновлять дерево в `App.tsx`.
3. **Связь с API:** те же функции из `client.ts`, что и для админки, но токен выбирается по контексту запроса; 401 может очистить storage по правилам `shouldClearPatientSessionOn401` (важно для оплаты и смежных эндпоинтов не только `/v1/patient/*`).
4. **Изоляция данных:** на бэкенде пациент идентифицируется сущностью `Patient`; `RequestContext.clinic_id` для пациента в `dependencies.py` — `None`, поэтому проверки «свой пациент / своя клиника» выполняются в сервисах, а не одним полем контекста.

## Точки входа

- Страницы: `frontend/src/app/pages/` — `HomePage`, `FeedPage`, `BookingWizardPage`, `BookingSuccessPage`, `HistoryPage`, `LoyaltyPage`, `FormsPage`, `ChatPage`, `ProfilePage`, `StorePage` (витрина Commerce при `patient_store_visible`), `LoginPage`, `OAuthResultPage`.
- Оболочка: `frontend/src/app/layouts/AppLayout.tsx`.
- Аутентификация: `frontend/src/contexts/PatientAuthContext.tsx` (согласована с `client.ts` и 401).

## Маршруты

Канон в `ROUTE_PATHS.patient` внутри `frontend/src/routePaths.ts`.

## Магазин (витрина Commerce в PWA)

Канон по слоям и публичному API: [domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md](../domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md). Кратко: вкладка «Магазин» в нижней/десктоп-навигации появляется, если у выбранной клиники `patient_store_visible`; данные карточек — `GET /api/v1/public/clinics/{clinic_id}/commerce/vitrine` (без Bearer). Настройка заголовка секции и флага — в админке `/admin/commerce`.

## Статус

| Аспект | Статус |
|--------|--------|
| Маршруты под `/app` | Реализовано в `App.tsx` |
| Связь с patient API | Через тот же `API_BASE` и patient token |
| Витрина `/app/store` | Публичный GET витрины + флаги клиники; см. план Commerce |

## Непонятное

E2E-покрытие всех patient-сценариев см. `tests/e2e/` и `08_tests_matrix.md`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** смешение patient token с платёжными путями и правилами 401 — регрессии дают «тихую» потерю сессии; покрывать e2e.
- **Средние риски:** доступ к данным пациента зависит от серверных проверок, не от `clinic_id` в JWT ([backend/domain_layer.md](../backend/domain_layer.md)).
- **Формально / недоделано:** полнота a11y и локализации не оценивается в этом документе.
- **Рекомендуемые доработки:** сквозные тесты «login → booking → payment» в активном CI.

### Соответствие фактам (проверка)

- `PatientAuthProvider`, `app/pages`, `client.ts` — статическое чтение.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** правила `shouldClearPatientSessionOn401` при оплате — ошибка даёт «тихий» сброс сессии; нужны e2e.
- **Что усилить:** сквозные тесты patient → payment webhook (через API/e2e).
- **С нуля:** не применимо.
- **БД:** сервер определяет доступ к данным пациента без `clinic_id` в JWT.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§2.3).
