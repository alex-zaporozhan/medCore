# Манифест подключения роутеров API v1

> **Источник:** порядок `include_router` в `src/api/v1/router.py` (78 модулей).  
> **Базовый префикс:** `Settings.api_v1_prefix` (по умолчанию `/api/v1`, `src/core/config.py`, `src/main.py`).  
> **Полный URL:** `{api_v1_prefix}` + `{prefix из APIRouter}` + `{path в декораторе}`.

Интерактивный полный перечень HTTP-путей: **`/docs`** и **`/redoc`** у запущенного API (Swagger UI, не git-каталог `docs/`).

## Таблица (модуль → prefix)

| Модуль | prefix |
|--------|--------|
| auth | `/auth` |
| config | *(нет)* |
| stickers | `/stickers` |
| clinics | `/clinics` |
| doctors | `/doctors` |
| services | `/services` |
| admin_services | `/admin/clinics` |
| admin_schedule | `/admin/clinics` |
| admin_doctor_schedule | `/admin/doctors` |
| admin_prepayment | `/admin/clinics` |
| admin_waitlist | `/admin/clinics` |
| admin_recall | `/admin/clinics` |
| admin_marketing | `/admin/clinics` |
| admin_reports | `/admin/clinics` |
| admin_reports_aggregate | `/admin` |
| admin_marketing_attribution | `/admin/attribution` |
| admin_chat | `/admin/chat` |
| admin_channel_configs | `/admin/clinics` |
| admin_admins | `/admin/admins` |
| admin_staff_directory | `/admin/clinics` |
| admin_staff_profile | `/admin/staff` |
| admin_patient_medical | `/admin/clinics` |
| admin_agreement | `/admin/clinics` |
| admin_auth | `/admin/auth` |
| admin_client_reference | `/admin/client-reference` |
| admin_clinics_summary | `/admin/clinics` |
| admin_discounts | `/admin/clinics` |
| admin_integrations | `/admin/clinics` |
| admin_owner_settings | `/admin/clinics` |
| admin_notification_policy | `/admin/clinics` |
| admin_attention_feed | `/admin/clinics` |
| admin_patient_ai | `/admin/patients` |
| admin_ai_settings | `/admin/clinics` |
| admin_ai_reports | `/admin/ai-reports` |
| admin_ai_status | `/admin/ai-status` |
| admin_ai_tasks_settings | `/admin/clinics` |
| admin_public_doctor_profiles | `/admin/clinics` |
| admin_payment_gateway | `/admin/clinics` |
| admin_finance | `/admin/clinics` |
| admin_payroll | `/admin/clinics` |
| admin_inventory | `/admin/clinics` |
| admin_crm | `/admin/crm` |
| admin_tasks | `/admin/tasks` |
| admin_task_boards | `/admin/task-boards` |
| admin_task_streams | `/admin/task-streams` |
| admin_task_tags | `/admin/task-tags` |
| admin_staff_collab | `/admin/staff` |
| admin_staff_announcement_policy | `/admin/staff` |
| patient_chat | `/patient/chat` |
| patient_notification_settings | `/patient` |
| public_services | `/public/clinics` |
| public_marketing | `/public/clinics` |
| public_doctor_profiles | `/public/clinics` |
| patients | `/patients` |
| schedule | `/doctors` |
| bookings | *(нет — пути в декораторах)* |
| payments | `/payments` |
| csv_sync | *(нет — пути в декораторах)* |
| reports | `/reports` |
| admin_omni_chat | `/admin/omni-chats` |
| admin_omni_chat_closure_tags | `/admin/omni-chat-closure-tags` |
| integrations_gateway | `""` |
| owner_omni_channels | `/owner/channels` |
| owner_omni_ai_settings | `/owner/omni-ai-settings` |
| owner_omni_audit | `/owner/audit-log` |
| admin_loyalty | `/admin/loyalty` |
| patient_loyalty | `/patient/loyalty` |
| admin_forms | `/admin/forms` |
| patient_forms | `/patient/forms` |
| admin_search | `/admin` |
| ai_agent | `/ai` |
| admin_retention | `/admin/clinics` |
| admin_vault | `/admin` |
| admin_ui_events | `/admin/ui-events` |
| admin_omni_tools | `/admin/omni` |
| admin_rbac_management | `/admin/rbac` |
| admin_lead_logs | `/admin/lead-logs` |
| admin_leads_log_routing | `/admin/leads-log` |

**Примеры без prefix:** `config` → `GET /api/v1/config`; `bookings` — см. пути вида `/patient/bookings`, … в `bookings.py`.

Несколько модулей с общим `/admin/clinics` различаются **суффиксами** внутри файла; уточнять по OpenAPI или исходнику.

## Сопровождение

При изменении `router.py` обновляйте эту таблицу или добавьте CI-сравнение списка модулей.
