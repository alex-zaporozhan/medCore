## ARCH_API_GUARDS — единый слой ACL и защита от IDOR

Основание: `ARCH_HARDENING_ROADMAP.md` (п. 2), `ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md`, `ARCH_CHAT_PATIENT_ADMIN.md`, текущий код `src/api/v1/routers/*`, `src/api/v1/dependencies.py`, `src/api/v1/routers/admin_auth.py`.

**Цель:** зафиксировать единый способ проверки доступа по `clinic_id`/`patient_id`/`owner_id` и устранить разнобой по всему API, чтобы:

- защита от IDOR (Insecure Direct Object Reference) была централизованной;
- все эндпоинты полагались на одни и те же dependency‑guard’ы и сервисные хелперы;
- в коде не появлялись анти‑паттерны вида “доверяем `clinic_id` или `patient_id` из query/path”.

---

## 1. Базовые принципы ACL

1. **Одна клиника на инстанс, но `clinic_id` есть везде.**  
   Даже при single‑clinic, `clinic_id` остаётся обязательным полем в БД и в ACL‑логике (историческая архитектура + подготовка к мультиклинике).

2. **Источники идентичности:**
   - Пациент:
     - идентифицируется по `patient_id` из токена (`sub`, см. `ARCH_AUTH_SESSIONS.md`);
     - `clinic_id` пациента определяется по его записи в БД.
   - Админ:
     - идентифицируется по `admin.id` из токена (`sub`);
     - `clinic_id` берётся из связанной записи `AdminUser` (а на этапе хардонинга — дублируется в токене как клейм, см. `ARCH_AUTH_SESSIONS.md`).

3. **Запрет на доверие к идентификаторам из внешнего ввода:**
   - `clinic_id` никогда не читается из query/path/body как основной источник прав доступа;
   - `patient_id` пациента никогда не берётся из query/path для действий от имени текущего пациента;
   - `owner_id`/`admin_id` для проверок владения берутся из контекста аутентификации, а не из запроса.

4. **Стратегия ответов (404 vs 403):**
   - по умолчанию для IDOR‑чувствительных эндпоинтов, где утечка факта существования ресурса нежелательна, использовать **404** при ошибке доступа (ресурс ведёт себя как “не существует”);
   - **403** использовать там, где факт существования ресурса и так очевиден (например, агрегированные отчёты в админке, не раскрывающие чужие идентификаторы).

---

## 2. Dependency‑guard’ы

Все HTTP‑эндпоинты должны опираться на централизованные dependency‑guard’ы, а не раскодировать токены и не подгружать пользователей вручную.

### 2.1. `get_current_admin` (уже есть, но стандартизируется)

**Расположение:** `src/api/v1/routers/admin_auth.py` (функция `get_current_admin_dependency()` + alias `get_current_admin`).

**Назначение:**

- извлечь Bearer‑токен из заголовка `Authorization`;
- декодировать JWT, проверить:
  - `type == "admin"`;
  - токен не истёк, подпись валидна;
- по `sub` загрузить `AdminUser` из БД;
- вернуть доменную сущность `AdminUser`.

**Требования:**

- не включать в ответ/исключения чувствительные данные токена;
- все admin‑роуты (префикс `/v1/admin`) должны принимать `current_admin: AdminUser = Depends(get_current_admin)` вместо произвольного разбора токена;
- `clinic_id` для ACL в админских эндпоинтах берётся **только из `current_admin.clinic_id`**.

### 2.2. `get_current_admin_optional`

**Назначение:**

- вернуть `AdminUser | None` без генерации 401, если токен отсутствует/некорректен (для "опционально авторизованных" эндпоинтов);
- использовать только там, где это явно описано архитектурой (например, некоторые публичные отчёты или конфиги).

**Требования:**

- не использовать как обход обязательной авторизации;
- при наличии `current_admin is None` эндпоинт сам решает, выдавать ли данные (публичный доступ) или 401/403.

### 2.3. `get_current_patient` (вводится)

**Расположение:** `src/api/v1/dependencies_auth.py` или расширение `src/api/v1/dependencies.py` — отдельный модуль для auth‑зависимостей.

**Назначение:**

