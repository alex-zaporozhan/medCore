## DEV_PROMPTS_RBAC_AND_TASKS — RBAC и Task Management

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `ARCH_RBAC_AND_TASKS.md`, `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`, `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`.

---

## 1. Цели реализации

- **RBAC:**
  - вынести роли и права в явную модель БД (`Role`, `Permission`, `RolePermission`, `UserRole`);
  - заменить разрозненные `if role == ...` на централизованные проверки `require_permissions(...)`;
  - подготовить основу для разграничения доступа к новым модулям (Finance, Tasks, Marketing Attribution, Paperless и т.д.).
- **Tasks:**
  - ввести единый домен задач (`Task`, `TaskComment`);
  - связать задачи с ключевыми доменами (Booking, LeadCard, Inventory, Patient и др.);
  - обеспечить создание задач:
    - вручную из UI;
    - автоматически по событиям (без AI);
    - автоматически через AI Task Generator (`source="ai_auto"`).

---

## 2. Backend — модель данных и миграции

### 2.1. Сущности RBAC

- Добавить в `src/domain/entities/`:
  - `role.py`
  - `permission.py`
  - `role_permission.py`
  - `user_role.py`

Опираться на поля и инварианты из `ARCH_RBAC_AND_TASKS.md`:

- `Role`:
  - `id`, `clinic_id | None`, `code`, `name`, `description`.
- `Permission`:
  - `id`, `code`, `description`.
- `RolePermission`:
  - `id`, `role_id`, `permission_id`.
- `UserRole`:
  - `id`, `user_id`, `role_id`, `clinic_id`.

### 2.2. Сущности задач

- Добавить в `src/domain/entities/`:
  - `task.py`
  - `task_comment.py`

Состав полей — по разделу 3 `ARCH_RBAC_AND_TASKS.md` (статусы, приоритеты, связи с доменами, `source`, `source_event_id` и т.д.) с обязательным `clinic_id`.

### 2.3. Миграции Alembic

- Создать миграцию, которая добавит таблицы:
  - `roles`, `permissions`, `role_permissions`, `user_roles`;
  - `tasks`, `task_comments`.
- Для всех таблиц:
  - индексы по `clinic_id`;
  - индексы по часто используемым фильтрам:
    - `tasks`: `clinic_id + status`, `clinic_id + assignee_id`, `clinic_id + role_assignee`, `clinic_id + due_at`.

### 2.4. Инициализация базовых ролей и прав

- В той же миграции или отдельной seeding‑миграции:
  - создать базовые `Role` по `ARCH_RBAC_AND_TASKS.md`:
    - `owner`, `manager`, `admin`, `doctor`;
  - создать `Permission`:
    - для основных разделов и действий:
      - `view_dashboard`, `view_reports`;
      - `view_finance`, `manage_finance`;
      - `view_payroll`, `manage_payroll`;
      - `view_inventory`, `manage_inventory`;
      - `view_crm`, `manage_crm`;
      - `view_tasks`, `manage_tasks`, `assign_tasks`;
      - `view_loyalty`, `manage_loyalty`;
      - `view_forms`, `manage_forms`;
      - `view_marketing_analytics`, `manage_marketing_campaigns`;
      - `view_ai_settings`, `manage_ai_settings`;
  - заполнить `RolePermission` по матрице из ARCH (Owner имеет все права, Manager — без глобальных/критичных настроек, Admin — без финансов/настроек, Doctor — только свои данные).

### 2.5. Миграция существующих пользователей

- Предусмотреть шаг миграции текущих `AdminUser`/врачей:
  - на Phase 1:
    - маппинг существующих флагов/ролей на новые `Role`:
      - бывший «superadmin» → `owner` или `manager`;
      - текущие администраторы смен → `admin`;
      - пользователи‑врачи → `doctor`;
  - создать соответствующие записи `UserRole` для каждой клиники, где у пользователя есть доступ.

---

## 3. Backend — сервис `rbac_service`

### 3.1. Репозиторий и сервис

- В `src/domain/interfaces/repositories/`:
  - `rbac_repository.py` (доступ к ролям, правам, привязкам пользователей).
- В `src/infrastructure/database/`:
  - `RbacRepositoryImpl`.
- В `src/application/services/`:
  - `rbac_service.py`:
    - методы:
      - `get_roles_for_user(user_id, clinic_id)`;
      - `get_permissions_for_user(user_id, clinic_id)`;
      - `user_has_any_permission(user_id, clinic_id, permission_codes: list[str]) -> bool`.

### 3.2. Расширение контекста пользователя

- Обновить существующий `AdminContext`/`CurrentUser` (см. TECH_PASSPORT_BACKEND):
  - добавить:
    - `roles: list[str]`;
    - `permissions: list[str]`;
    - метод `has_any_permission(codes: Iterable[str]) -> bool`.
