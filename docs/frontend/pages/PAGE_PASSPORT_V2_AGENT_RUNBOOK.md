# Runbook: усиление паспортов SPA (v2) — последовательное выполнение для агента

> **Версия:** 2026-04-08  
> **Аудитория:** агент Cursor / исполнитель @QA_ARCH  
> **Режим:** **Agent** (выполнять шаги по порядку; не пропускать номера без явной команды лида).

**Мастер-план фаз (когда этот runbook — только фаза 2):** [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md) — там же **полная шпаргалка**, когда вызывать `scripts/gen_frontend_page_passport_stubs.py` (`verify` / `generate` / `print-matrix`).

## Соответствие мастер-задаче (честная оценка @QA_ARCH)

Этот runbook **работоспособен** для своей узкой цели: **последовательно усилить файлы** `docs/frontend/pages/<slug>.md` (v2) — факты из кода, ось H, хуки→API, RBAC, gap scan, без обязательных правок приложения.

Он **не заменяет** полный объём исходного промпта:

| Блок исходной задачи | Покрытие runbook |
|----------------------|------------------|
| Обновление всего `docs/architecture`, дедуп, реструктура RAG, порядок папок | **Нет** — отдельные эпики / Plan mode |
| Усиление центрального канона дизайна **до** глубокого обхода страниц (NOTA BENE 2) | **Частично** — агент должен читать существующие `docs/design/`, `FRONTEND_*`, но runbook это не гарантирует как фазу 0 |
| Per-page: логика + эндпоинты + as-built UI | **Да** (в границах markdown паспорта) |
| Per-page: «премиум» целевая архитектура в документе, 2-я редакция | **Частично** — есть Gap scan и *target*; глубина зависит от исполнителя |
| Пиксельные цвета/шрифты/эффекты как единый аудит по всему SPA | **Слабо** — паспорт не заменяет визуальный проход в браузере и не правит `theme.ts` |
| Сверка всех эндпоинтов бэкенда с UI, починка пустых селектов, правки кода | **Нет** по умолчанию (в директиве запрет на код); исходный промпт это **требует** — нужен **отдельный** runbook/эпик «функциональный аудит + фиксы» |
| Политика копирайта, вычистка «артефактов ИИ» в строках UI | **Нет** — только отсылка к `COPY_STYLE_POLICY`; не массовый grep по UI |
| Финальная «покупательская» приёмка, безопасность, единорог-SaaS | **Нет** — это программа из нескольких треков |