- извлечь Bearer‑токен пациента:
  - из заголовка `Authorization` (предпочтительно);
  - либо из cookie/другого канала, если он появится в будущем (расширение без изменения сигнатуры dependency).
- декодировать JWT, проверить:
  - клейм `role == "patient"` (см. `ARCH_AUTH_SESSIONS.md`);
- по `sub` загрузить `Patient` из БД с проверкой `deleted_at is NULL`;
- вернуть доменную сущность `Patient`.

**Требования:**

- dependency **не принимает** `patient_id` из запроса;
- при ошибке токена/отсутствии пациента возвращать 401 с коротким сообщением;
- все patient‑роуты (префикс `/v1/patient`) должны использовать `current_patient: Patient = Depends(get_current_patient)` для авторизованных операций.

### 2.4. `get_current_clinic` / `get_current_clinic_id`

**Назначение:**

- унифицировать доступ к текущей клинике:
  - для patient‑ и admin‑контекста — через их сущности;
  - для системных/безличных эндпоинтов — через `get_default_clinic`.

**Паттерн:**

- для patient‑роутов:
  - `clinic = await patient_service.get_clinic_for_patient(current_patient)` или напрямую через `current_patient.clinic_id`;
- для admin‑роутов:
  - `clinic_id = current_admin.clinic_id`;
- `get_default_clinic` использовать только там, где операция действительно не зависит от конкретного пациента/админа, и явно отмечено в ARCH (например, `auth/send-code` в single‑clinic).

---

## 3. Паттерны проверки сущностей (load + ACL)

Цель — не дублировать ручные проверки `if entity.clinic_id != current_admin.clinic_id: ...` во всех сервисах, а использовать общие хелперы.

### 3.1. Общий хелпер для сущностей клиники

**Интерфейс (пример):**

- `load_entity_for_clinic(repo, entity_id: UUID, clinic_id: UUID) -> Entity`:
  - загружает сущность по `id` и `clinic_id` одновременно;
  - если не нашёл — возвращает `None` или выбрасывает доменное исключение (`NotFound`).

**Реализация:**

- на уровне репозиториев (`ServiceRepository`, `BookingRepository`, `ConversationRepository`, и т.п.) добавить методы:
  - `get_by_id_for_clinic(entity_id, clinic_id)`;
  - или ввести базовый generic‑хелпер в инфраструктурном слое.

**Паттерн использования:**

- Admin‑эндпоинт:
  - получает `current_admin.clinic_id`;
  - вызывает `service.get_entity_for_clinic(entity_id, clinic_id=current_admin.clinic_id)`;
  - если `None` → отдаёт 404 без уточнения, существует ли объект в другой клинике.

### 3.2. Сущности с owner‑связью (пациент)

Для сущностей, принадлежащих конкретному пациенту (история записей, сообщения, настройки и т.п.), вводим паттерн:

- `load_entity_for_patient(entity_id: UUID, patient_id: UUID) -> Entity`:
  - в запросе к БД добавляется фильтр `entity.patient_id == patient_id` (и, опционально, `clinic_id`).
- В patient‑эндпоинтах:
  - использовать `current_patient.id` как источник `patient_id`;
  - **не принимать** `patient_id` из query/path, кроме служебных случаев, описанных в ARCH (например, админ‑поиск).

### 3.3. Chat/booking как пример ACL

Из `ARCH_CHAT_PATIENT_ADMIN.md`:

- все запросы к БД в модуле чата выполняются **только с фильтром по `clinic_id`** из контекста;
- пациент видит только свой `conversation` (`clinic_id`, `patient_id`);
- админ видит только диалоги своей клиники (`clinic_id`).

Этот паттерн применяется и к другим сущностям:

- `bookings`:
  - patient‑API: `Booking.clinic_id == current_patient.clinic_id` и `Booking.patient_id == current_patient.id`;
  - admin‑API: `Booking.clinic_id == current_admin.clinic_id`.
- `services`, `doctors`, `discounts`, `reports` — аналогично, все фильтры по клинике строятся на основе контекста, а не ввода.

---

## 4. Чёрный список анти‑паттернов

Чтобы следующие ревью кода были однозначными, фиксируем явные **анти‑паттерны**, которые нельзя использовать.

