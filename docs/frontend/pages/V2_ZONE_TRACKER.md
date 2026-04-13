# Трекер качества паспортов v2 (по зонам)

> **Версия:** 2026-04-08  
> **Назначение:** итерации после v1 — ось H (инвентарь поверхностей), таблица хуков → типовые `/v1/...`, RBAC/entitlements/edition для админских сегментов, gap scan вторым проходом. Порядок зон совпадает с макро-порядком обхода в плане LEAD/QA_ARCH.

Критерии: [`../PAGE_PASSPORT_CRITERIA.md`](../PAGE_PASSPORT_CRITERIA.md). При работе над зоной: выставить статус строки в таблице ниже; в паспортах зоны не оставлять маркер **«не заполнено»** в критичных секциях runbook §1 — только факты из кода или явный **gap** с обоснованием.

## Зоны

| ID | Зона | Файлы (slug-префиксы / маска) | Ось H | UI↔API | RBAC / entitlements | Gap scan | Статус |
|----|------|--------------------------------|-------|--------|---------------------|----------|--------|
| Z1 | Маркетинг и публичное | `marketing-*`, `public-doctor-profile` | срез готов | срез готов | N/A / публичное | срез готов | срез готов |
| Z2 | Platform (основатель) | `platform-*` | срез готов | срез готов | контур platform_founder | срез готов | срез готов |
| Z3 | Auth, legacy, oauth, success | `auth-*`, `app-oauth-result`, `booking-success` | срез готов | срез готов | по экрану | срез готов | срез готов |
| Z4 | Админ: index, login, task detail | `admin-dashboard`, `admin-login`, `admin-task-detail` | срез готов | срез готов | `AdminAuthGuard`, задачи | срез готов | срез готов |
| Z5 | Админ: shell-сегменты | `admin-*` кроме Z4 и дубликатов маркетинга | срез готов | срез готов | `AdminShellSegmentPage`, entitlements, edition | срез готов | срез готов |
| Z6 | Пациентское приложение и цепочка | `app-*`, `patient-sign-in-chain` | срез готов | срез готов | patient session | срез готов | срез готов |

**Статус зоны:** `ожидает` | `в работе` | `срез готов` (для LEAD достаточно выборочного аудита файлов с заполненной осью H без оставшихся «не заполнено» в этом разделе).

## Примечание

Дубли mount path `/app/*` и `/c/:clinicSlug/app/*` описываются в одном паспорте на сегмент (`app-*.md`); зеркало указано в **Path** в метаданных и в [`README.md`](./README.md).

Срез Z5 (ось H + API, полный перечень shell-сегментов по `App.tsx`): `admin-staff-chat`, `admin-me`, `admin-calendar`, `admin-knowledge`, `admin-clinics`, `admin-services`, `admin-schedule`, `admin-tasks`, `admin-leads-log`, `admin-bookings`, `admin-prepayment`, `admin-waitlist`, `admin-recall`, `admin-marketing`, `admin-retention`, `admin-sales`, `admin-attention`, `admin-reports`, `admin-finance`, `admin-commerce`, `admin-loyalty`, `admin-forms`, `admin-doctors`, `admin-doctor-schedule`, `admin-patients`, `admin-channels`, `admin-integrations`, `admin-embed`, `admin-rag-kb`, `admin-data-export`, `admin-omni-vault`, `admin-omni-chat`, `admin-omni-channels`, `admin-omni-ai-settings`, `admin-styling`, `admin-stickers`, `admin-settings`, `admin-subscription`, `admin-administrators`, `admin-payment-gateway`, `admin-client-reference`, `admin-discounts`, `admin-notification-policy`, `admin-agreements`, `admin-rights-policies` — см. соответствующие `.md`.

Срез Z6 (ось H + API): `app-home` (index), `app-feed`, `app-booking`, `app-history`, `app-loyalty`, `app-forms`, `app-chat`, `app-profile`, `patient-sign-in-chain` — см. соответствующие `.md`.
