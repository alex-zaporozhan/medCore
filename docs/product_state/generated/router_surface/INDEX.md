# Поверхность API v1 по каждому роутеру (автогенерация)

> **Источник:** `scripts/generate_router_surface_docs.py` · порядок = `include_router` в `src/api/v1/router.py`.
> **Полный URL:** значение `api_v1_prefix` из `src/core/config.py` + prefix роутера + path.

Чек-лист для разработки: бэкенд-файл, префикс, маршруты (статический разбор), тесты (эвристика по вхождению имени модуля), метрики (импорты из `src.core.metrics`).

После изменений роутеров: `python scripts/generate_router_surface_docs.py` и закоммитить diff.

## Ограничения автогенерации

- Пути в декораторах на нескольких строках без кавычек сразу после `(` могут не попасть в таблицу.
- Список тестов неполный, если модуль не упоминается в тексте файла теста.
- Связка с экранами SPA — сверять с `frontend/src/App.tsx` и `frontend/src/routePaths.ts`.

# Роутеры по порядку подключения

## 1. `auth`
- **Backend:** `src/api/v1/routers/auth.py`
- **APIRouter prefix:** `/auth`
- **Frontend search hint:** `rg 'auth' frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `auth_captcha_required_total`
  - `auth_captcha_verified_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/send-code` |
| POST | `/verify-code` |
| GET | `/agreement` |
| GET | `/oauth/vk/start` |
| GET | `/oauth/yandex/start` |
| GET | `/oauth/vk/callback` |
| GET | `/oauth/yandex/callback` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_auth.py`
- `tests/api/test_auth_oauth.py`
- `tests/api/test_auth_turnstile_adaptive.py`

---

## 2. `config`
- **Backend:** `src/api/v1/routers/config.py`
- **APIRouter prefix:** `(see decorators — no APIRouter prefix)`
- **Frontend search hint:** `rg 'config' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/config` |

### Tests (files under `tests/` mentioning this module)

- `tests/services/test_ai_config_service.py`
- `tests/services/test_omnichannel_integrations_config_service.py`

---

