# Чек-лист роутеров для SCRIBE (обязательный порядок)

> **Версия:** 2026-04-02  
> **Назначение:** документатор **не** описывает продукт «с нуля по интуиции». Каждое изменение в пользовательских текстах, затрагивающее API или экраны, проходит **по фиксированному списку модулей** в том же порядке, что `api_router.include_router(...)` в `src/api/v1/router.py`.

## 1. Канонические артефакты (читать до правок)

| Артефакт | Зачем |
|----------|--------|
| [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md) | Префиксы и порядок 78 модулей |
| [router_surface/INDEX.md](./router_surface/INDEX.md) | Автогенерация: файлы роутеров, таблица HTTP-путей, импорты метрик, эвристика pytest |
| [FEATURE_KANBAN_AND_TASKS.md](./FEATURE_KANBAN_AND_TASKS.md) | Kanban / задачи / потоки / теги / доски |
| [FEATURE_CHATS_OMNI_PATIENT_STAFF.md](./FEATURE_CHATS_OMNI_PATIENT_STAFF.md) | Омни-инбокс, чат пациента, legacy admin chat, **внутренний** чат персонала |
| [FEATURE_CALENDAR_SCHEDULE.md](./FEATURE_CALENDAR_SCHEDULE.md) | Расписание записи, админ-расписание, календарь персонала |
| [FEATURE_PAYMENTS_FINANCE.md](./FEATURE_PAYMENTS_FINANCE.md) | Платежи, касса / платёжный шлюз, финансы |
| [TESTING_SURFACE.md](./TESTING_SURFACE.md) | Где лежат тесты и как связать с роутерами |
| `frontend/src/routePaths.ts` | Канон URL админки и PWA |
| OpenAPI | `/docs`, `/redoc` у поднятого API (не каталог `docs/` в корне) |

## 2. Порядок работы по одному модулю `N. name`

Для каждого блока `## N. \`name\`` в [router_surface/INDEX.md](./router_surface/INDEX.md):

1. **Бэкенд:** открыть указанный `src/api/v1/routers/{name}.py`; сверить префикс и пути с таблицей в INDEX (если расхождение — перегенерировать INDEX, см. п. 4).
2. **Права:** при описании возможностей для персонала — сверить `require_permissions` и [rbac_router_permissions.txt](./rbac_router_permissions.txt) / матрицу RBAC.
3. **Фронт:** выполнить подсказку «Frontend search hint» из INDEX или найти страницу по `ROUTE_PATHS` / `App.tsx`; не придумывать несуществующие маршруты.
4. **Тесты:** список в INDEX — отправная точка; дополнить по [TESTING_SURFACE.md](./TESTING_SURFACE.md). Если тестов нет — **явно** написать «автопокрытие отсутствует».
5. **Метрики:** перечислить символы из INDEX; глобальные HTTP-гистограммы — [OBSERVABILITY.md](./OBSERVABILITY.md) и `src/main.py` (`/metrics`).
6. **Кросс-модули:** если модуль входит в зону Kanban, чатов, календаря или оплат — обновить соответствующий `FEATURE_*.md`, не дублируя дословно весь INDEX.

## 3. Когда обновлять USER_DOCS и PRODUCT_KNOWLEDGE_BASE

- Любой новый или изменённый **пользовательский** сценарий (кнопка, право, URL): после шагов п. 2 — правка в [USER_DOCS/](./USER_DOCS/) и при необходимости строк в [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) §5.
- **Запрещено:** добавлять в USER_DOCS описание экрана, не пройдя чек-лист для роутеров, от которых экран зависит (хуки к `/api/v1/...`).

## 4. Регенерация автосводки

После изменения `router.py` или любого файла в `src/api/v1/routers/`:

```bash
python scripts/generate_router_surface_docs.py
```

Закоммитить обновлённый `documentation/router_surface/INDEX.md` вместе с кодом или в том же PR.

## 5. Именованный порядок модулей (синхронизировать с `router.py`)

При расхождении с репозиторием — править этот список **и** манифест.

`auth`, `config`, `stickers`, `clinics`, `doctors`, `services`, `admin_services`, `admin_schedule`, `admin_doctor_schedule`, `admin_prepayment`, `admin_waitlist`, `admin_recall`, `admin_marketing`, `admin_reports`, `admin_reports_aggregate`, `admin_marketing_attribution`, `admin_chat`, `admin_channel_configs`, `admin_admins`, `admin_staff_directory`, `admin_staff_profile`, `admin_patient_medical`, `admin_agreement`, `admin_auth`, `admin_client_reference`, `admin_clinics_summary`, `admin_discounts`, `admin_integrations`, `admin_owner_settings`, `admin_notification_policy`, `admin_attention_feed`, `admin_patient_ai`, `admin_ai_settings`, `admin_ai_reports`, `admin_ai_status`, `admin_ai_tasks_settings`, `admin_public_doctor_profiles`, `admin_payment_gateway`, `admin_finance`, `admin_payroll`, `admin_inventory`, `admin_crm`, `admin_tasks`, `admin_task_boards`, `admin_task_streams`, `admin_task_tags`, `admin_staff_collab`, `admin_staff_announcement_policy`, `patient_chat`, `patient_notification_settings`, `public_services`, `public_marketing`, `public_doctor_profiles`, `patients`, `schedule`, `bookings`, `payments`, `csv_sync`, `reports`, `admin_omni_chat`, `admin_omni_chat_closure_tags`, `integrations_gateway`, `owner_omni_channels`, `owner_omni_ai_settings`, `owner_omni_audit`, `admin_loyalty`, `patient_loyalty`, `admin_forms`, `patient_forms`, `admin_search`, `ai_agent`, `admin_retention`, `admin_vault`, `admin_ui_events`, `admin_omni_tools`, `admin_rbac_management`, `admin_lead_logs`, `admin_leads_log_routing`.

---

Reference: [SCRIBE.md](./SCRIBE.md) · [STRUCTURE.md](./STRUCTURE.md)