1. **Доверие к `clinic_id` из query/path/body**:
   - Плохо: `GET /v1/admin/clinics/{clinic_id}/services` → выборка по переданному `clinic_id` без сравнения с `current_admin.clinic_id`.
   - Правильно: использовать `current_admin.clinic_id` и, если нужен `clinic_id` в пути — сверять их и возвращать 404/403 при несовпадении.

2. **Доверие к `patient_id` из query/path в patient‑контексте:**
   - Плохо: `GET /v1/patient/bookings?patient_id=...` от текущего пациента.
   - Правильно: использовать `current_patient.id` внутри сервиса и не позволять пациенту указывать чужие `patient_id`.

3. **Отсутствие фильтра по `clinic_id` в admin‑поисках:**
   - Плохо: админ‑поиск бронирований/пациентов без условия `Booking.clinic_id == current_admin.clinic_id`.
   - Правильно: всегда добавлять фильтр по клинике из контекста.

4. **Сырой доступ к `Authorization` в эндпоинтах:**
   - Плохо: в каждом роутере парсить токен вручную.
   - Правильно: использовать dependency‑guard’ы `get_current_admin`/`get_current_patient`.

5. **Выдача различимых сообщений при ошибке доступа:**
   - Плохо: возвращать разные ответы для случаев “нет доступа” и “нет такой записи” для чувствительных ресурсов.
   - Правильно: следовать стратегии 404/403 из раздела 1.4.

---

## 5. Таблица роутеров для выравнивания

Этот список служит чек‑листом для @DEV при рефакторинге.

### 5.1. Admin‑роутеры (`/v1/admin/*`)

- `src/api/v1/routers/admin_auth.py`
- `src/api/v1/routers/admin_services.py`
- `src/api/v1/routers/admin_doctors.py` (если есть)
- `src/api/v1/routers/admin_reports.py`
- `src/api/v1/routers/admin_discounts.py`
- `src/api/v1/routers/admin_marketing.py`
- `src/api/v1/routers/admin_notification_policy.py`
- `src/api/v1/routers/admin_client_reference.py`
- `src/api/v1/routers/admin_ai_settings.py`
- `src/api/v1/routers/admin_ai_reports.py`
- `src/api/v1/routers/admin_attention_feed.py`
- `src/api/v1/routers/admin_chat.py`
- `src/api/v1/routers/admin_integrations.py`
- другие `admin_*` роутеры, присутствующие в `src/api/v1/routers`.

**Задача:** убедиться, что:

- в каждом роутере:
  - используется `current_admin = Depends(get_current_admin)` (или `get_current_admin_optional` там, где это явно нужно);
  - все выборки/изменения клинико‑зависимых сущностей фильтруются по `current_admin.clinic_id`;
  - в местах, где в пути есть `clinic_id`, он сверяется с `current_admin.clinic_id`.

### 5.2. Patient‑роутеры (`/v1/patient/*`)

- `src/api/v1/routers/patient_bookings.py` (если есть);
- `src/api/v1/routers/admin_patient_ai.py` (для patient‑ориентированных AI‑ответов через админку, ACL по clinic/patient);
- `src/api/v1/routers/public_services.py` (частично публичный, но с patient‑контекстом там, где он есть);
- `src/api/v1/routers/admin_patient_*` — там, где админ работает с пациентскими данными.

**Задача:** убедиться, что:

- все действия от имени **текущего пациента** используют `get_current_patient` и `current_patient.id`;
- `patient_id` из запроса используется только там, где так задумано (например, в админских эндпоинтах), и всегда проверяется по `clinic_id`.

---

## 6. Выход для @DEV

Этот документ задаёт:

- **контракт dependency‑guard’ов** (`get_current_admin`, `get_current_admin_optional`, `get_current_patient`);
- **паттерны репозиториев и сервисов** для ACL (`load_entity_for_clinic`, `load_entity_for_patient`);
- **чёткий чёрный список анти‑паттернов**, который можно использовать при code review;
- **чек‑лист роутеров**, которые нужно выровнять.

При реализации hardening‑фазы A.2 (@DEV, см. `DEV_PROMPTS_HARDENING_SECURITY_AND_AI.md`) необходимо:

- создать/обновить dependency‑модуль в соответствии с этим документом;
- пройтись по списку роутеров и привести их к единому паттерну ACL/IDOR‑защиты.

