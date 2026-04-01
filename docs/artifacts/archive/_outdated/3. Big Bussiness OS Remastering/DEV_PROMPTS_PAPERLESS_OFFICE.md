## DEV_PROMPTS_PAPERLESS_OFFICE — Digital Forms, E‑Sign, EMR

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `ARCH_PAPERLESS_OFFICE.md`, `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`, `ARCH_RBAC_AND_TASKS.md`.

---

## 1. Цели реализации

- Убрать бумажные анкеты и согласия:
  - цифровые формы (`DigitalFormTemplate`, `DigitalFormSubmission`);
  - электронная подпись (`ESignature`);
  - хранение и просмотр в админке и PWA.
- Связать формы с пациентами/визитами:
  - `PatientProfile`, `VisitNote`;
  - интеграция с Recall и AI (только факты, без утечки ПДн в LLM).

---

## 2. Backend — модель данных и миграции

### 2.1. DigitalFormTemplate и DigitalFormSubmission

- В `src/domain/entities/`:
  - `digital_form_template.py`
  - `digital_form_submission.py`

- Поля — по `ARCH_PAPERLESS_OFFICE.md` (clinic_id, code, version, schema, requires_signature, active, связи с patient/booking и т.д.).
- `schema`:
  - минимальный собственный формат, который удобно парсить на фронте (или подмножество JSON Schema):
    - список полей с ключами:
      - `id: str`
      - `label: str`
      - `type: str` (`text`, `textarea`, `number`, `select`, `checkbox`, `date`, и т.п.)
      - `required: bool`
      - `options?: list[str]` (для select/checkbox‑групп)
      - `sensitive: bool` — признак чувствительного поля (ПДн/медицинские данные), не попадающего в AI‑контекст.

### 2.2. ESignature

- В `src/domain/entities/`:
  - `e_signature.py`
  - поля: clinic_id, patient_id, digital_form_submission_id, signed_at, signer_name/role, signature_type, signature_payload, meta.

### 2.3. VisitNote / PatientProfile

- В зависимости от текущей реализации:
  - либо расширить существующие `Patient`/`Booking`;
  - либо добавить новые сущности:
    - `patient_profile.py`
    - `visit_note.py`
  - по структуре из ARCH (note, attachments, связи с Booking/Patient).

### 2.4. Alembic‑миграции

- Добавить таблицы:
  - `digital_form_templates`, `digital_form_submissions`, `e_signatures`;
  - при необходимости — `patient_profiles`, `visit_notes`.
- Индексы:
  - по `clinic_id`;
  - по `patient_id`, `booking_id` для быстрых выборок истории.

---

## 3. Backend — сервисы и валидация форм

### 3.1. `forms_service`

- В `src/application/services/forms_service.py`:
  - операции:
    - управление шаблонами:
      - CRUD `DigitalFormTemplate` (ограничение по `clinic_id`);
    - приём и валидация отправленных форм:
      - `submit_form(template_code, patient_id | booking_id, data, signature_payload?, ctx)`:
        - загрузить актуальный активный шаблон по `clinic_id + code`;
        - провалидировать `data` по `schema` (JSON‑валидация);
        - создать `DigitalFormSubmission`;
        - если `requires_signature=True` — создать `ESignature`.

### 3.2. Интеграция с Patient/Booking

- При создании/подтверждении `Booking`:
  - иметь возможность запросить список «ожидаемых» форм (например, анкета здоровья и согласия).
- При загрузке карточки пациента:
  - давать API для получения списка шаблонов/отправленных форм.

---

## 4. Backend — API `admin_forms` и `patient_forms`

### 4.1. `admin_forms.py`

- Новый роутер:
  - `GET /api/v1/admin/forms/templates` — список `DigitalFormTemplate` по клинике;
  - `POST /api/v1/admin/forms/templates` — создание/обновление шаблона;
  - `GET /api/v1/admin/forms/submissions` — фильтрация по пациенту/визиту/типу;
  - `GET /api/v1/admin/forms/submissions/{id}` — детали формы (+ подпись).
- RBAC:
  - доступ только ролям с соответствующими правами (см. `ARCH_RBAC_AND_TASKS.md`), например:
    - просмотр: `view_forms`;
    - управление: `manage_forms`.

### 4.2. `patient_forms.py`

- Новый роутер:
  - `GET /api/v1/patient/forms/pending`:
    - список форм, которые нужно заполнить перед визитом/первичным приёмом;
  - `POST /api/v1/patient/forms/{template_code}/submit`:
    - отправка заполненной формы и подписи.