**Вывод:** runbook — **правильный слой** для «документировать фронт как бэкенд на уровне экранов» (трассируемость). Чтобы выполнить **всю** мастер-задачу, нужны **дополнительные** артефакты: фаза A (архитектура/docs), фаза C (код+копирайт+ручной прогон), рубрика в [`MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md).

Скопируйте блок **«Директива агенту»** ниже в чат вместе с указанием, с какого **шага N** начать (или «с шага 1»).

---

## Директива агенту (вставить в чат)

Ты выполняешь runbook `docs/frontend/pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`.

- Работай **строго по порядку** нумерованных шагов **N = 1 … 71** (один шаг = один файл `docs/frontend/pages/<slug>.md`; предварительные шаги — только §0).
- На **каждом** шаге с паспортом: открой файл страницы из метаданных паспорта (`frontend/src/...`), выполни **рецепт одной страницы** из **§1**, сохрани изменения только в соответствующем `.md` (и при закрытии зоны — строка в `V2_ZONE_TRACKER.md` по **§3**).
- **Не** меняй прикладной код (`src/`, `frontend/src/`), если в задаче не сказано иначе. Нашёл расхождение кода и дока — зафиксируй **gap** в паспорте.
- Источник маршрутов: `frontend/src/routePaths.ts` + `frontend/src/App.tsx`. Список API для экрана — из **хуков и вызовов клиента** страницы, **не** из `src/api/v1/router.py` как инвентаря SPA.
- После **каждых 5** шагов с паспортами (или в конце сессии): `python scripts/gen_frontend_page_passport_stubs.py verify` (должен быть exit 0).

**Начни с шага:** ___ (1 по умолчанию).

---

## §0. Предварительные шаги (перед шагом 1)

| Шаг | Действие |
|-----|----------|
| **0.1** | Из корня репозитория: `python scripts/gen_frontend_page_passport_stubs.py verify` — убедиться, что exit 0. |
| **0.2** | Прочитать критерии: `docs/frontend/PAGE_PASSPORT_CRITERIA.md` (ось H). |
| **0.3** | Иметь под рукой: `docs/frontend/pages/README.md` (матрица Path → файл). |

---

## §1. Рецепт одной страницы (повторять на шагах 1–71)

Для файла `docs/frontend/pages/<slug>.md`:

1. **Метаданные** — не менять Path/зону/компонент без расхождения с `App.tsx` / `routePaths.ts`; при расхождении — поправить метаданные по коду.
2. **Назначение** — один абзац по факту UX страницы (**fact**); убрать все **«не заполнено»** в этой секции.
3. **Логика и данные** — перечислить реальные хуки (`frontend/src/hooks/...`), ключевые `queryKey`/мутации, типовые пути `/v1/...` или полные `/api/v1/...` как в `client.ts`; без выдуманных эндпоинтов.
4. **RBAC / entitlements / edition** — для админки: `AdminAuthGuard`, `AdminShellSegmentPage`, `isAdminSegmentBlockedInBox`, `adminShellSegmentEntitlementKey` / сессия; для публичных — «нет гейта» (**fact**).
5. **UI-скелет** — кратко по структуре layout, таблиц, вкладок из кода.
6. **Инвентарь поверхностей UI (ось H)** — полный перечень значимых `AdminDrawer`, `GlassModal`, `Menu`, `Modal`, `Stepper`, `Alert`… с триггером и поведением; если нет — одна фраза: модалок/drawer нет (**fact**).
7. **Целевой UX** — кратко *as-built* по коду; *target* можно оставить кратким или «совпадает с v1 приёмкой».
8. **Тесты** — указать реальные `vitest`/e2e пути или «не найдено (**gap**)».
9. **Gap scan** — второй взгляд: 1–3 bullets, что осталось непроверенным.

Если страница **уже** заполнена (пилот: `marketing-landing`, `admin-dashboard`, `admin-finance`, `app-booking`, `platform-login`) — сверить с кодом, дополнить ось H/API при необходимости, не деградировать.

---

## §2. Очередь страниц (шаги 1–71)

Порядок совпадает с таблицей в [`README.md`](./README.md). После каждой **зоны** (см. комментарии) обнови [`V2_ZONE_TRACKER.md`](./V2_ZONE_TRACKER.md): колонки зоны → **в работе** на время прохода, по завершении зоны → **срез готов** (если все страницы зоны без «не заполнено» в осях из §1).

### Зона Z1 — маркетинг (и публичный врач в конце матрицы)

| Шаг | Файл паспорта | Примечание |
|-----|----------------|------------|
| 1 | `marketing-landing.md` | Пилот — сверка |
| 2 | `marketing-pricing.md` | |
| 3 | `marketing-signup.md` | |
| 4 | `marketing-legal-privacy.md` | |
| 5 | `marketing-legal-terms.md` | |

### Зона Z2 — platform (основатель)

| Шаг | Файл паспорта | Примечание |
|-----|----------------|------------|
| 6 | `platform-login.md` | Пилот — сверка |
| 7 | `platform-login-mfa.md` | |
| 8 | `platform-dashboard.md` | |
| 9 | `platform-provision-queue.md` | |

### Зона Z3 — начало auth / admin entry

| Шаг | Файл паспорта | Примечание |
|-----|----------------|------------|
| 10 | `auth-legacy-sign-in.md` | |
| 11 | `admin-login.md` | |
| 12 | `admin-dashboard.md` | Пилот — сверка |

### Зона Z5 (сегменты shell) — порядок `ADMIN_SHELL_ROUTE_SEGMENTS`

| Шаг | Файл паспорта |
|-----|----------------|
| 13 | `admin-staff-chat.md` |
| 14 | `admin-me.md` |
| 15 | `admin-calendar.md` |
| 16 | `admin-knowledge.md` |
| 17 | `admin-clinics.md` |
| 18 | `admin-services.md` |
| 19 | `admin-schedule.md` |
| 20 | `admin-tasks.md` |
| 21 | `admin-leads-log.md` |
| 22 | `admin-bookings.md` |
| 23 | `admin-prepayment.md` |
| 24 | `admin-waitlist.md` |
| 25 | `admin-recall.md` |
| 26 | `admin-marketing.md` |
| 27 | `admin-retention.md` |
| 28 | `admin-sales.md` |
| 29 | `admin-attention.md` |
| 30 | `admin-reports.md` |
| 31 | `admin-finance.md` | Пилот — сверка |
| 32 | `admin-commerce.md` |
| 33 | `admin-loyalty.md` |
| 34 | `admin-forms.md` |
| 35 | `admin-doctors.md` |
| 36 | `admin-doctor-schedule.md` |
| 37 | `admin-patients.md` |
| 38 | `admin-omni-chat.md` |
| 39 | `admin-omni-channels.md` |
| 40 | `admin-omni-ai-settings.md` |
| 41 | `admin-channels.md` |
| 42 | `admin-integrations.md` |
| 43 | `admin-embed.md` |
| 44 | `admin-rag-kb.md` |
| 45 | `admin-data-export.md` |
| 46 | `admin-omni-vault.md` |
| 47 | `admin-styling.md` |
| 48 | `admin-stickers.md` |
| 49 | `admin-settings.md` |
| 50 | `admin-subscription.md` |
| 51 | `admin-administrators.md` |
| 52 | `admin-payment-gateway.md` |
| 53 | `admin-client-reference.md` |
| 54 | `admin-discounts.md` |
| 55 | `admin-notification-policy.md` |
| 56 | `admin-agreements.md` |
| 57 | `admin-rights-policies.md` |

### Зона Z6 — patient app (`/app/*` + зеркало)

| Шаг | Файл паспорта | Примечание |
|-----|----------------|------------|
| 58 | `app-home.md` | |
| 59 | `app-feed.md` | |
| 60 | `app-booking.md` | Пилот — сверка |
| 61 | `app-history.md` | |
| 62 | `app-loyalty.md` | |
| 63 | `app-forms.md` | |
| 64 | `app-chat.md` | |
| 65 | `app-profile.md` | |

### Зона Z3 (продолжение) — legacy / oauth / success

| Шаг | Файл паспорта |
|-----|----------------|
| 66 | `auth-legacy-login-redirect.md` |
| 67 | `app-oauth-result.md` |
| 68 | `booking-success.md` |

### Динамические шаблоны и цепочка

| Шаг | Файл паспорта | Примечание |
|-----|----------------|------------|
| 69 | `admin-task-detail.md` | `/admin/tasks/:taskId` |
| 70 | `public-doctor-profile.md` | Z1 публичное — `/:clinicSlug/doctors/:doctorSlug` |
| 71 | `patient-sign-in-chain.md` | Цепочка `/c/:clinicSlug/...` |

---

## §3. Обновление `V2_ZONE_TRACKER.md`

После завершения всех шагов зоны:

- **Z1:** шаги 1–5 и 70 (`public-doctor-profile` — можно обновить статус Z1 после шага 70).
- **Z2:** шаги 6–9.
- **Z3:** шаги 10, 66–68.
- **Z4:** шаги 11–12 и 69 (`admin-task-detail`).
- **Z5:** шаги 13–57.
- **Z6:** шаги 58–65 и 71.

В таблице зон выставь **Статус** строки: `срез готов`, когда все соответствующие паспорта без «не заполнено» в критичных секциях §1 (минимум ось H и логика/API).

---

## §4. Финализация

| Шаг | Действие |
|-----|----------|
| F.1 | `python scripts/gen_frontend_page_passport_stubs.py verify` |
| F.2 | При изменении маршрутов в будущем: `generate` + обновить строку в `README.md` + `verify`. |
| F.3 | Краткий отчёт в PR/чат: список шагов, которые доведены до v2; оставшиеся **gap**. |

---

## Связанные файлы

- **Порядок эпиков и таблица «когда какую команду скрипта»:** [`../MASTER_FRONTEND_EXECUTION_PLAN.md`](../MASTER_FRONTEND_EXECUTION_PLAN.md).
- Скрипт: `scripts/gen_frontend_page_passport_stubs.py` (`verify`, `generate`, `print-matrix`, `migrate-placeholders`) — детали и частота: см. мастер-план и §0.1 / §4 F.1–F.2 здесь.
- Трекер зон: [`V2_ZONE_TRACKER.md`](./V2_ZONE_TRACKER.md).
- Соглашения: [`../FRONTEND_ENGINEERING_CONVENTIONS.md`](../FRONTEND_ENGINEERING_CONVENTIONS.md) §4.
- Критерии мастер-задачи (выжимка): [`MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md).
