# Каталог паспортов страниц SPA

> **Версия:** 2026-04-10 (матрица маршрутов; срез паспортов v2 по зонам — [`V2_ZONE_TRACKER.md`](./V2_ZONE_TRACKER.md))  
> **Мастер-план фаз @QA_ARCH:** [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md) (порядок эпиков + **когда запускать** `gen_frontend_page_passport_stubs.py`).  
> **Критерии:** [`../PAGE_PASSPORT_CRITERIA.md`](../PAGE_PASSPORT_CRITERIA.md) · **канон:** [`../FRONTEND_ARCHITECTURE_CANON.md`](../FRONTEND_ARCHITECTURE_CANON.md) · **слои SPA:** [`../FRONTEND_ENGINEERING_CONVENTIONS.md`](../FRONTEND_ENGINEERING_CONVENTIONS.md)

**Якорь списка страниц для паспортов:** статические path — `buildDerivedPublicAppPaths()` и `ALL_PUBLIC_APP_PATHS` в [`frontend/src/routePaths.ts`](../../../frontend/src/routePaths.ts); шаблоны с параметрами и цепочки (`/admin/tasks/:taskId`, `/:clinicSlug/doctors/:doctorSlug`, `/c/:clinicSlug/...`) — в [`frontend/src/App.tsx`](../../../frontend/src/App.tsx). Перечень экранов **не** выводить из бэкенд-агрегатора `include_router` в `src/api/v1/router.py`: для паспорта API нужен как журнал вызовов из хуков страницы (`/v1/...`), а не как список URL SPA.

**Скрипты:** `python scripts/gen_frontend_page_passport_stubs.py <команда>` — `generate`, `verify`, `print-matrix`, `migrate-placeholders`; **`python scripts/enrich_page_passport_manifest.py`** — машинный блок `AUTO_MANIFEST` во всех паспортах (статический анализ `frontend/src`, без скриншотов). Подробности и ограничения: [`../PAGE_PASSPORT_AUTOMATION.md`](../PAGE_PASSPORT_AUTOMATION.md). **Когда что запускать** (в т.ч. каждые 5 шагов runbook, PR, новый маршрут): таблица в [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md). Чеклист при смене маршрута — §4 [`../FRONTEND_ENGINEERING_CONVENTIONS.md`](../FRONTEND_ENGINEERING_CONVENTIONS.md).

**История версий паспорта:** **v1** — у каждого path из таблицы есть файл с метаданными и назначением (временно допускался явный маркер **«не заполнено»** в черновых секциях; это только markdown, не код приложения). **v2** — по рецепту [`PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`](./PAGE_PASSPORT_V2_AGENT_RUNBOOK.md): ось H, UI↔API из хуков, RBAC, gap scan; в критичных секциях маркеров **«не заполнено»** не оставляем — только **fact** или **gap** с обоснованием. **Текущее состояние среза:** все зоны Z1–Z6 в [`V2_ZONE_TRACKER.md`](./V2_ZONE_TRACKER.md) — **срез готов** (71 паспорт экрана + служебные `.md` в этом каталоге). **Глубина «каждый API ↔ контракт бэкенда»** — не минимум выхода из фазы 2; см. [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md) (раздел про границу фаз 2 и 4).

## Шаблон нового паспорта

Скопируйте блок ниже в новый файл `docs/frontend/pages/<slug>.md` и заполните (или сгенерируйте заглушку скриптом и допишите).

```markdown
# <Краткое имя экрана>

## Метаданные
- **Path:** `...`
- **Зона:** marketing | admin | app | platform | patient-entry | public
- **Компонент(ы) в App.tsx:** ...
- **Файл страницы:** `frontend/src/...`

## Назначение
(1 абзац: пользовательская цель.)

## Логика и данные
- **Хуки:** `frontend/src/hooks/...`
- **queryKey / мутации:** (кратко)
- **API:** пути `/api/v1/...` (через `api` из `client.ts`, в коде часто префикс `/v1/...`)

## RBAC / entitlements / edition
- ...

## UI-скелет (as-built)
- Layout, Card/Tabs/Table, важные Select — по факту кода.

## Инвентарь поверхностей UI (as-built)
- Таблица или список: **Drawer / Modal (Glass) / Menu / Stepper / Alert / Popover** — триггер, мутация, инвалидация, loading/error (**fact** или **gap**).
- Если overlay нет — одна строка: «модалок и drawer на странице нет».
- См. ось H в [`../PAGE_PASSPORT_CRITERIA.md`](../PAGE_PASSPORT_CRITERIA.md).

## Целевой UX (target vs as-built)
- *target:* ...
- *as-built:* ...

## Копирайт
- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты
- (vitest / e2e, если есть)

## Gap scan (вторая редакция)
- ...
```