- В зависимостях `get_current_admin_with_roles`:
  - подгружать роли/права через `rbac_service`.

### 3.3. Dependency `require_permissions`

- В `src/api/v1/dependencies.py` реализовать фабрику:

```python
def require_permissions(*permission_codes: str):
    async def dependency(current_admin: AdminContext = Depends(get_current_admin_with_roles)):
        if not current_admin.has_any_permission(permission_codes):
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_admin
    return dependency
```

- Применить `require_permissions`:
  - для новых роутеров (ERP, Loyalty, Attribution, Tasks);
  - постепенно заменить «ручные» проверки ролей там, где это безопасно в рамках V2.

### 3.4. Явная матрица прав для ключевых модулей

- Зафиксировать в коде/константах (и использовать в миграции):
  - `Finance & ERP`:
    - просмотр (`admin_finance`, `admin_payroll`, `admin_inventory`) → `view_finance`/`view_payroll`/`view_inventory`;
    - изменение касс/политик/склада → `manage_finance`/`manage_payroll`/`manage_inventory`.
  - `CRM & Sales`:
    - листинг/детали → `view_crm`;
    - изменение стадий/заметок → `manage_crm`.
  - `Tasks`:
    - просмотр задач → `view_tasks`;
    - создание/назначение другим → `manage_tasks`, `assign_tasks`.
  - `Loyalty`:
    - просмотр пакетов/кошельков → `view_loyalty`;
    - управление политиками/пакетами → `manage_loyalty`.
  - `Paperless`:
    - просмотр форм/подписей → `view_forms`;
    - управление шаблонами → `manage_forms`.
  - `Marketing Attribution`:
    - отчёты → `view_marketing_analytics`;
    - управление кампаниями → `manage_marketing_campaigns`.

---

## 4. Backend — сервис `task_service` и события

### 4.1. Репозиторий задач

- В `src/domain/interfaces/repositories/`:
  - `task_repository.py`.
- В `src/infrastructure/database/`:
  - `TaskRepositoryImpl`.

### 4.2. Сервис задач

- В `src/application/services/task_service.py`:
  - методы:
    - `create_task(...)`;
    - `update_task_status(task_id, status, completed_at?)`;
    - `reassign_task(task_id, assignee_id | role_assignee)`;
    - `add_comment(task_id, author_id, text)`;
    - `list_tasks(filters, pagination)`;
    - `get_task_details(task_id)`.

### 4.3. Интеграция с EventBus (системные задачи)

- Добавить обработчики для ключевых доменных событий (без AI):
  - примеры из `ARCH_RBAC_AND_TASKS.md`:
    - отсутствие PayrollPolicy/Cashbox;
    - отменённые записи;
    - низкие остатки материалов;
    - лиды без движения.
- Обработчики:
  - принимают события;
  - через `task_service.create_task` создают задачи с `source="system"` и заполненными привязками (`booking_id`, `lead_id`, `inventory_product_id` и т.п.).

---

## 5. AI Task Generator (Celery Beat)

### 5.1. Периодический джоб

- Создать Celery‑таску `run_ai_task_generator` (см. раздел 5 ARCH):
  - периодичность: раз в сутки (конфигурируемо).

### 5.2. Подготовка входных данных

- Внутри задачи:
  - собрать «аномалии» за период:
    - отмены, no‑show, пустые окна, лиды без движения, ERP‑аномалии и т.д.;
  - сформировать структурированный `json`‑payload (как в примере в ARCH).

### 5.3. Вызов AI и создание задач

- Через `AiClient` (отдельная модель/конфиг для аналитики):
  - отправить промпт и структурированный вход;
  - получить список предложенных задач (формат — по примеру из ARCH).
- Для каждой предложенной задачи:
  - провалидировать данные;
  - создать `Task` с `source="ai_auto"`;
  - при необходимости добавить записи в `AttentionFeed`.

### 5.4. Флаги и безопасность

- В настройках клиники:
  - `ai_tasks_enabled: bool`;
  - уровень автоматизации (только предложения vs автосоздание).
- При выключенном флаге:
  - Celery‑таска завершает работу без вызова AI.

---

## 6. Backend — API `admin_tasks`

### 6.1. Роутер

- Создать `src/api/v1/routers/admin_tasks.py`.
- Эндпоинты (по ARCH):
  - `GET /api/v1/admin/tasks` — список задач (фильтры: статус, исполнитель, роль, доменные связи, сроки);
  - `GET /api/v1/admin/tasks/{id}` — детали + комментарии;
  - `POST /api/v1/admin/tasks` — ручное создание задачи;
  - `PATCH /api/v1/admin/tasks/{id}` — изменение статуса/исполнителя/срока;
  - `POST /api/v1/admin/tasks/{id}/comments` — добавление комментария.

