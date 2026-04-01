## ARCH_BUSINESS_TYPES_AND_LEXICON — Универсальный бизнес, роли и лексика

**Проект:** Dental Booking System MVP  
**Режим:** SAAS с несколькими клиниками (бизнесами) в одной БД  

---

### 1. Цель архитектуры

- Сделать продукт **универсальным для разных типов бизнеса** (стоматология, клиники, салоны красоты и т.д.) без разведения отдельных кодовых баз.
- Жёстко зафиксировать модель:
  - **один `clinic` = один бизнес‑профиль** (один тип бизнеса, свой набор услуг, своя лексика);
  - если у владельца несколько направлений (например, барбер+ногти+массаж) — он заводит **несколько клиник**, не смешивая данные по одному `clinic_id`.
- Обеспечить:
  - единый источник правды по типу бизнеса (`clinics.business_type`);
  - настраиваемую **лексику интерфейса** (пациент/клиент, врач/мастер и т.п.) на уровне клиники;
  - настраиваемые **роли специалистов** на уровне клиники;
  - строгую изоляцию данных по `clinic_id` при переключении активной клиники в админке.
- Гарантировать, что:
  - список клиник, которые видит пациент в мастере записи (PWA), **совпадает** со списком в админке `/admin/clinics`;
  - вся админка всегда работает в контексте **активной клиники**, выбранной в шапке и на странице `Клиники`.

---

### 2. Модель данных

#### 2.1. Таблица `clinics`

К существующим полям добавляются:

- `business_type TEXT NOT NULL DEFAULT 'stomatology'`
  - допустимые значения: `stomatology`, `clinic`, `beauty_salon`, `barbershop`, `massage_salon`, `other`;
- `business_type_custom_name TEXT NULL`
  - человекочитаемое имя для `other` (например, «Барбершоп+тату»);
- `person_label_singular TEXT NULL`
  - как называть одного человека: «Пациент», «Клиент», «Гость»;
- `person_label_plural TEXT NULL`
  - множественное число: «Пациенты», «Клиенты»;
- `staff_label_plural TEXT NULL`
  - как называть сотрудников списком: «Врачи», «Мастера», «Специалисты».

Все новые поля **опциональны**, но при чтении через DTO мы всегда предоставляем значения (см. 3.2).

#### 2.2. Таблица `doctors`

Уже добавлены:

- `specialist_role TEXT NOT NULL DEFAULT 'doctor'`
  - допустимые значения (ключи, с которыми работает backend):
    - медицинский блок: `doctor`, `nurse`, `therapist`;
    - бьюти‑/сервисные роли: `master`, `barber`, `stylist`, `tattoo_master`, `massage_therapist`;
    - запасной вариант: `other`;
- `specialist_role_custom_name TEXT NULL`.

На entity уровня `Doctor` есть вычисляемое свойство:

- `display_role: str` — человекочитаемое название роли для UI и отчётов:
  - если `specialist_role_custom_name` непустой → используется она (_отчёты всегда показывают именно её_);
  - иначе используется словарь лексики для `specialist_role` (см. 2.3);
  - fallback → «Специалист».

#### 2.3. Лексикон по умолчанию (in‑memory словарь)

На backend создаётся словарь **дефолтов** по `business_type`:

```python
DEFAULT_BUSINESS_LEXICON = {
    "stomatology": {
        "person_label_singular": "Пациент",
        "person_label_plural": "Пациенты",
        "staff_label_plural": "Врачи",
        "role_display": {
            "doctor": "Врач",
            "nurse": "Медсестра",
            "therapist": "Терапевт",
            "master": "Мастер",
            "barber": "Барбер",
            "stylist": "Стилист",
            "tattoo_master": "Тату‑мастер",
            "massage_therapist": "Массажист",
            "other": "Специалист",
        },
    },
    "clinic": {
        "person_label_singular": "Пациент",
        "person_label_plural": "Пациенты",
        "staff_label_plural": "Врачи",
        "role_display": { ... как для stomatology ... },
    },
    "beauty_salon": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Мастера",
        "role_display": {
            "master": "Мастер",
            "barber": "Барбер",
            "stylist": "Стилист",
            "tattoo_master": "Тату‑мастер",
            "therapist": "Массажист",
            "massage_therapist": "Массажист",
            "doctor": "Специалист",
            "nurse": "Ассистент",
            "other": "Специалист",
        },
    },
    "barbershop": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Мастера",
        "role_display": {
            "barber": "Барбер",
            "master": "Мастер",
            "stylist": "Стилист",
            "tattoo_master": "Тату‑мастер",
            "therapist": "Массажист",
            "massage_therapist": "Массажист",
            "doctor": "Специалист",
            "nurse": "Ассистент",
            "other": "Специалист",
        },
    },
    "massage_salon": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Специалисты",
        "role_display": {
            "therapist": "Массажист",
            "master": "Мастер",
            "doctor": "Специалист",
            "nurse": "Ассистент",
            "other": "Специалист",
        },
    },
    "other": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Специалисты",
        "role_display": {
            "doctor": "Специалист",
            "nurse": "Ассистент",
            "master": "Специалист",
            "therapist": "Специалист",
            "other": "Специалист",
        },
    },
}
```

---

### 3. Backend API и DTO

#### 3.1. DTO клиники

`ClinicRead` дополняется полями:

- `business_type: str`  
- `business_type_custom_name: str | None`
- `person_label_singular: str | None`
- `person_label_plural: str | None`
- `staff_label_plural: str | None`
- `business_lexicon: BusinessLexiconRead`

Где `BusinessLexiconRead`:

```python
class BusinessLexiconRead(BaseModel):
    business_type: str
    business_type_custom_name: str | None = None
    person_label_singular: str
    person_label_plural: str
    staff_label_plural: str
    role_display: dict[str, str]  # ключи specialist_role → строка для UI
```

`ClinicUpdate` получает опциональные поля:

- `business_type: BusinessType | None`
- `business_type_custom_name: str | None`
- `person_label_singular: str | None`
- `person_label_plural: str | None`
- `staff_label_plural: str | None`

`ClinicCreate` по‑прежнему может задавать только базовые поля + `business_type`/`business_type_custom_name` (лексика не обязательна на этапе создания).

#### 3.2. Сервис `ClinicService` / утилита лексики

Добавляется функция:

```python
def build_business_lexicon(clinic: Clinic) -> BusinessLexiconRead:
    # 1. Берём дефолты по business_type
    base = DEFAULT_BUSINESS_LEXICON.get(clinic.business_type or "stomatology", DEFAULT_BUSINESS_LEXICON["other"])
    # 2. Перекрываем person_label_*, staff_label_* клиники, если заданы
    # 3. Возвращаем DTO BusinessLexiconRead
```

`ClinicService.get_clinic` и `get_clinics`:

- после получения entity вычисляют `business_lexicon` и прокидывают его в `ClinicRead`.

#### 3.3. Эндпоинты

- `GET /api/v1/clinics` и `GET /api/v1/clinics/{id}` возвращают `ClinicRead` с `business_lexicon`.
- `PUT /api/v1/clinics/{id}` принимает новые поля лексики и сохраняет их в `clinics`.

**Важно:** PWA и админка **используют один и тот же эндпоинт `/api/v1/clinics`** (через `useClinics`), так что список клиник в мастере записи и в `/admin/clinics` совпадает «из коробки». В рамках этой архитектуры мы не меняем этот принцип.

---

### 4. Frontend: контекст клиники и лексика

#### 4.1. Типы

В `frontend/src/api/types.ts` (расширение существующего интерфейса `Clinic`):

- добавить:

```ts
export interface BusinessLexicon {
  business_type: string;
  business_type_custom_name?: string | null;
  person_label_singular: string;
  person_label_plural: string;
  staff_label_plural: string;
  role_display: Record<string, string>;
}

export interface Clinic {
  ...
  business_type?: string;
  business_type_custom_name?: string | null;
  person_label_singular?: string | null;
  person_label_plural?: string | null;
  staff_label_plural?: string | null;
  business_lexicon?: BusinessLexicon;
}
```

#### 4.2. `AdminClinicContext`

В контексте админки уже хранятся список клиник и `currentClinicId`.  
Добавляем:

- хелпер `useBusinessLexicon()`:

```ts
function useBusinessLexicon() {
  const { clinics, currentClinicId } = useAdminClinic();
  const clinic = clinics.find((c) => c.id === currentClinicId);
  const lex = clinic?.business_lexicon;
  // Возвращаем безопасные значения с дефолтами (например, "Пациент"/"Врачи")
}
```

Все компоненты, которым нужны тексты («Врач», «Пациент», «Врачи», «Клиенты»), берут их отсюда.

#### 4.3. Страница `/admin/clinics`

Модалка создания/редактирования клиники:

- уже содержит:
  - `Тип бизнеса` (селект);
  - `Свой тип бизнеса` (поле для `other`).
- добавляем блок «Термины в интерфейсе»:
  - «Как называть человека» (ед. число, мн. число);
  - «Как называть специалистов» (мн. число).
- При изменении `business_type` можно подставлять дефолты (плейсхолдеры, не обязательно автозаполнение).

Таблица клиник:

- новая колонка «Тип / Лексика», где показываем:
  - человекочитаемое имя бизнеса;
  - например: `Пациенты / Врачи` или `Клиенты / Мастера`.

#### 4.4. Использование лексики по всему админ‑интерфейсу

С помощью `useBusinessLexicon()`:

- `AdminDoctorsPage`:
  - заголовок `Врачи` → `staff_label_plural`;
  - подсказки «Управление специалистами клиники» → использовать `staff_label_plural`.
- `SchedulePage`, `AdminBookingsPage`, `AdminWaitlistPage`:
  - «Врач» в заголовках и подписях → использовать либо `staff_label_plural`, либо `display_role` конкретного врача;
  - тексты вроде «Выберите врачей» → `Выберите {staff_label_plural}`.
- `AdminPrepaymentPage`, отчёты:
  - в описаниях где явно упоминаются «врачи»/«пациенты», использовать лексикон.

PWA (`BookingWizardPage`, `HomePage` и т.п.):

- список клиник уже берётся через `useClinics` → синхронен с `/admin/clinics`;
- шаг выбора врача:
  - заголовок/лейбл «Врач» можно кастомизировать по `staff_label_plural`;
  - возле имени специалиста использовать `display_role`, если он важен в контексте.

---

### 5. Изоляция данных по `clinic_id`

Архитектурно система уже опирается на `clinic_id`:

- все ключевые сущности (`doctors`, `patients`, `services`, `bookings`, `discounts`, `waitlist`, `notifications`, `chat_messages` и т.д.) содержат `clinic_id`;
- админские эндпоинты имеют префикс `/admin/clinics/{clinic_id}/...` или явно принимают `clinic_id` как параметр.

Требования:

1. **Проверка**: пройтись по основным admin‑роутам и убедиться, что:
   - везде фильтрация по `clinic_id` текущего админа/выбранной клиники;
   - нет «забытых» выборок без фильтра по клинике.
2. **Фронтенд**:
   - `AdminClinicContext` при смене `currentClinicId` должен:
     - сбрасывать/перезапрашивать данные React Query, которые завязаны на клинику;
     - все хуки (`useAdmin*`) уже принимают `clinic_id` — проверить консистентность.

Таким образом, «ветка» данных для каждой клиники полностью изолирована логически в одной БД, а переключатель в шапке админки контролирует, к какой ветке мы обращаемся.

---

### 6. DEV-план (синхронизация с DEV_PROMPT)

Для @DEV подробный чек‑лист изложен в `DEV_PROMPT_BUSINESS_TYPES_AND_LEXICON.md`.  
Кратко по этапам:

1. Миграция + обновление `Clinic` entity и DTO (`ClinicRead/Update`).
2. Реализация `DEFAULT_BUSINESS_LEXICON` и `build_business_lexicon`.
3. Обновление эндпоинтов `/api/v1/clinics` и `/api/v1/clinics/{id}`.
4. Расширение типов на фронте и `AdminClinicContext`.
5. Доработка страницы `/admin/clinics` (форма + таблица).
6. Использование лексики в админ‑страницах и PWA.
7. Точечный аудит по `clinic_id` и smoke‑тесты.