## Полная матрица Path → файл

Групповые waiver на обязательные маршруты не используются: каждая строка ведёт на отдельный файл.

| Path / шаблон | Файл паспорта |
|---------------|----------------|
| `/` | [`marketing-landing.md`](./marketing-landing.md) |
| `/pricing` | [`marketing-pricing.md`](./marketing-pricing.md) |
| `/signup` | [`marketing-signup.md`](./marketing-signup.md) |
| `/legal/privacy` | [`marketing-legal-privacy.md`](./marketing-legal-privacy.md) |
| `/legal/terms` | [`marketing-legal-terms.md`](./marketing-legal-terms.md) |
| `/platform/login` | [`platform-login.md`](./platform-login.md) |
| `/platform/login/mfa` | [`platform-login-mfa.md`](./platform-login-mfa.md) |
| `/platform/dashboard` | [`platform-dashboard.md`](./platform-dashboard.md) |
| `/platform/provision-queue` | [`platform-provision-queue.md`](./platform-provision-queue.md) |
| `/sign-in` | [`auth-legacy-sign-in.md`](./auth-legacy-sign-in.md) |
| `/admin/login` | [`admin-login.md`](./admin-login.md) |
| `/admin` (index) | [`admin-dashboard.md`](./admin-dashboard.md) |
| `/admin/staff-chat` | [`admin-staff-chat.md`](./admin-staff-chat.md) |
| `/admin/me` | [`admin-me.md`](./admin-me.md) |
| `/admin/calendar` | [`admin-calendar.md`](./admin-calendar.md) |
| `/admin/knowledge` | [`admin-knowledge.md`](./admin-knowledge.md) |
| `/admin/clinics` | [`admin-clinics.md`](./admin-clinics.md) |
| `/admin/services` | [`admin-services.md`](./admin-services.md) |
| `/admin/schedule` | [`admin-schedule.md`](./admin-schedule.md) |
| `/admin/tasks` | [`admin-tasks.md`](./admin-tasks.md) |
| `/admin/leads-log` | [`admin-leads-log.md`](./admin-leads-log.md) |
| `/admin/bookings` | [`admin-bookings.md`](./admin-bookings.md) |
| `/admin/prepayment` | [`admin-prepayment.md`](./admin-prepayment.md) |
| `/admin/waitlist` | [`admin-waitlist.md`](./admin-waitlist.md) |
| `/admin/recall` | [`admin-recall.md`](./admin-recall.md) |
| `/admin/marketing` | [`admin-marketing.md`](./admin-marketing.md) |
| `/admin/retention` | [`admin-retention.md`](./admin-retention.md) |
| `/admin/sales` | [`admin-sales.md`](./admin-sales.md) |
| `/admin/attention` | [`admin-attention.md`](./admin-attention.md) |
| `/admin/reports` | [`admin-reports.md`](./admin-reports.md) |
| `/admin/finance` | [`admin-finance.md`](./admin-finance.md) |
| `/admin/commerce` | [`admin-commerce.md`](./admin-commerce.md) |
| `/admin/loyalty` | [`admin-loyalty.md`](./admin-loyalty.md) |
| `/admin/forms` | [`admin-forms.md`](./admin-forms.md) |
| `/admin/doctors` | [`admin-doctors.md`](./admin-doctors.md) |
| `/admin/doctor-schedule` | [`admin-doctor-schedule.md`](./admin-doctor-schedule.md) |
| `/admin/patients` | [`admin-patients.md`](./admin-patients.md) |
| `/admin/omni-chat` | [`admin-omni-chat.md`](./admin-omni-chat.md) |
| `/admin/omni-channels` | [`admin-omni-channels.md`](./admin-omni-channels.md) |
| `/admin/omni-ai-settings` | [`admin-omni-ai-settings.md`](./admin-omni-ai-settings.md) |
| `/admin/channels` | [`admin-channels.md`](./admin-channels.md) |
| `/admin/integrations` | [`admin-integrations.md`](./admin-integrations.md) |
| `/admin/embed` | [`admin-embed.md`](./admin-embed.md) |
| `/admin/rag-kb` | [`admin-rag-kb.md`](./admin-rag-kb.md) |
| `/admin/data-export` | [`admin-data-export.md`](./admin-data-export.md) |
| `/admin/omni-vault` | [`admin-omni-vault.md`](./admin-omni-vault.md) |
| `/admin/styling` | [`admin-styling.md`](./admin-styling.md) |
| `/admin/stickers` | [`admin-stickers.md`](./admin-stickers.md) |
| `/admin/settings` | [`admin-settings.md`](./admin-settings.md) |
| `/admin/subscription` | [`admin-subscription.md`](./admin-subscription.md) |
| `/admin/administrators` | [`admin-administrators.md`](./admin-administrators.md) |
| `/admin/payment-gateway` | [`admin-payment-gateway.md`](./admin-payment-gateway.md) |
| `/admin/client-reference` | [`admin-client-reference.md`](./admin-client-reference.md) |
| `/admin/discounts` | [`admin-discounts.md`](./admin-discounts.md) |
| `/admin/notification-policy` | [`admin-notification-policy.md`](./admin-notification-policy.md) |
| `/admin/agreements` | [`admin-agreements.md`](./admin-agreements.md) |
| `/admin/rights-policies` | [`admin-rights-policies.md`](./admin-rights-policies.md) |
| `/app` (index) | [`app-home.md`](./app-home.md) |
| `/app/feed` и зеркало `/c/:clinicSlug/app/feed` | [`app-feed.md`](./app-feed.md) |
| `/app/booking` и зеркало `/c/:clinicSlug/app/booking` | [`app-booking.md`](./app-booking.md) |
| `/app/history` и зеркало `/c/:clinicSlug/app/history` | [`app-history.md`](./app-history.md) |
| `/app/loyalty` и зеркало `/c/:clinicSlug/app/loyalty` | [`app-loyalty.md`](./app-loyalty.md) |
| `/app/forms` и зеркало `/c/:clinicSlug/app/forms` | [`app-forms.md`](./app-forms.md) |
| `/app/chat` и зеркало `/c/:clinicSlug/app/chat` | [`app-chat.md`](./app-chat.md) |
| `/app/profile` и зеркало `/c/:clinicSlug/app/profile` | [`app-profile.md`](./app-profile.md) |
| `/login` → редирект на `/?patientEntry=need-clinic` | [`auth-legacy-login-redirect.md`](./auth-legacy-login-redirect.md) |
| `/oauth/result` | [`app-oauth-result.md`](./app-oauth-result.md) |
| `/booking/success` | [`booking-success.md`](./booking-success.md) |
| `/admin/tasks/:taskId` | [`admin-task-detail.md`](./admin-task-detail.md) |
| `/:clinicSlug/doctors/:doctorSlug` | [`public-doctor-profile.md`](./public-doctor-profile.md) |
| `/c/:clinicSlug` (index → `sign-in`), `/c/:clinicSlug/sign-in`, `/c/:clinicSlug/app` и сегменты как у `/app/*`; отдельно `/c/sign-in` → редирект с подсказкой | [`patient-sign-in-chain.md`](./patient-sign-in-chain.md) |

