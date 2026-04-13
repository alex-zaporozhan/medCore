# QA_ARCH: отчёт — patient entry по `clinic_slug` (2026-04-06)

Источник решений: `docs/artifacts/LEAD_PATIENT_ENTRY_AND_TENANCY_DECISIONS_2026-04-06.md`.  
Проверено по коду: `patient_entry_clinic.py`, `auth` router/DTO, OAuth, фронт `PatientEntryContext`, `useAuth`, `PatientPhoneAuthPanel`, `AppLayout`, `client.ts`.

---

## Вердикт

| Область | Заключение |
|---------|------------|
| Соответствие LEAD | **Соответствует**: контекст клиники по slug, отдельные маршруты `/c/:clinicSlug/…`, метрика, контракт ошибки `UNKNOWN_CLINIC_SLUG`. |
| Готовность к прод-нагрузке | **Условно**: базовые rate limit и Redis есть; ниже — пробелы и усиления. |

---

## Критические риски (🔴)

1. **Дубли `clinic_slug` в БД** (нарушение уникальности): `scalar_one_or_none()` при двух строках — `MultipleResultsFound` → 500. **Митигация:** запрос с `.limit(1)` + уникальный индекс в БД (уже есть `unique=True` на колонке) — остаётся дисциплина миграций/данных.
2. **Глобальный `/app` без slug** — при **`PATIENT_AUTH_REQUIRE_CLINIC_SLUG=false`** (по умолчанию) сохраняется legacy «первая клиника». В prod после миграции клиентов на `/c/{slug}/…` включите **`true`** — API вернёт `CLINIC_SLUG_REQUIRED` без утечки данных о клиниках.

---

## Средние риски (🟡)

1. **Длина и мусор в `clinic_slug`** — без ограничения длины возможны abuse и 500 на БД. **Исправлено:** Pydantic `max_length=120` + trim, Query для agreement.
2. **Перечисление валидных slug** через `GET /agreement` — ответ 400 быстрее, чем для «левого» телефона; частично смягчено **`RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_*`** (счётчик на каждый 400 `UNKNOWN_CLINIC_SLUG`; при превышении — 429 или OAuth `status=rate_limited`). 0 = выкл.
3. **Расхождение send/verify slug** — пользователь меняет URL между шагами → неверный код. Поведение ожидаемо; UX: подсказка в тексте (опционально).
4. **OAuth redirect `/app/login`** — в legacy ещё редирект на `/sign-in`; fallback в `_parse_oauth_state` безопасен (`_is_safe_redirect_path`).

---

## Формально сделано / недоделано

| Тема | Было |
|------|------|
| Метрики | `patient_auth_clinic_context_total` — ок; Prometheus rules `PatientAuthUnknownClinicSlugBurst`, `PatientAuthSlugRequiredPolicyTraffic` в `deploy/prometheus/dental_booking_alerts.yml`. |
| Кэш slug→id | Не делался — **ок для первого этапа** (индекс по slug). |
| E2E Playwright | `frontend/e2e/patient-entry-sign-in.spec.ts` (preview, без API). |
| Админка: «скопировать ссылку пациенту» | Не делалось — **UX-бэклог**. |

---

## Усиления внесённые в код (этот PR QA_ARCH)

1. Валидация и нормализация `clinic_slug` (длина ≤120, trim) в `SendCodeRequest` / `VerifyCodeRequest`, в `Query` для `GET /agreement` и OAuth `/oauth/*/start`.
2. `LIMIT 1` в SQL-резолве slug для предсказуемости при аномальных данных.
3. Нормализация `clinicSlug` во `PatientEntryBoundary` (пробелы / пустая строка → `null`).
4. Заголовок алерта «Клиника не найдена» при `ApiErrorWithCode` с кодом `UNKNOWN_CLINIC_SLUG`.
5. Юнит-тесты: `tests/test_auth_dto_clinic_slug.py`.
6. **2026-04-13:** `PATIENT_AUTH_REQUIRE_CLINIC_SLUG`, `AUTH_CLINIC_SLUG_REQUIRED`, метка `slug_required`; `RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_*`; OAuth редиректы `CLINIC_SLUG_REQUIRED` / `rate_limited`; фронт — заголовок для `CLINIC_SLUG_REQUIRED`; API-тест `test_send_code_clinic_slug_required_when_flag`.

---

## Рекомендации на следующий спринт

- **`APP_ENV=production`:** при отсутствии явных env включаются умолчания `patient_auth_require_clinic_slug=true`, лимит перебора slug **90 / 600 с** (`Settings._apply_production_patient_auth_defaults`). Override через `PATIENT_AUTH_*` / `RATE_AUTH_*` при необходимости.
- Админка: блок «Ссылка для пациентов» с полным URL (UX-бэклог).
- E2E с поднятым API: smoke send-code с `seed` slug (опционально в CI со стеком).