## 3. `stickers`
- **Backend:** `src/api/v1/routers/stickers.py`
- **APIRouter prefix:** `/stickers`
- **Frontend search hint:** `rg 'stickers' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/sets` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 4. `clinics`
- **Backend:** `src/api/v1/routers/clinics.py`
- **APIRouter prefix:** `/clinics`
- **Frontend search hint:** `rg 'clinics' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| GET | `/{clinic_id}` |
| POST | `(root)` |
| PUT | `/{clinic_id}` |
| DELETE | `/{clinic_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 5. `doctors`
- **Backend:** `src/api/v1/routers/doctors.py`
- **APIRouter prefix:** `/doctors`
- **Frontend search hint:** `rg 'doctors' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| GET | `/{doctor_id}` |
| POST | `(root)` |
| PUT | `/{doctor_id}` |
| DELETE | `/{doctor_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_doctors.py`

---

## 6. `services`
- **Backend:** `src/api/v1/routers/services.py`
- **APIRouter prefix:** `/services`
- **Frontend search hint:** `rg 'services' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| GET | `/{service_id}` |
| POST | `(root)` |
| PUT | `/{service_id}` |
| DELETE | `/{service_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_services.py`
- `tests/services/test_erp_services.py`
- `tests/services/test_loyalty_services.py`

---

## 7. `admin_services`
- **Backend:** `src/api/v1/routers/admin_services.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/services` |
| GET | `/{clinic_id}/services/{service_id}/card` |
| POST | `/{clinic_id}/services` |
| PUT | `/{clinic_id}/services/{service_id}` |
| DELETE | `/{clinic_id}/services/{service_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 8. `admin_schedule`
- **Backend:** `src/api/v1/routers/admin_schedule.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/schedule` |
| GET | `/{clinic_id}/schedule/suggest-slots` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 9. `admin_doctor_schedule`
- **Backend:** `src/api/v1/routers/admin_doctor_schedule.py`
- **APIRouter prefix:** `/admin/doctors`
- **Frontend search hint:** `rg doctors frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{doctor_id}/working-hours` |
| POST | `/{doctor_id}/working-hours` |
| PUT | `/{doctor_id}/working-hours/{wh_id}` |
| DELETE | `/{doctor_id}/working-hours/{wh_id}` |
| GET | `/{doctor_id}/absence` |
| POST | `/{doctor_id}/absence` |
| DELETE | `/{doctor_id}/absence/{absence_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 10. `admin_prepayment`
- **Backend:** `src/api/v1/routers/admin_prepayment.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/prepayment/policies` |
| POST | `/{clinic_id}/prepayment/policies` |
| GET | `/{clinic_id}/prepayment/policies/{policy_id}` |
| PUT | `/{clinic_id}/prepayment/policies/{policy_id}` |
| DELETE | `/{clinic_id}/prepayment/policies/{policy_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 11. `admin_waitlist`
- **Backend:** `src/api/v1/routers/admin_waitlist.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/waitlist` |
| POST | `/{clinic_id}/waitlist` |
| GET | `/{clinic_id}/waitlist/{entry_id}` |
| PUT | `/{clinic_id}/waitlist/{entry_id}` |
| DELETE | `/{clinic_id}/waitlist/{entry_id}` |
| GET | `/{clinic_id}/queue-policy` |
| PUT | `/{clinic_id}/queue-policy` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 12. `admin_recall`
- **Backend:** `src/api/v1/routers/admin_recall.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/recall/segments` |
| POST | `/{clinic_id}/recall/segments` |
| GET | `/{clinic_id}/recall/segments/{segment_id}` |
| PUT | `/{clinic_id}/recall/segments/{segment_id}` |
| DELETE | `/{clinic_id}/recall/segments/{segment_id}` |
| GET | `/{clinic_id}/recall/templates` |
| POST | `/{clinic_id}/recall/templates` |
| GET | `/{clinic_id}/recall/templates/{template_id}` |
| PUT | `/{clinic_id}/recall/templates/{template_id}` |
| DELETE | `/{clinic_id}/recall/templates/{template_id}` |
| GET | `/{clinic_id}/recall/campaigns` |
| POST | `/{clinic_id}/recall/campaigns` |
| GET | `/{clinic_id}/recall/campaigns/{campaign_id}` |
| PUT | `/{clinic_id}/recall/campaigns/{campaign_id}` |
| DELETE | `/{clinic_id}/recall/campaigns/{campaign_id}` |
| POST | `/{clinic_id}/recall/campaigns/{campaign_id}/run` |
| GET | `/{clinic_id}/recall/automations` |
| POST | `/{clinic_id}/recall/automations` |
| GET | `/{clinic_id}/recall/automations/{automation_id}` |
| PUT | `/{clinic_id}/recall/automations/{automation_id}` |
| DELETE | `/{clinic_id}/recall/automations/{automation_id}` |
| GET | `/{clinic_id}/recall/logs` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 13. `admin_marketing`
- **Backend:** `src/api/v1/routers/admin_marketing.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/marketing/posts` |
| POST | `/{clinic_id}/marketing/posts` |
| GET | `/{clinic_id}/marketing/posts/{post_id}` |
| PUT | `/{clinic_id}/marketing/posts/{post_id}` |
| DELETE | `/{clinic_id}/marketing/posts/{post_id}` |
| GET | `/{clinic_id}/marketing/stories` |
| POST | `/{clinic_id}/marketing/stories` |
| GET | `/{clinic_id}/marketing/stories/{story_id}` |
| PUT | `/{clinic_id}/marketing/stories/{story_id}` |
| DELETE | `/{clinic_id}/marketing/stories/{story_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_marketing_attribution.py`

---

## 14. `admin_reports`
- **Backend:** `src/api/v1/routers/admin_reports.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `Counter  # type: ignore[attr-defined]`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/reports/revenue-saved-by-ai` |
| GET | `/{clinic_id}/reports/dashboard` |
| GET | `/{clinic_id}/reports/no-show` |
| GET | `/{clinic_id}/reports/revenue` |
| GET | `/{clinic_id}/reports/revenue-by-period` |
| POST | `/{clinic_id}/reports/erp-aggregates/visit-revenue/refresh` |
| POST | `/{clinic_id}/reports/erp-aggregates/refresh` |
| GET | `/{clinic_id}/reports/owner-dashboard` |
| GET | `/{clinic_id}/reports/crm-funnel` |
| GET | `/{clinic_id}/reports/patient-ltv` |
| GET | `/{clinic_id}/reports/payroll-by-period` |
| GET | `/{clinic_id}/reports/materials-by-period` |
| GET | `/{clinic_id}/reports/loyalty-obligations` |
| GET | `/{clinic_id}/reports/roi-by-source` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_reports_erp_endpoints.py`

---

## 15. `admin_reports_aggregate`
- **Backend:** `src/api/v1/routers/admin_reports_aggregate.py`
- **APIRouter prefix:** `/admin`
- **Frontend search hint:** `rg /admin frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/reports/dashboard-aggregate` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 16. `admin_marketing_attribution`
- **Backend:** `src/api/v1/routers/admin_marketing_attribution.py`
- **APIRouter prefix:** `/admin/attribution`
- **Frontend search hint:** `rg attribution frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/summary` |
| GET | `/campaigns` |
| POST | `/campaigns` |
| GET | `/drill-down` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_marketing_attribution.py`

---

## 17. `admin_chat`
- **Backend:** `src/api/v1/routers/admin_chat.py`
- **APIRouter prefix:** `/admin/chat`
- **Frontend search hint:** `rg chat frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `chat_rate_limited_total`
  - `chat_upload_rejected_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/conversations` |
| GET | `/conversations/{conversation_id}/messages` |
| POST | `/conversations/{conversation_id}/messages` |
| POST | `/conversations/{conversation_id}/messages/upload` |
| GET | `/conversations/{conversation_id}/attachments/{attachment_id}/file` |
| POST | `/conversations/{conversation_id}/assign` |
| DELETE | `/conversations/{conversation_id}/messages/{message_id}` |
| POST | `/conversations/{conversation_id}/mark-read` |
| GET | `/conversations/{conversation_id}/ai-summary` |
| POST | `/conversations/{conversation_id}/ai-suggest-reply` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 18. `admin_channel_configs`
- **Backend:** `src/api/v1/routers/admin_channel_configs.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/channel-configs` |
| PUT | `/{clinic_id}/channel-configs/{channel}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 19. `admin_admins`
- **Backend:** `src/api/v1/routers/admin_admins.py`
- **APIRouter prefix:** `/admin/admins`
- **Frontend search hint:** `rg admins frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PATCH | `/{admin_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 20. `admin_staff_directory`
- **Backend:** `src/api/v1/routers/admin_staff_directory.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/staff-directory/profession-categories` |
| POST | `/{clinic_id}/staff-directory/profession-categories` |
| PATCH | `/{clinic_id}/staff-directory/profession-categories/{category_id}` |
| DELETE | `/{clinic_id}/staff-directory/profession-categories/{category_id}` |
| GET | `/{clinic_id}/staff-directory/admins` |
| POST | `/{clinic_id}/staff-directory/admins` |
| PATCH | `/{clinic_id}/staff-directory/admins/{admin_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_staff_directory.py`

---

## 21. `admin_staff_profile`
- **Backend:** `src/api/v1/routers/admin_staff_profile.py`
- **APIRouter prefix:** `/admin/staff`
- **Frontend search hint:** `rg staff frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/profiles/{admin_id}` |
| GET | `/me/profile` |
| PATCH | `/me/profile` |
| POST | `/me/avatar` |
| GET | `/avatars/{admin_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_staff_profile.py`

---

## 22. `admin_patient_medical`
- **Backend:** `src/api/v1/routers/admin_patient_medical.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `(`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/patients/{patient_id}/medical/visits` |
| POST | `/{clinic_id}/patients/{patient_id}/medical/visits` |
| GET | `/{clinic_id}/patients/{patient_id}/medical/diagnoses` |
| POST | `/{clinic_id}/patients/{patient_id}/medical/diagnoses` |
| GET | `/{clinic_id}/patients/{patient_id}/medical/files` |
| POST | `/{clinic_id}/patients/{patient_id}/medical/files:upload` |
| GET | `/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download` |
| POST | `/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:download-token` |
| GET | `/{clinic_id}/patients/{patient_id}/medical/files/{file_id}:stream` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_patient_medical.py`

---

## 23. `admin_agreement`
- **Backend:** `src/api/v1/routers/admin_agreement.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/agreement-settings` |
| PUT | `/{clinic_id}/agreement-settings` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 24. `admin_auth`
- **Backend:** `src/api/v1/routers/admin_auth.py`
- **APIRouter prefix:** `/admin/auth`
- **Frontend search hint:** `rg auth frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/login` |
| GET | `/session` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 25. `admin_client_reference`
- **Backend:** `src/api/v1/routers/admin_client_reference.py`
- **APIRouter prefix:** `/admin/client-reference`
- **Frontend search hint:** `rg client-reference frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| PUT | `(root)` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 26. `admin_clinics_summary`
- **Backend:** `src/api/v1/routers/admin_clinics_summary.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/patients/{patient_id}/summary` |
| GET | `/{clinic_id}/patients/{patient_id}/messages` |
| GET | `/{clinic_id}/doctors/{doctor_id}/summary` |
| GET | `/{clinic_id}/patients/{patient_id}/card` |
| GET | `/{clinic_id}/doctors/{doctor_id}/card` |
| GET | `/{clinic_id}/marketing/insights` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 27. `admin_discounts`
- **Backend:** `src/api/v1/routers/admin_discounts.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/discounts` |
| POST | `/{clinic_id}/discounts` |
| GET | `/{clinic_id}/discounts/{discount_id}` |
| PUT | `/{clinic_id}/discounts/{discount_id}` |
| DELETE | `/{clinic_id}/discounts/{discount_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 28. `admin_integrations`
- **Backend:** `src/api/v1/routers/admin_integrations.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/integration-settings/{provider}` |
| PUT | `/{clinic_id}/integration-settings/{provider}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 29. `admin_owner_settings`
- **Backend:** `src/api/v1/routers/admin_owner_settings.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/settings/owner-brief` |
| PATCH | `/{clinic_id}/settings/owner-brief` |
| GET | `/{clinic_id}/settings/ai-supervisor` |
| PATCH | `/{clinic_id}/settings/ai-supervisor` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 30. `admin_notification_policy`
- **Backend:** `src/api/v1/routers/admin_notification_policy.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/notification-policy` |
| PUT | `/{clinic_id}/notification-policy` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 31. `admin_attention_feed`
- **Backend:** `src/api/v1/routers/admin_attention_feed.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/attention-feed` |
| PATCH | `/{clinic_id}/attention-feed/items/claim` |
| GET | `/{clinic_id}/attention-feed/{item_type}/{item_id}/tasks` |
| POST | `/{clinic_id}/attention-feed/{item_type}/{item_id}/tasks` |
| POST | `/{clinic_id}/attention-feed/follow-up/{message_id}/close` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 32. `admin_patient_ai`
- **Backend:** `src/api/v1/routers/admin_patient_ai.py`
- **APIRouter prefix:** `/admin/patients`
- **Frontend search hint:** `rg patients frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{patient_id}/ai-insight` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 33. `admin_ai_settings`
- **Backend:** `src/api/v1/routers/admin_ai_settings.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/ai-settings` |
| PUT | `/{clinic_id}/ai-settings` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 34. `admin_ai_reports`
- **Backend:** `src/api/v1/routers/admin_ai_reports.py`
- **APIRouter prefix:** `/admin/ai-reports`
- **Frontend search hint:** `rg ai-reports frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/conflicts` |
| POST | `/conflicts/reanalyze` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 35. `admin_ai_status`
- **Backend:** `src/api/v1/routers/admin_ai_status.py`
- **APIRouter prefix:** `/admin/ai-status`
- **Frontend search hint:** `rg ai-status frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 36. `admin_ai_tasks_settings`
- **Backend:** `src/api/v1/routers/admin_ai_tasks_settings.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/ai-task-settings` |
| PUT | `/{clinic_id}/ai-task-settings` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 37. `admin_public_doctor_profiles`
- **Backend:** `src/api/v1/routers/admin_public_doctor_profiles.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/public-doctor-profiles` |
| POST | `/{clinic_id}/public-doctor-profiles` |
| PATCH | `/{clinic_id}/public-doctor-profiles/{profile_id}` |
| DELETE | `/{clinic_id}/public-doctor-profiles/{profile_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 38. `admin_payment_gateway`
- **Backend:** `src/api/v1/routers/admin_payment_gateway.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/{clinic_id}/payment-gateway/credentials` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_payment_gateway_credentials.py`

---

## 39. `admin_finance`
- **Backend:** `src/api/v1/routers/admin_finance.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/finance/liability` |
| GET | `/{clinic_id}/finance/cashboxes` |
| POST | `/{clinic_id}/finance/cashboxes` |
| PATCH | `/{clinic_id}/finance/cashboxes/{cashbox_id}` |
| DELETE | `/{clinic_id}/finance/cashboxes/{cashbox_id}` |
| GET | `/{clinic_id}/finance/transactions` |
| POST | `/{clinic_id}/finance/transactions` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 40. `admin_payroll`
- **Backend:** `src/api/v1/routers/admin_payroll.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/payroll/policies` |
| POST | `/{clinic_id}/payroll/policies` |
| PATCH | `/{clinic_id}/payroll/policies/{policy_id}` |
| DELETE | `/{clinic_id}/payroll/policies/{policy_id}` |
| GET | `/{clinic_id}/payroll/transactions` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 41. `admin_inventory`
- **Backend:** `src/api/v1/routers/admin_inventory.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/inventory/products` |
| POST | `/{clinic_id}/inventory/products` |
| PATCH | `/{clinic_id}/inventory/products/{product_id}` |
| DELETE | `/{clinic_id}/inventory/products/{product_id}` |
| GET | `/{clinic_id}/inventory/warehouses` |
| POST | `/{clinic_id}/inventory/warehouses` |
| PATCH | `/{clinic_id}/inventory/warehouses/{warehouse_id}` |
| DELETE | `/{clinic_id}/inventory/warehouses/{warehouse_id}` |
| GET | `/{clinic_id}/inventory/services/{service_id}/consumables` |
| PUT | `/{clinic_id}/inventory/services/{service_id}/consumables` |
| GET | `/{clinic_id}/inventory/transactions` |
| GET | `/{clinic_id}/inventory/stock` |
| POST | `/{clinic_id}/inventory/transactions` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 42. `admin_crm`
- **Backend:** `src/api/v1/routers/admin_crm.py`
- **APIRouter prefix:** `/admin/crm`
- **Frontend search hint:** `rg crm frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `crm_ai_recommendations_total`
  - `crm_leads_list_requests_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/pipelines` |
| GET | `/stages` |
| GET | `/pipelines/{pipeline_id}/stage-semantics` |
| PUT | `/pipelines/{pipeline_id}/stage-semantics` |
| GET | `/leads` |
| GET | `/leads/{lead_id}` |
| PATCH | `/leads/{lead_id}/stage` |
| PATCH | `/leads/{lead_id}/estimated-value` |
| POST | `/leads/{lead_id}/notes` |
| GET | `/leads/{lead_id}/ai/summary` |
| GET | `/leads/{lead_id}/ai/suggest-next-stage` |
| PATCH | `/leads/{lead_id}/ai/stage` |
| POST | `/leads/{lead_id}/ai/tasks` |
| POST | `/leads/{lead_id}/ai/recommendations/ignore` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_crm.py`

---

## 43. `admin_tasks`
- **Backend:** `src/api/v1/routers/admin_tasks.py`
- **APIRouter prefix:** `/admin/tasks`
- **Frontend search hint:** `rg tasks frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `task_bulk_status_total`
  - `task_context_admin_events_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `/{task_id}/claim` |
| GET | `/{task_id}/comments` |
| GET | `/{task_id}` |
| POST | `(root)` |
| PATCH | `/{task_id}` |
| POST | `/{task_id}/comments` |
| GET | `/wip-policies` |
| GET | `/{task_id}/transitions` |
| GET | `/{task_id}/calendar-context` |
| POST | `/reorder` |
| POST | `/bulk/status` |
| POST | `/{task_id}/calendar-events/{event_id}/invite` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_tasks_rate_limit.py`
- `tests/api/test_admin_tasks_rbac.py`
- `tests/api/test_admin_tasks_reorder_concurrency.py`
- `tests/api/test_admin_tasks_workflow_and_calendar.py`

---

## 44. `admin_task_boards`
- **Backend:** `src/api/v1/routers/admin_task_boards.py`
- **APIRouter prefix:** `/admin/task-boards`
- **Frontend search hint:** `rg task-boards frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PUT | `/{board_id}/columns` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_task_boards.py`

---

## 45. `admin_task_streams`
- **Backend:** `src/api/v1/routers/admin_task_streams.py`
- **APIRouter prefix:** `/admin/task-streams`
- **Frontend search hint:** `rg task-streams frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `task_context_admin_events_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PATCH | `/{stream_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_task_streams_and_tags.py`

---

## 46. `admin_task_tags`
- **Backend:** `src/api/v1/routers/admin_task_tags.py`
- **APIRouter prefix:** `/admin/task-tags`
- **Frontend search hint:** `rg task-tags frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `task_context_admin_events_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PATCH | `/{tag_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 47. `admin_staff_collab`
- **Backend:** `src/api/v1/routers/admin_staff_collab.py`
- **APIRouter prefix:** `/admin/staff`
- **Frontend search hint:** `rg staff frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `chat_rate_limited_total`
  - `chat_upload_rejected_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/chat/rooms` |
| POST | `/chat/rooms/{room_id}/read` |
| GET | `/chat/rooms/{room_id}/messages` |
| POST | `/chat/rooms/{room_id}/messages` |
| POST | `/chat/rooms/dm` |
| POST | `/chat/rooms/group` |
| GET | `/chat/task-rooms/{task_id}` |
| POST | `/chat/rooms/{room_id}/members` |
| POST | `/chat/messages/{message_id}/attachments` |
| GET | `/attachments/{attachment_id}/file` |
| GET | `/feed/posts` |
| GET | `/feed/announcements` |
| POST | `/feed/posts` |
| PATCH | `/feed/posts/{post_id}` |
| DELETE | `/feed/posts/{post_id}` |
| POST | `/feed/posts/{post_id}/like` |
| POST | `/feed/posts/{post_id}/ack` |
| GET | `/feed/posts/{post_id}/ack-status` |
| POST | `/feed/posts/{post_id}/attachments` |
| GET | `/feed/attachments/{attachment_id}/file` |
| GET | `/feed/posts/{post_id}/comments` |
| POST | `/feed/posts/{post_id}/comments` |
| PATCH | `/feed/comments/{comment_id}` |
| DELETE | `/feed/comments/{comment_id}` |
| GET | `/feed/comments/{comment_id}/attachments` |
| GET | `/calendar/events` |
| GET | `/calendar/month` |
| GET | `/calendar/events/{event_id}` |
| POST | `/calendar/events/{event_id}/invitations/ack` |
| POST | `/calendar/events` |
| PATCH | `/calendar/events/{event_id}` |
| GET | `/knowledge/documents` |
| POST | `/knowledge/documents` |
| PATCH | `/knowledge/documents/{doc_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 48. `admin_staff_announcement_policy`
- **Backend:** `src/api/v1/routers/admin_staff_announcement_policy.py`
- **APIRouter prefix:** `/admin/staff`
- **Frontend search hint:** `rg staff frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/feed/announcements/publish-policy` |
| PUT | `/feed/announcements/publish-policy` |
| GET | `/feed/announcements/publish-policy/audit` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 49. `patient_chat`
- **Backend:** `src/api/v1/routers/patient_chat.py`
- **APIRouter prefix:** `/patient/chat`
- **Frontend search hint:** `rg 'patient_chat' frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `chat_rate_limited_total`
  - `chat_upload_rejected_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/conversation` |
| GET | `/conversation/messages` |
| POST | `/conversation/messages` |
| POST | `/conversation/messages/upload` |
| GET | `/attachments/{attachment_id}/file` |
| DELETE | `/conversation/messages/{message_id}` |
| POST | `/conversation/mark-read` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_patient_chat.py`

---

## 50. `patient_notification_settings`
- **Backend:** `src/api/v1/routers/patient_notification_settings.py`
- **APIRouter prefix:** `/patient`
- **Frontend search hint:** `rg 'patient_notification_settings' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/notification-settings` |
| PUT | `/notification-settings` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 51. `public_services`
- **Backend:** `src/api/v1/routers/public_services.py`
- **APIRouter prefix:** `/public/clinics`
- **Frontend search hint:** `rg 'public_services' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/services` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 52. `public_marketing`
- **Backend:** `src/api/v1/routers/public_marketing.py`
- **APIRouter prefix:** `/public/clinics`
- **Frontend search hint:** `rg 'public_marketing' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/feed` |
| GET | `/{clinic_id}/stories` |
| POST | `/{clinic_id}/leads` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 53. `public_doctor_profiles`
- **Backend:** `src/api/v1/routers/public_doctor_profiles.py`
- **APIRouter prefix:** `/public/clinics`
- **Frontend search hint:** `rg 'public_doctor_profiles' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/by-slug/{clinic_slug}/doctors/{doctor_slug}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_public_doctor_profiles.py`

---

## 54. `patients`
- **Backend:** `src/api/v1/routers/patients.py`
- **APIRouter prefix:** `/patients`
- **Frontend search hint:** `rg 'patients' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| GET | `/{patient_id}` |
| POST | `(root)` |
| PUT | `/{patient_id}` |
| DELETE | `/{patient_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 55. `schedule`
- **Backend:** `src/api/v1/routers/schedule.py`
- **APIRouter prefix:** `/doctors`
- **Frontend search hint:** `rg 'schedule' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{doctor_id}/schedule` |
| GET | `/admin/{doctor_id}/schedule` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_p2_clients_schedule.py`
- `tests/api/test_schedule.py`

---

## 56. `bookings`
- **Backend:** `src/api/v1/routers/bookings.py`
- **APIRouter prefix:** `(see decorators — no APIRouter prefix)`
- **Frontend search hint:** `rg 'bookings' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/patient/bookings` |
| POST | `/patient/bookings` |
| DELETE | `/patient/bookings/{booking_id}` |
| GET | `/admin/bookings/{booking_id}/checkout-info` |
| GET | `/admin/bookings/{booking_id}/card` |
| GET | `/admin/bookings` |
| POST | `/admin/bookings` |
| PUT | `/admin/bookings/{booking_id}/cancel` |
| PUT | `/admin/bookings/{booking_id}/complete` |
| PUT | `/admin/bookings/{booking_id}/complete/retry` |
| PUT | `/admin/bookings/{booking_id}/mark-no-show` |
| PATCH | `/admin/bookings/{booking_id}` |
| PUT | `/admin/bookings/{booking_id}/reschedule` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_bookings.py`

---

## 57. `payments`
- **Backend:** `src/api/v1/routers/payments.py`
- **APIRouter prefix:** `/payments`
- **Frontend search hint:** `rg 'payments' frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `payment_webhook_failures_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `(root)` |
| POST | `/webhook` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_payments.py`

---

## 58. `csv_sync`
- **Backend:** `src/api/v1/routers/csv_sync.py`
- **APIRouter prefix:** `(see decorators — no APIRouter prefix)`
- **Frontend search hint:** `rg 'csv_sync' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/schedule/import-csv` |
| GET | `/bookings/export-csv` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 59. `reports`
- **Backend:** `src/api/v1/routers/reports.py`
- **APIRouter prefix:** `/reports`
- **Frontend search hint:** `rg 'reports' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/dashboard` |
| GET | `/no-show` |
| GET | `/revenue` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_reports_erp_endpoints.py`
- `tests/services/test_erp_reports_repository.py`

---

## 60. `admin_omni_chat`
- **Backend:** `src/api/v1/routers/admin_omni_chat.py`
- **APIRouter prefix:** `/admin/omni-chats`
- **Frontend search hint:** `rg omni-chats frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `(`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/sse-token` |
| GET | `/events` |
| GET | `/quick-replies` |
| POST | `/quick-replies` |
| PATCH | `/quick-replies/{reply_id}` |
| DELETE | `/quick-replies/{reply_id}` |
| GET | `(root)` |
| POST | `/{chat_id}/claim` |
| POST | `/{chat_id}/presence` |
| POST | `/{chat_id}/close` |
| POST | `/{chat_id}/resolve` |
| GET | `/analytics` |
| GET | `/{chat_id}` |
| PATCH | `/{chat_id}` |
| GET | `/{chat_id}/messages` |
| POST | `/{chat_id}/messages` |
| POST | `/{chat_id}/messages/upload` |
| GET | `/{chat_id}/messages/{message_id}/attachments/{attachment_id}/file` |
| POST | `/{chat_id}/ai-mode` |
| POST | `/{chat_id}/messages/{message_id}/hide` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_lead_logs_stats.py`
- `tests/api/test_admin_omni_chat.py`

---

## 61. `admin_omni_chat_closure_tags`
- **Backend:** `src/api/v1/routers/admin_omni_chat_closure_tags.py`
- **APIRouter prefix:** `/admin/omni-chat-closure-tags`
- **Frontend search hint:** `rg omni-chat-closure-tags frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PATCH | `/{tag_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 62. `integrations_gateway`
- **Backend:** `src/api/v1/routers/integrations_gateway.py`
- **APIRouter prefix:** `(see decorators — no APIRouter prefix)`
- **Frontend search hint:** `rg 'integrations_gateway' frontend/src --glob '*.ts*'`
- **Prometheus / `src.core.metrics` symbols used in this file:**
  - `auth_captcha_required_total`
  - `auth_captcha_verified_total`

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/integrations/webhooks/telegram` |
| POST | `/webchat/messages` |
| GET | `/webchat/poll` |
| POST | `/integrations/webhooks/whatsapp` |
| POST | `/integrations/webhooks/vk` |
| POST | `/integrations/webhooks/instagram` |
| POST | `/integrations/webhooks/email` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_integrations_gateway.py`
- `tests/api/test_integrations_gateway_whatsapp.py`

---

## 63. `owner_omni_channels`
- **Backend:** `src/api/v1/routers/owner_omni_channels.py`
- **APIRouter prefix:** `/owner/channels`
- **Frontend search hint:** `rg 'owner_omni_channels' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| POST | `(root)` |
| PUT | `/{channel_id}` |
| POST | `/{channel_id}/credentials` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_owner_omni_channels.py`

---

## 64. `owner_omni_ai_settings`
- **Backend:** `src/api/v1/routers/owner_omni_ai_settings.py`
- **APIRouter prefix:** `/owner/omni-ai-settings`
- **Frontend search hint:** `rg 'owner_omni_ai_settings' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |
| PUT | `(root)` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_owner_omni_ai_settings.py`

---

## 65. `owner_omni_audit`
- **Backend:** `src/api/v1/routers/owner_omni_audit.py`
- **APIRouter prefix:** `/owner/audit-log`
- **Frontend search hint:** `rg 'owner_omni_audit' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `(root)` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_owner_omni_audit.py`

---

## 66. `admin_loyalty`
- **Backend:** `src/api/v1/routers/admin_loyalty.py`
- **APIRouter prefix:** `/admin/loyalty`
- **Frontend search hint:** `rg loyalty frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/packages` |
| POST | `/packages` |
| PATCH | `/packages/{package_id}` |
| DELETE | `/packages/{package_id}` |
| GET | `/customer-subscriptions` |
| GET | `/customer-subscriptions/{subscription_id}` |
| POST | `/customer-subscriptions/{subscription_id}/family-members` |
| DELETE | `/customer-subscriptions/{subscription_id}/family-members/{patient_id}` |
| GET | `/family-links` |
| POST | `/family-links` |
| PATCH | `/family-links/{link_id}` |
| POST | `/family-links/{link_id}/deactivate` |
| GET | `/wallets` |
| GET | `/wallets/{wallet_id}/transactions` |
| GET | `/subscription-usages` |
| GET | `/summary-by-contact` |
| GET | `/policy` |
| POST | `/policy` |
| PATCH | `/policy` |
| GET | `/campaign-settings` |
| PATCH | `/campaign-settings` |
| POST | `/campaigns/run` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_loyalty.py`
- `tests/api/test_admin_loyalty_summary_by_contact.py`

---

## 67. `patient_loyalty`
- **Backend:** `src/api/v1/routers/patient_loyalty.py`
- **APIRouter prefix:** `/patient/loyalty`
- **Frontend search hint:** `rg 'patient_loyalty' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/me` |
| GET | `/history` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 68. `admin_forms`
- **Backend:** `src/api/v1/routers/admin_forms.py`
- **APIRouter prefix:** `/admin/forms`
- **Frontend search hint:** `rg forms frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/export` |
| POST | `/send-link` |
| GET | `/templates` |
| POST | `/templates` |
| PATCH | `/templates/{template_id}` |
| GET | `/submissions` |
| GET | `/submissions/{submission_id}` |
| PATCH | `/submissions/{submission_id}/revoke` |
| PATCH | `/submissions/{submission_id}/cancel` |
| POST | `/submissions/test-submit` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_forms.py`

---

## 69. `patient_forms`
- **Backend:** `src/api/v1/routers/patient_forms.py`
- **APIRouter prefix:** `/patient/forms`
- **Frontend search hint:** `rg 'patient_forms' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/pending` |
| POST | `/{template_code}/submit` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_patient_forms.py`

---

## 70. `admin_search`
- **Backend:** `src/api/v1/routers/admin_search.py`
- **APIRouter prefix:** `/admin`
- **Frontend search hint:** `rg /admin frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/search` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 71. `ai_agent`
- **Backend:** `src/api/v1/routers/ai_agent.py`
- **APIRouter prefix:** `/ai`
- **Frontend search hint:** `rg 'ai_agent' frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/agent` |
| POST | `/generate-offers` |

### Tests (files under `tests/` mentioning this module)

- `tests/security/test_ai_agent_security.py`

---

## 72. `admin_retention`
- **Backend:** `src/api/v1/routers/admin_retention.py`
- **APIRouter prefix:** `/admin/clinics`
- **Frontend search hint:** `rg clinics frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/{clinic_id}/retention/segments` |
| GET | `/{clinic_id}/retention/campaigns/{campaign_id}/roi` |
| GET | `/{clinic_id}/media` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 73. `admin_vault`
- **Backend:** `src/api/v1/routers/admin_vault.py`
- **APIRouter prefix:** `/admin`
- **Frontend search hint:** `rg /admin frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `/export` |
| GET | `/export/status` |
| GET | `/export/download/{task_id}` |
| POST | `/backup/request` |
| GET | `/backup/status` |
| GET | `/backup/download/{task_id}` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 74. `admin_ui_events`
- **Backend:** `src/api/v1/routers/admin_ui_events.py`
- **APIRouter prefix:** `/admin/ui-events`
- **Frontend search hint:** `rg ui-events frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| POST | `(root)` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 75. `admin_omni_tools`
- **Backend:** `src/api/v1/routers/admin_omni_tools.py`
- **APIRouter prefix:** `/admin/omni`
- **Frontend search hint:** `rg omni frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/available-tools` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---

## 76. `admin_rbac_management`
- **Backend:** `src/api/v1/routers/admin_rbac_management.py`
- **APIRouter prefix:** `/admin/rbac`
- **Frontend search hint:** `rg rbac frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/catalog` |
| POST | `/roles` |
| DELETE | `/roles/{role_id}` |
| GET | `/users` |
| PATCH | `/roles/{role_id}/permissions` |
| PATCH | `/users/{user_id}/roles` |
| PATCH | `/users/{user_id}/permissions` |
| GET | `/policies` |
| PATCH | `/policies` |
| GET | `/audit` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_rbac_management.py`

---

## 77. `admin_lead_logs`
- **Backend:** `src/api/v1/routers/admin_lead_logs.py`
- **APIRouter prefix:** `/admin/lead-logs`
- **Frontend search hint:** `rg lead-logs frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/stats` |
| GET | `(root)` |
| GET | `/{log_id}` |

### Tests (files under `tests/` mentioning this module)

- `tests/api/test_admin_lead_logs_stats.py`

---

## 78. `admin_leads_log_routing`
- **Backend:** `src/api/v1/routers/admin_leads_log_routing.py`
- **APIRouter prefix:** `/admin/leads-log`
- **Frontend search hint:** `rg leads-log frontend/src --glob '*.ts*'`
- **Metrics:** *(no direct `src.core.metrics` import in this router file; HTTP still counted by global middleware if enabled)*

### HTTP routes (decorator paths only)

| Method | Path |
|--------|------|
| GET | `/routing-rules` |
| PUT | `/routing-rules` |
| POST | `/routing-rules/simulate` |

### Tests (files under `tests/` mentioning this module)

- *(no pytest file matched — add coverage or document gap)*

---