## Эталонные паспорта для выборочного аудита LEAD

Страницы, которые изначально шли как пилоты полноты по [`../PAGE_PASSPORT_CRITERIA.md`](../PAGE_PASSPORT_CRITERIA.md); удобно сверять стиль и глубину при ревью любых других файлов из матрицы выше:

| Страница | Заметка |
|----------|---------|
| Лендинг | [`marketing-landing.md`](./marketing-landing.md) |
| Дашборд админки | [`admin-dashboard.md`](./admin-dashboard.md) |
| Финансы | [`admin-finance.md`](./admin-finance.md) |
| Запись PWA | [`app-booking.md`](./app-booking.md) |
| Platform login | [`platform-login.md`](./platform-login.md) |

Полный срез v2 по зонам и осям — [`V2_ZONE_TRACKER.md`](./V2_ZONE_TRACKER.md); счётчик файлов и синхронизация с кодом маршрутов — `python scripts/gen_frontend_page_passport_stubs.py verify`.

## Связанные документы

- [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md) · фазы 6–8: [`../PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](../PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md), [`../PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](../PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md), [`../PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](../PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md)  
- [`../../product_state/FRONTEND_PASSPORT.md`](../../product_state/FRONTEND_PASSPORT.md)  
- [`../../review/FRONTEND_ROUTE_AUDIT_MATRIX.md`](../../review/FRONTEND_ROUTE_AUDIT_MATRIX.md)  
- [`../../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md`](../../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md)
