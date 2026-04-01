## DEV_PROMPT: Типы бизнеса, роли и лексика (корневая страница клиник)

> Архитектура и контекст: `ARCH_BUSINESS_TYPES_AND_LEXICON.md`, `ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md`, `DEV_PROMPT_UNIVERSAL_BUSINESS_AND_INTEGRATIONS.md`.
> Цель: сделать страницу `/admin/clinics` центром управления бизнесами (клиниками), добавить конфиг лексики (пациент/клиент, врачи/мастера), связать всё с PWA и гарантировать изоляцию данных по `clinic_id`.

---

### Общие правила для @DEV

- Двигаться по чек‑листу ниже **строго по порядку**, не смешивая несколько крупных пунктов в одном коммите.
- После каждого логически завершённого блока:
  - прогонять миграции в dev/локальном окружении;
  - при необходимости дополнять тесты в `tests/api` и `tests/e2e`.
- Не ломать существующий прод: все новые поля должны иметь дефолты / быть nullable и не нарушать старые DTO.

---

### To‑dos (по шагам)

#### 1. Backend: миграция и DTO клиники

1.1. **Alembic‑миграция для `clinics`**

- Добавить в таблицу `clinics` поля:
  - `person_label_singular TEXT NULL`;
  - `person_label_plural TEXT NULL`;
  - `staff_label_plural TEXT NULL`.
- Создать отдельный файл миграции (последовательность ревизий смотри в `alembic/versions`).

1.2. **Entity `Clinic`**

- Обновить `src/domain/entities/clinic.py`:
  - добавить три новых атрибута с типами `Mapped[str | None]`.

1.3. **DTO `ClinicRead` / `ClinicUpdate` / `ClinicCreate`**

- В `src/application/dto/clinic_dto.py`:
  - `ClinicRead`:
    - добавить поля `person_label_singular: str | None`, `person_label_plural: str | None`, `staff_label_plural: str | None`;
    - добавить поле `business_lexicon: BusinessLexiconRead` (см. 2.1).
  - Создать `BusinessLexiconRead` (см. ARCH):
    - поля: `business_type`, `business_type_custom_name`, `person_label_singular`, `person_label_plural`, `staff_label_plural`, `role_display: dict[str, str]`.
  - `ClinicUpdate`:
    - добавить опциональные поля `business_type`, `business_type_custom_name`, `person_label_singular`, `person_label_plural`, `staff_label_plural`.
  - `ClinicCreate`:
    - оставить лексические поля опциональными (можно не добавлять на create, если не требуется).

1.4. **Расширение словаря ролей специалистов**

- В `src/application/dto/doctor_dto.py` обновить `SpecialistRole`:
  - добавить значения: `"barber"`, `"stylist"`, `"tattoo_master"`, `"massage_therapist"`;
  - сохранить существующие: `"doctor"`, `"nurse"`, `"master"`, `"therapist"`, `"other"`.
- Никаких дополнительных полей в БД не требуется: `specialist_role` уже `TEXT`, новые значения обрабатываются на уровне валидации и лексикона.

#### 2. Backend: словарь лексики и сервис

2.1. **Словарь дефолтов**

- В новом модуле, например `src/application/services/business_lexicon_service.py` (или внутри `clinic_service.py`, если так принято):
  - описать `DEFAULT_BUSINESS_LEXICON` в соответствии с `ARCH_BUSINESS_TYPES_AND_LEXICON.md`.

2.2. **Функция сборки лексикона**

- Реализовать:

```python
def build_business_lexicon(clinic: Clinic) -> BusinessLexiconRead:
    ...
```

- Логика:
  - взять дефолт по `clinic.business_type` (fallback к `"other"`);
  - перекрыть `person_label_*` и `staff_label_plural` значениями из самой клиники, если они заданы;
  - вернуть `BusinessLexiconRead`.

2.3. **Интеграция в `ClinicService`**

- В `src/application/services/clinic_service.py`:
  - при формировании `ClinicRead` (в `get_clinic`, `get_clinics`, `create_clinic`, `update_clinic`):
    - после получения entity `Clinic` вызывать `build_business_lexicon` и передавать его в DTO.

#### 3. Backend: эндпоинты `/clinics`

3.1. **GET `/api/v1/clinics` и `/api/v1/clinics/{id}`**

- Убедиться, что оба эндпоинта возвращают обновлённый `ClinicRead` с `business_lexicon`.

3.2. **PUT `/api/v1/clinics/{id}`**

- Разрешить обновление:
  - `business_type`, `business_type_custom_name`;
  - `person_label_singular`, `person_label_plural`, `staff_label_plural`.
- Убедиться, что:
  - при `business_type='other'` можно задавать `business_type_custom_name`;
  - при других типах `business_type_custom_name` можно оставить `NULL` (без ошибок).

3.3. **Тесты**

- В `tests/api` добавить / обновить smoke‑тесты:
  - GET `/api/v1/clinics` → первый элемент содержит `business_type` и `business_lexicon` с заполненными полями и непустым `role_display`.
  - PUT `/api/v1/clinics/{id}`:
    - обновление `business_type` и лексики успешно применяются;
    - после обновления GET возвращает новые значения.

