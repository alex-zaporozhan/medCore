# Инвентаризация tenant (clinic / business_account)

> **Назначение:** закрыть ARCH P0 §3 и SME: явная модель изоляции данных.  
> **Проверка в CI:** `poetry run python scripts/audit_tenant_columns.py` — у каждой ORM-таблицы есть **`clinic_id`** или **`business_account_id`** (омниканал), либо таблица в `scripts/tenant_allowlist.txt` с обоснованием ниже.

## Правило

- **Прямой tenant:** колонка `clinic_id` или `business_account_id` (эквивалент клиники в омниканале).
- **Иначе:** связь только через FK к сущности, у которой уже есть tenant (junction, часы врача и т.д.) — таблица в **allowlist** и кратко описана здесь.

## Allowlist (кратко)

| Таблица | Почему без literal `clinic_id` / `business_account_id` |
|---------|------------------------------------------------------|
| `clinics` | Корневая сущность tenant |
| `permissions` | Глобальный справочник кодов прав |
| `role_permissions` | Связь роль ↔ право; роль имеет `clinic_id` |
| `service_doctors` | Связь услуга ↔ врач; оба FK в tenant |
| `doctor_working_hours` | FK на врача (`doctor_id`) |
| `doctor_absence` | FK на врача |
| `task_comments` | FK на `tasks` (`clinic_id`) |
| `package_family_links` | FK на пакеты/семью в контексте клиники |
| `patient_communication_preferences` | FK на пациента |
| `prepayment_transactions` | FK на предоплату/клинику по доменной модели |
| `waitlist_notifications` | FK на waitlist |
| `form_audit_entries` | FK на формы/клинику |
| `client_reference` | Справочник в контексте клиники по FK |
| `omni_ai_settings` | Scope `BUSINESS` + `scope_id` = business account |
| `omni_messages` | FK на `omni_chats` → `business_account_id` |

Полный список имён — в `scripts/tenant_allowlist.txt`.

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | Первая версия (P0 QA closure) |