---

## 5. Frontend — Paperless Office

### 5.1. Админка: раздел «Формы и документы»

- В разделе Settings (см. ARCH_FRONTEND_BUSINESS_OS_UX):
  - список шаблонов форм:
    - таблица `DigitalFormTemplate` (code, name, version, active, requires_signature);
    - форма создания/редактирования (drawer) с редактором `schema` (простая форма + raw JSON).
  - список отправленных форм:
    - фильтры по пациенту/визиту/типу;
    - просмотр деталей (данные и подпись).
- Типы/хуки:
  - DTO для шаблонов, сабмишенов, сигнатур в `frontend/src/api/types.ts`;
  - `useFormTemplates`, `useFormSubmissions`, `useFormSubmissionDetails`, `useUpsertFormTemplate`.

### 5.2. PWA пациента: «Анкеты и согласия»

- Новый экран:
  - список ожидающих форм (`pending`);
  - история ранее подписанных документов (короткие карточки с датами);
  - форма заполнения с:
    - генерацией полей по `schema`;
    - компонентом электронной подписи (canvas или готовый компонент).

### 5.3. OmniChat: виджет статуса форм

- В правой панели OmniChat (см. ARCH_FRONTEND_BUSINESS_OS_UX):
  - виджет:
    - список обязательных форм для пациента (заполнены/не заполнены);
    - быстрые действия:
      - «Отправить ссылку на анкету в чат»;
      - «Открыть последнюю анкету/согласие».

---

## 6. Экспорт форм и подписей

- **TODO:**
  1. Реализовать backend‑механику защищённого экспорта:
     - endpoint или служебный скрипт для выгрузки форм/подписей:
       - по пациенту;
       - по периоду;
       - по типу формы (анкеты/согласия).
     - формат экспорта:
       - PDF или zip‑архив с JSON‑данными + вложенными файлами.
  2. Ограничить доступ к экспорту через RBAC:
     - только роли уровня `Owner` (и, при необходимости, юридически ответственные лица);
  3. Залогировать операции экспорта:
     - кто, когда и что выгрузил (ID пациента/клиники, диапазон дат).

---

## 7. ПДн и безопасность

- При работе с формами:
  - гарантировать, что их содержимое **не** уходит во внешние LLM:
    - Ai‑интеграции используют только факты (есть/нет согласия, дата/версия), а не текст полей;
    - в `AiSanitizer` при формировании контекста:
      - ориентироваться на `schema.sensitive`:
        - поля с `sensitive=True` никогда не включать в промпт;
        - для остальных полей — минимизировать детализацию по политике ПДн;
      - обезличивать любые свободные текстовые поля, если политика запрещает передачу ПДн.
- Доступ к формам/подписям:
  - ограничить через RBAC:
    - отдельные права `view_forms`, `manage_forms`, возможно `view_medical_notes`.
- Файлы (фото, вложения из `VisitNote`):
  - хранить во внешнем сторедже (S3/аналог), в БД хранить только ссылки/ID.

---

## 8. Тестирование

### 8.1. Backend

- Юнит‑тесты:
  - валидация данных по `schema` в `forms_service`;
  - корректность создания `DigitalFormSubmission` и `ESignature`.
- Интеграционные:
  - полный поток:
    - админ создаёт шаблон;
    - пациент получает `pending` форму, заполняет и подписывает;
    - форма отображается в админке в привязке к пациенту/визиту.

### 8.2. Frontend

- Проверка:
  - работы конструктора шаблонов и списка отправленных форм;
  - UX‑потока в PWA: отображение списка, заполнение, подпись, успешное завершение.

---

## 9. Порядок выполнения для @DEV

1. Добавить доменные сущности и миграции для DigitalFormTemplate, DigitalFormSubmission, ESignature (+ VisitNote/PatientProfile при необходимости).
2. Реализовать `forms_service` с валидацией по `schema`.
3. Реализовать API `admin_forms` и `patient_forms` с проверками RBAC.
4. Реализовать раздел Settings → «Формы и документы» в админке.
5. Реализовать PWA‑экран пациента «Анкеты и согласия».
6. Добавить виджет статуса форм в правую панель OmniChat.
7. Реализовать безопасный экспорт форм и подписей (endpoint/скрипт + RBAC + логирование).
8. Обеспечить ограничения по ПДн в AI‑интеграциях и покрыть ключевые сценарии тестами.