#### 4. Frontend: типы и контекст клиники

4.1. **Типы API**

- В `frontend/src/api/types.ts`:
  - добавить интерфейс `BusinessLexicon` согласно ARCH;
  - расширить `Clinic` новыми полями:
    - `business_type`, `business_type_custom_name`;
    - `person_label_singular?`, `person_label_plural?`, `staff_label_plural?`;
    - `business_lexicon?: BusinessLexicon`.

4.2. **AdminClinicContext**

- В `frontend/src/contexts/AdminClinicContext.tsx`:
  - убедиться, что контекст хранит полный массив `Clinic[]` с новыми полями;
  - добавить хелпер `useBusinessLexicon()`:
    - находит текущую клинику по `currentClinicId`;
    - возвращает объект с безопасными значениями (`Пациент` / `Пациенты` / `Врачи` по умолчанию, если чего‑то нет).

#### 5. Frontend: страница `/admin/clinics` как центр бизнеса

5.1. **Форма клиники**

- В `frontend/src/admin/pages/AdminClinicsPage.tsx`:
  - форма (модалка) уже содержит:
    - `Тип бизнеса`;
    - `Свой тип бизнеса`.
  - добавить поля:
    - `person_label_singular` (label: «Как называть клиента (ед. число)»);
    - `person_label_plural` (label: «Как называть клиентов (мн. число)»);
    - `staff_label_plural` (label: «Как называть специалистов (списком)»).
  - При открытии формы редактирования:
    - подставлять значения из `clinic.person_label_*`, `clinic.staff_label_plural` (или пустые строки).
  - При сохранении:
    - отправлять в payload новые поля (null, если строки пустые).

5.2. **Таблица клиник**

- В таблице на `/admin/clinics`:
  - добавить колонку, показывающую:
    - `business_type` (человеческое название);
    - и/или лейблы: `{person_label_plural} / {staff_label_plural}`.

#### 6. Frontend: использование лексики в админке и PWA

6.1. **AdminDoctorsPage**

- Используя `useBusinessLexicon()`:
  - заголовок и подзаголовок страницы заменить:
    - «Врачи» → `staff_label_plural`;
  - в таблицах/подсказках избегать жёсткого слова «врач», использовать `display_role` и/или `staff_label_plural`.

6.2. **Расписание, записи, лист ожидания**

- В `SchedulePage`, `AdminBookingsPage`, `AdminWaitlistPage`:
  - заменить тексты «Врач» в заголовках/лейблах на:
    - `staff_label_plural` для списков/групп;
    - `display_role` конкретного специалиста там, где речь о конкретном человеке.

6.3. **PWA (мастер записи)**

- В `BookingWizardPage`:
  - шаг выбора врача:
    - лейбл шага и селект «Врач» → использовать комбинацию:
      - заголовок шага может использовать `staff_label_plural` («Специалист»/«Мастер») — по согласованию;
      - рядом с ФИО врача уже используется `display_role` (это реализовано в предыдущем этапе, проверить и при необходимости доработать).

6.4. **Список клиник для пациента**

- Убедиться, что PWA (`HomePage`, `FeedPage`, `BookingWizardPage`) использует **один и тот же хук `useClinics`**, который бьётся в `/api/v1/clinics`.
- Это гарантирует, что пациент видит **ровно тот же набор клиник**, что и админ на `/admin/clinics`.

#### 7. Изоляция данных по `clinic_id`

7.1. **Аудит backend‑роутов**

- Пройтись по основным admin‑роутам в `src/api/v1/routers`:
  - `admin_services`, `admin_schedule`, `admin_doctor_schedule`, `admin_prepayment`, `admin_waitlist`, `admin_recall`, `admin_marketing`, `admin_reports`, `admin_chat`, `admin_discounts`, `admin_channel_configs`, `admin_integrations`, `admin_notification_policy`, `admin_admins`.
- Проверить, что:
  - везде выборки и операции фильтруются по `clinic_id` либо из URL (`/admin/clinics/{clinic_id}/...`), либо из текущего админа;
  - нет выборок без фильтра `clinic_id` там, где это критично.

7.2. **Аудит фронтенд‑хуков**

- Для основных `useAdmin*`‑хуков:
  - убедиться, что каждый принимает `clinicId` и пробрасывает его в API‑вызовы;
  - при смене `currentClinicId` контекст админки должен инициировать перезапросы (за это уже отвечает React Query по ключам; важно не забывать включать `clinicId` в `queryKey`).

7.3. **Smoke‑тесты**

- Добавить/обновить:
  - e2e‑тесты, которые:
    - создают вторую клинику;
    - переключаются между клиниками в шапке;
    - проверяют, что списки врачей/пациентов/услуг различаются и не пересекаются.

---

### Завершение

По окончании работ:

- убедиться, что:
  - страница `/admin/clinics` управляет полным конфигом бизнеса (тип + лексика);
  - все admin‑страницы и PWA используют лексикон и отображают правильные термины;
  - пациент при записи выбирает клинику из того же списка, что и админ на `/admin/clinics`;
  - переключение клиники в админке изолирует данные по `clinic_id` без утечек.