### 6.2. RBAC‑ограничения

- Использовать `require_permissions`:
  - просмотр: `view_tasks`;
  - управление/назначение: `manage_tasks`, `assign_tasks`.
- Правило видимости для `Doctor`:
  - фильтровать по `assignee_id` = текущий пользователь или `role_assignee="doctor"`.

---

## 7. Задачи из OmniChat и AI‑агента

- **TODO:**
  1. Добавить в API/сервисах удобный способ создавать задачи из контекста Omnichannel:
     - метод `create_task_from_conversation(...)` или использование существующего `create_task`, но с:
       - автозаполнением `booking_id`, `patient_id`, `lead_id` по текущему чату;
       - установкой `source="manual"` или `source="ai_suggested"`.
  2. На стороне Omnichannel‑фронта:
     - добавить кнопку «Создать задачу» в правой панели:
       - форма создания сразу привязывает задачу к текущему пациенту/лиду/визиту.
  3. Для AI‑агента:
     - предусмотреть использование `task_service.create_task(...)` из оркестратора или отдельного обработчика:
       - при ситуациях, когда агент не может завершить сценарий сам (сложные конфликты, жалобы и т.п.);
       - задачи помечаются `source="ai_auto"` или `source="ai_suggested"`.

---

## 8. Frontend — `AdminTasksPage` и виджеты

### 8.1. Страница задач

- Добавить страницу `AdminTasksPage` в раздел `Tasks` (см. ARCH_FRONTEND_BUSINESS_OS_UX):
  - слева: фильтры по статусам, ролям, исполнителям, срокам;
  - центр: Kanban по статусам или таблица задач;
  - справа: панель деталей задачи (описание, комментарии, привязки к доменам, история изменений).

### 8.2. Типы и хуки

- В `frontend/src/api/types.ts`:
  - DTO `Task`, `TaskComment`, фильтры и ответы листинга.
- В `frontend/src/hooks/`:
  - `useTasks`, `useTaskDetails`, `useCreateTask`, `useUpdateTask`, `useCreateTaskComment`.

### 8.3. Встраивание в другие экраны

- На главной (Dashboard):
  - виджет «Задачи на сегодня» (top‑N задач по текущему пользователю).
- В CRM, OmniChat, Patient‑карточке:
  - контекстные виджеты задач:
    - список задач по `lead_id`/`patient_id`/`booking_id`;
    - кнопка «Создать задачу» с автозаполнением связей.

---

## 9. Тестирование

### 9.1. Backend

- Юнит‑тесты:
  - `rbac_service` — корректная сборка ролей/прав, проверка `has_any_permission`;
  - `task_service` — создание/обновление/фильтрация задач, комментарии.
- Интеграционные:
  - сценарии автоматических задач по событиям (отмена записи, отсутствие PayrollPolicy и т.д.);
  - сценарий AI Task Generator с mock‑AiClient.

### 9.2. Тесты на отказ в доступе (403)

- Для каждого критичного модуля (Finance, Payroll, Inventory, CRM, Tasks, Loyalty, Forms, Marketing Attribution):
  - написать тесты, эмулирующие:
    - запрос без авторизации → 401;
    - авторизованный пользователь без нужного `Permission` → 403 (через `require_permissions`);
    - пользователь с нужным `Permission` → 200 и ожидаемый результат.
- Зафиксировать, что добавление/изменение endpoint‑ов сопровождается покрытием соответствующими RBAC‑тестами.

### 9.3. Frontend

- Тесты UI:
  - корректное отображение задач и фильтров;
  - изменение статуса/исполнителя обновляет список и вызывает правильные API‑запросы.

---

## 10. Порядок выполнения для @DEV

1. Реализовать доменные сущности и миграции для RBAC и Tasks (включая seeding базовых ролей/прав).
2. Реализовать `rbac_service`, матрицу прав и интегрировать `require_permissions` в новые/ключевые роутеры.
3. Добавить миграцию существующих пользователей в новые роли (`UserRole`).
4. Реализовать `task_service`, репозиторий и базовые обработчики событий (системные задачи).
5. Добавить Celery‑джоб AI Task Generator и конфигурацию флагов клиники.
6. Реализовать API `admin_tasks` с проверками RBAC.
7. Реализовать создание задач из OmniChat и/или AI‑агента с автопривязкой к пациенту/лиду/визиту.
8. Реализовать `AdminTasksPage` и виджеты задач на фронтенде.
9. Написать и прогнать backend и frontend тесты (включая 403‑сценарии для критичных модулей).

