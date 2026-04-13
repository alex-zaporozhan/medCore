# LEAD: решения по входу пациента, тенантности и зонам продукта (2026-04-06)

Статус: **принято к реализации** (код в том же релизном потоке). Согласовано с обсуждением: маркетинговый лендинг, секретный контур основателя, пациент только в контексте бизнеса (клиники/сети).

---

## 1. Принцип ответственности и «решение-победитель»

| Критерий | Победитель |
|----------|------------|
| Пациент не ищет среди глобального каталога клиник | Публичный вход пациента **только** с контекстом клиники: публичный **`clinic_slug`** в URL или эквивалент (виджет с привязкой). |
| Масштаб 10k+ владельцев без ручного DNS на стороне платформы | Один домен продукта + **путь** `/c/{clinic_slug}/…` (и при необходимости позже wildcard-поддомен / custom domain в таблице соответствий). |
| Изоляция данных | Как и раньше: `clinic_id` в строках пациента; JWT пациента идентифицирует субъект; проверки на API по `patient.clinic_id`. |
| Сеть (5–10 точек) после входа | **Этап 2 продукта**: переключатель клиник внутри организации; в JWT/сессии — выбранная клиника. Текущий шаг — **одна домашняя клиника** = клиника из slug входа. |
| Основатель отделён от маркетинга | Витрина не ведёт на кабинет основателя; технический URL хранится в ops / закрытой документации. |
| Бизнес-лэндинг (тарифы, регистрация клиники) | Отдельная зона `/`, `/pricing`, `/signup` — **без** смешения с пациентским входом. Авторизация **владельца/сотрудника** — **`/sign-in?tab=clinic`** (и `/admin`), не на лендинге как основной сценарий. |

---

## 2. Зоны URL (канон)

| Зона | Назначение | Авторизация |
|------|------------|-------------|
| `/`, `/pricing`, `/signup`, legal | Маркетинг, онбординг **бизнеса** | Регистрация клиники/checkout; вход владельца **не** обязателен на этих страницах (отдельный `/sign-in?tab=clinic` при необходимости). |
| `/sign-in` | Единая витрина: пациент / клиника / (опционально скрыть основателя в UI) | Три контура токенов, как сейчас. |
| `/platform/*`, `/sign-in?tab=founder` | Платформа (основатель) | Секретно от маркетинга. |
| **`/c/{clinic_slug}/sign-in`**, **`/c/{clinic_slug}/app/*`** | **Пациент конкретной клиники** | SMS/OAuth с передачей `clinic_slug` в API; соглашения ПД по этой клинике. |

---

## 3. Бэкенд (реализация)

- **`clinic_slug` в `POST /v1/auth/send-code` и `POST /v1/auth/verify-code`**: опционально; если передан — резолв `Clinic` по `clinics.clinic_slug` (не удалена); если нет — **поведение как раньше** (первая клиника в БД) для dev/legacy **или** при **`PATIENT_AUTH_REQUIRE_CLINIC_SLUG=true`** — **400** с кодом `CLINIC_SLUG_REQUIRED` (**решение-победитель**: не смешивать глобальный `/app` с тенантом без явного slug). В **`APP_ENV=production`** при отсутствии переменных в окружении включаются умолчания: **`patient_auth_require_clinic_slug=true`**, **`rate_auth_unknown_clinic_slug_ip_limit=90`**, **`…_window_seconds=600`** (10 мин; диапазон QA_ARCH 60–120 / 5–15 мин); override через env.
- **`GET /v1/auth/agreement?clinic_slug=`** — политика ПД для выбранной клиники.
- **OAuth**: в state Redis — JSON `{ "redirect", "clinic_slug" }`; колбэки передают slug в `OAuthAuthService`; при неизвестном slug — редирект с `code=UNKNOWN_CLINIC_SLUG`; при лимите перебора — `status=rate_limited`; при политике без slug — `code=CLINIC_SLUG_REQUIRED`.
- **Метрика** `patient_auth_clinic_context_total{source,result}` — `default|slug` × `ok|unknown|empty_db|slug_required`.
- **Защита и нагрузки**: rate limit по IP/телефону; опционально **`RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_*`** — бюрст ответов 400 по несуществующему slug (перечисление); ключи Redis для кодов содержат `clinic_id`.
- **Кэш**: Redis для SMS-кодов и OAuth state без изменения TTL; кэш справочника slug не обязателен на первом шаге (запрос по индексу `clinic_slug`).
- **Наблюдаемость**: Prometheus rules `PatientAuthUnknownClinicSlugBurst`, `PatientAuthSlugRequiredPolicyTraffic` в `deploy/prometheus/dental_booking_alerts.yml`.

---

## 4. Принципиальные замечания ARCH / PRINCIPLE

- **ARCH**: контракт API расширен опциональным полем; ошибка «неизвестный slug» — 400 с кодом для UI; без утечки существования телефона в чужом slug.
- **PRINCIPLE**: инвариант «пациент создаётся в клинике, определённой контекстом входа»; перенос сети (организация → несколько клиник для одного пациента) — отдельная модель (этап 2).

---

## 5. Фронтенд

- Контекст **`PatientEntryContext`**: `clinicSlug: string | undefined` для вложенных маршрутов `/c/:clinicSlug/…`.
- Панель пациента передаёт `clinic_slug` в хуки auth; OAuth — query `clinic_slug` и redirect на `/c/{slug}/app`.

---

## 6. Что остаётся бэклогом (не блокирует текущий merge)

- `organizations.public_slug` и вход «на сеть» одним slug без привязки к одной клинике.
- JWT с `organization_id` для переключателя сети.
- Кастомные домены клиентов (CNAME → platform).

---

## 7. Реализация в коде (сессия 2026-04-06)

- **Бэкенд:** `src/application/services/patient_entry_clinic.py` — резолв клиники по `clinic_slug` или fallback; метрика `patient_auth_clinic_context_total`; DTO `clinic_slug` в send/verify; `GET /v1/auth/agreement?clinic_slug=`; OAuth state JSON с `clinic_slug`, исправлена логика чтения state в VK/Yandex callback.
- **Политика prod (QA_ARCH 2026-04-13):** `Settings.patient_auth_require_clinic_slug`, сообщение `AUTH_CLINIC_SLUG_REQUIRED`, опциональный лимит перебора slug на auth-роутерах.
- **Фронтенд:** `PatientEntryBoundary` + маршруты `/c/:clinicSlug/sign-in` и `/c/:clinicSlug/app/*`; `useAuth` передаёт `clinic_slug`; на scoped sign-in только панель пациента; редиректы 401 и AppLayout учитывают slug; панель пациента — заголовки ошибок по кодам `UNKNOWN_CLINIC_SLUG` / `CLINIC_SLUG_REQUIRED`.
- **Тесты API:** `tests/api/test_auth_clinic_slug.py` (при `DATABASE_URL_TEST` и `pytest`).
- **E2E (статический preview):** `frontend/e2e/patient-entry-sign-in.spec.ts` — заголовок «Вход пациента» на `/c/.../sign-in`.
