# QA checklist — multi-clinic Booking / PWA / Admin (BKG_MULTI)

Связанные артефакты: `ARCH_DEV_BKG_MULTI_003_TASKS.md`, `ARCH_DEV_BKG_MULTI_003.md`.

## Backend — API и границы клиники

- [ ] **Публичное расписание** `GET /v1/doctors/{id}/schedule?date=&clinic_id=` — без `clinic_id` → 422; чужой `clinic_id` для врача → **404** (не раскрывать факт существования врача).
- [ ] **Админ расписание** `GET /v1/doctors/admin/{id}/schedule` — врач не из клиники JWT → **403**, `code: clinic_forbidden` (и счётчик Redis для повторов).
- [ ] **Агрегат** `GET /v1/admin/clinics/{clinic_id}/schedule` — `clinic_id` в пути ≠ JWT → **403** `clinic_forbidden`; врач не из клиники → **403** (не 404).
- [ ] **Suggest slots** — врач не в клинике → **403** `clinic_forbidden`.
- [ ] **Пациент** `POST /v1/patient/bookings` — `clinic_id` ≠ клиника пациента → **400** `clinic_mismatch`.
- [ ] **Пациент** отмена записи — запись другой клиники → **404** (как «не найдено»).
- [ ] **Админ** cancel / no_show / reschedule — запись другой клиники → **403**, тело с `code: clinic_forbidden`, поля `expected_clinic_id` / `entity_clinic_id` при необходимости.
- [ ] **Повторные нарушения** — после **3** событий за час Redis → создаётся **Task** с `attention_kind=security.multitenancy_mismatch` (дедуп на сутки).

## Frontend — PWA

- [ ] При **>1** клинике первый шаг wizard — выбор клиники; при одной — шаг скрыт, клиника в шапке.
- [ ] `GET` расписания всегда с `clinic_id` в query; смена клиники сбрасывает услугу/врача/слот.
- [ ] История визитов показывает название клиники (или fallback).

## Frontend — Admin

- [ ] После входа `currentClinicId` совпадает с JWT / `localStorage` admin clinic id; нельзя переключиться на чужую клинику (селектор disabled или одна опция).
- [ ] **Schedule**, **Waitlist**, **Записи** — виден общий **`ClinicSelector`** (compact) в контексте страницы.
- [ ] Ответ **403** `clinic_forbidden` отображается осмысленно (при появлении toast/обработки в клиенте).

## Метрики / логи

- [ ] `multitenancy_clinic_mismatch_total{source=...}` растёт при assert / schedule_guard.
- [ ] В логах есть `multitenancy_clinic_mismatch` / `schedule_clinic_guard_failed` с id клиник.

## Регрессия

- [ ] Создание записи в своей клинике (пациент и админ) — **201**.
- [ ] RBAC и существующие security-тесты (чужая клиника) — допускается **403** вместо **404** там, где обновлён контракт.
