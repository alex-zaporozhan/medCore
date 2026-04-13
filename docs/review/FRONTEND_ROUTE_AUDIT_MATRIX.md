# Матрица маршрутов фронтенда — аудит по слоям

> **Версия:** 2026-04-08  
> **Источник маршрутов:** `frontend/src/routePaths.ts`, `frontend/src/App.tsx`, `frontend/src/__tests__/routePaths.test.ts`.

Ниже — **полный перечень публичных зон** для поэтапной приёмки (тексты, визуал, сквозные действия, связь с API). Для каждой строки в итерации заполняется: статус данных, пустые состояния, баги полей, соответствие [../COPY_STYLE_POLICY_RU.md](../COPY_STYLE_POLICY_RU.md).

Шаблон строки аудита: **маршрут** → владелец/фаза → P0 интерактивы → ссылка на user-doc (если есть).

## Маркетинг и платформа

| Path | Страница / назначение | Примечания |
|------|------------------------|------------|
| `/` | Лендинг | Витрина Business OS |
| `/pricing` | Тарифы / каталог | См. `documentation/USER_DOCS/MARKETING_LANDING.md` |
| `/signup` | Регистрация клиники | |
| `/legal/privacy`, `/legal/terms` | Юридические | |
| `/platform/login`, `/platform/login/mfa` | Вход основателя | |
| `/platform/dashboard`, `/platform/provision-queue` | Кабинет платформы | |
| `/sign-in`, `/login` | Legacy → редиректы | |

## Админка клиники (`/admin/...`)

Сегменты в порядке `ADMIN_SHELL_ROUTE_SEGMENTS` (`routePaths.ts`):

| Сегмент | Path |
|---------|------|
| staff-chat | `/admin/staff-chat` |
| me | `/admin/me` |
| calendar | `/admin/calendar` |
| knowledge | `/admin/knowledge` |
| clinics | `/admin/clinics` |
| services | `/admin/services` |
| schedule | `/admin/schedule` |
| tasks | `/admin/tasks` |
| leads-log | `/admin/leads-log` |
| bookings | `/admin/bookings` |
| prepayment | `/admin/prepayment` |
| waitlist | `/admin/waitlist` |
| recall | `/admin/recall` |
| marketing | `/admin/marketing` |
| retention | `/admin/retention` |
| sales | `/admin/sales` |
| attention | `/admin/attention` |
| reports | `/admin/reports` |
| finance | `/admin/finance` |
| commerce | `/admin/commerce` |
| loyalty | `/admin/loyalty` |
| forms | `/admin/forms` |
| doctors | `/admin/doctors` |
| doctor-schedule | `/admin/doctor-schedule` |
| patients | `/admin/patients` |
| omni-chat | `/admin/omni-chat` |
| omni-channels | `/admin/omni-channels` |
| omni-ai-settings | `/admin/omni-ai-settings` |
| channels | `/admin/channels` |
| integrations | `/admin/integrations` |
| embed | `/admin/embed` |
| rag-kb | `/admin/rag-kb` |
| data-export | `/admin/data-export` |
| omni-vault | `/admin/omni-vault` |
| styling | `/admin/styling` |
| stickers | `/admin/stickers` |
| settings | `/admin/settings` |
| subscription | `/admin/subscription` |
| administrators | `/admin/administrators` |
| payment-gateway | `/admin/payment-gateway` |
| client-reference | `/admin/client-reference` |
| discounts | `/admin/discounts` |
| notification-policy | `/admin/notification-policy` |
| agreements | `/admin/agreements` |
| rights-policies | `/admin/rights-policies` |

Дополнительно: `/admin/login`, `/admin` (дашборд), динамические детали задач и др. — см. дерево в `App.tsx`.

## Пациентское PWA (`/app/...`)

| Path | Назначение |
|------|------------|
| `/app` | Домашняя |
| `/app/feed` | Лента |
| `/app/booking` | Запись |
| `/app/history` | История |
| `/app/loyalty` | Лояльность |
| `/app/forms` | Формы |
| `/app/chat` | Чат |
| `/app/profile` | Профиль |

## Публичные динамические

| Шаблон | Назначение |
|--------|------------|
| `/:clinicSlug/doctors/:doctorSlug` | Публичный профиль врача — `documentation/USER_DOCS/PUBLIC_DOCTOR_PROFILE.md` |
| `/:clinicSlug/sign-in` и цепочка пациента | См. `PatientEntryBoundary` в `App.tsx` |

## Связь с бэкендом

Для проверки «каждый endpoint осмысленно подключён» опираться на [`../../documentation/API_V1_ROUTER_MANIFEST.md`](../../documentation/API_V1_ROUTER_MANIFEST.md) и срезы `documentation/router_surface/`. Отдельно сверять хуки в `frontend/src/hooks/` и вызовы в `frontend/src/api/client.ts`.

Канон приёмки UI: [../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md).
