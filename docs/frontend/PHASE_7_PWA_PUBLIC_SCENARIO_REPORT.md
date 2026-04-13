# Фаза 7 — сквозные сценарии PWA и публичная витрина (критерий C5)

> **Версия:** 2026-04-09  
> **Мастер-план:** [`MASTER_FRONTEND_EXECUTION_PLAN.md`](./MASTER_FRONTEND_EXECUTION_PLAN.md) · **критерии:** [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md) (C5)

## Что делаете вы лично (фаза 7)

Колонки **Статус** и **Gap** в атрице ниже — не вывод из CI; это **ваша оценка** после живого прогона (или доверия к отчёту QA):м

1. Выберите сценарии, критичные для ближайшего релиза (можно не все S1–S13).
2. Выполните шаги в браузере с реалистичными данными тестовой клиники (вход пациента, запись, витрина, публичный профиль врача и т.д.).
3. Обновите в этом файле **Статус** (OK / PARTIAL / GAP) и при необходимости **Gap / примечание**.
4. Обновите дату в шапке файла (`> **Версия:** …` или отдельная строка «Последняя ревизия матрицы: …»).

Агент может предложить черновик статусов по коду и паспортам, но **подтверждение поведением в UI** остаётся за человеком.

## Назначение

Единый **отчёт-матрица**: сценарий → маршруты → паспорта → статус → gap. Обновлять при смене `App.tsx` / `routePaths.ts` или после аудита; не дублировать тело паспортов — только трассировка.

## Легенда статуса

| Статус | Смысл |
|--------|--------|
| **OK** | Сквозной сценарий воспроизводим; API и состояния по паспорту согласованы с кодом на момент версии строки |
| **PARTIAL** | Работает частично или зависит от данных клиники / энтайтлментов |
| **GAP** | Известный разрыв (см. колонку Gap / паспорт) |

## Матрица сценариев

| ID | Сценарий | Ключевые маршруты | Паспорта (якоря) | Статус | Gap / примечание |
|----|-----------|-------------------|------------------|--------|------------------|
| S1 | Пациент выбирает клинику и входит | `/c/:clinicSlug`, sign-in, редиректы | [`patient-sign-in-chain.md`](./pages/patient-sign-in-chain.md) | PARTIAL | Зависит от slug клиники и политики patient auth |
| S2 | Запись на приём (PWA) | `/app/booking`, зеркало `/c/.../app/booking` | [`app-booking.md`](./pages/app-booking.md), [`booking-success.md`](./pages/booking-success.md) | OK | Сверять оплату/успех с [`docs/product_state/BACKEND_PASSPORT.md`](../product_state/BACKEND_PASSPORT.md) при изменениях платежей |
| S3 | Лента и контент после входа | `/app/feed` | [`app-feed.md`](./pages/app-feed.md) | PARTIAL | Контент зависит от данных клиники |
| S4 | История визитов | `/app/history` | [`app-history.md`](./pages/app-history.md) | PARTIAL | — |
| S5 | Лояльность / бонусы | `/app/loyalty` | [`app-loyalty.md`](./pages/app-loyalty.md) | PARTIAL | — |
| S6 | Формы | `/app/forms` | [`app-forms.md`](./pages/app-forms.md) | PARTIAL | — |
| S7 | Чат пациента | `/app/chat` | [`app-chat.md`](./pages/app-chat.md) | PARTIAL | — |
| S8 | Профиль | `/app/profile` | [`app-profile.md`](./pages/app-profile.md) | PARTIAL | — |
| S9 | Домашняя точка PWA | `/app` | [`app-home.md`](./pages/app-home.md) | OK | — |
| S10 | OAuth callback | `/oauth/result` | [`app-oauth-result.md`](./pages/app-oauth-result.md) | PARTIAL | Зависит от провайдера |
| S11 | Публичный профиль врача | `/:clinicSlug/doctors/:doctorSlug` | [`public-doctor-profile.md`](./pages/public-doctor-profile.md) | OK | Связка с админкой: справочник врачей / публичные поля — см. [`admin-doctors.md`](./pages/admin-doctors.md) |
| S12 | Витрина: цены и оффер | `/pricing`, `/` | [`marketing-pricing.md`](./pages/marketing-pricing.md), [`marketing-landing.md`](./pages/marketing-landing.md) | OK | Не смешивать с операционным UI |
| S13 | Админ: услуги и цены для витрины | `/admin/services` | [`admin-services.md`](./pages/admin-services.md) | PARTIAL | Сквозняк «админка → публичная цена» требует сверки API витрины и админских справочников |

## PWA-технические точки (не сценарии, а инфраструктура)

| Тема | Где смотреть | Заметка |
|------|--------------|---------|
| Manifest / installability | `frontend/` (Vite PWA plugin), `manifest.webmanifest` в билде | После смены иконок/scope — smoke в Chrome |
| Офлайн | Service worker (генерация в build) | Не заявлять полный офлайн для админки без отдельного тест-плана |

## Критерий «готово» по фазе 7

- Таблица выше актуальна (дата в шапке отчёта обновлена при смене сценариев).
- Для строк **GAP** есть либо исправление в коде, либо явная запись в паспорте страницы (gap scan).
- После изменения маршрутов: `python scripts/gen_frontend_page_passport_stubs.py verify`.

## Связанные файлы

- [`pages/README.md`](./pages/README.md) — полная матрица Path → паспорт.  
- [`../product_state/FRONTEND_PASSPORT.md`](../product_state/FRONTEND_PASSPORT.md) — срез маршрутов SPA.
