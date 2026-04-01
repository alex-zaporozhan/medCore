## DEV_PROMPT: Применение скидок и фиксация цены

> Архитектура и контекст: `BIZ_DISCOUNTS_PRICING_RULES.md`, `ARCH_PRICING_AND_DISCOUNTS_APPLY.md`.  
> Цель: при создании записи фиксировать базовую цену, скидку и итоговую цену в БД, чтобы:
> - пациент видел цену со скидкой на шаге подтверждения;
> - админ видел, какая скидка применена и как изменилась цена;
> - скидка не пересчитывалась задним числом.

---

### Общие правила для @DEV

- Двигаться по чек‑листу ниже **строго по порядку**, не смешивая большие пункты в одном коммите.
- Не ломать существующий прод:
  - новые поля в таблицах должны иметь дефолты / быть nullable и не ломать старые DTO;
  - API расширяем добавлением полей, а не переименованием.
- Источники правды:
  - `BIZ_DISCOUNTS_PRICING_RULES.md` — бизнес‑правила скидок;
  - `ARCH_PRICING_AND_DISCOUNTS_APPLY.md` — архитектура БД, точка расчёта и контракты.

Рекомендуемый порядок: 1) миграции БД, 2) сервисы скидок и бронирования, 3) PaymentService, 4) DTO и API, 5) фронт, 6) тесты.

---

### To‑dos (по шагам)

#### 1. Миграции БД: `bookings` и `discounts`

1.1. **Расширить таблицу `bookings`**

- Новая Alembic‑миграция, например `add_booking_pricing_fields.py`:
  - добавить в `bookings` колонки:
    - `base_price NUMERIC(10,2) NULL`;
    - `discount_amount NUMERIC(10,2) NULL`;
    - `final_price NUMERIC(10,2) NULL`;
    - `applied_discount_id UUID NULL` (FK → `discounts.id`).
- Индексы на этих полях на первом шаге **не обязательны**, но FK должен быть настроен.

1.2. **Расширить таблицу `discounts`**

- В той же или отдельной миграции:
  - добавить:
    - `priority INTEGER NOT NULL DEFAULT 0`;
    - `only_first_visit BOOLEAN NOT NULL DEFAULT false`.

1.3. **Обновить сущности**

- В `src/domain/entities/booking.py`:
  - добавить свойства `base_price`, `discount_amount`, `final_price`, `applied_discount_id` с типом `Decimal | None` / `UUID | None`.
- В `src/domain/entities/discount.py`:
  - добавить свойства `priority: int` и `only_first_visit: bool`.

---

#### 2. Backend: обновление DiscountService

2.1. **Фильтрация и сортировка скидок**

- В `DiscountService.get_applicable_discount`:
  - при выборке скидок по клинике добавить сортировку:

  ```python
  select(Discount).where(
      Discount.clinic_id == clinic_id,
      Discount.is_active.is_(True),
  ).order_by(Discount.priority.desc(), Discount.created_at.desc())
  ```

2.2. **Комбинации условий**

- Логика применения (одна скидка на запись):
  - игнорировать скидки, у которых `valid_from` / `valid_until` не покрывают `on_date`;
  - для каждого `Discount` в отсортированном списке:
    - если `discount_type == "first_visit"`:
      - проверить `patient_id` и `is_patient_first_visit`;
    - если `discount_type == "service"`:
      - `service_id` должен совпадать (если задан),
      - если `only_first_visit == True` — дополнительно проверять `is_patient_first_visit`;
    - аналогично для `doctor` и `period`.
  - при первом совпадении вызвать `compute_discount_and_final` и вернуть результат.

2.3. **Проверка первого визита**

- Убедиться, что `is_patient_first_visit`:
  - проверяет отсутствие записей `Booking` с:
    - `patient_id`, `clinic_id`, `status == "completed"`.

---

#### 3. Backend: фиксация цены при создании записи

3.1. **Обновить сервис создания бронирования**

- В `BookingService` (или соответствующем application‑сервисе, который создаёт `Booking`):
  - после валидации входных данных:
    1. найти услугу по `service_id` и считать `base_price = service.price`;
    2. вызвать `DiscountService.get_applicable_discount(...)` с:
       - `clinic_id`, `service_id`, `doctor_id`, `patient_id`, `appointment_date`, `price=base_price`;
    3. установить на сущности `Booking`:
       - `base_price = base_price`;
       - `discount_amount`;
       - `final_price`;
       - `applied_discount_id = discount.id` (если есть).

3.2. **Заполнение полей по умолчанию**

- Если скидок нет:
  - `discount_amount = 0`;
  - `final_price = base_price`;
  - `applied_discount_id = None`.

3.3. **Сохранение**

- Убедиться, что поля попадают в `BookingRead` и возвращаются в ответе API после создания записи.

---

#### 4. Backend: адаптация PaymentService

4.1. **Не пересчитывать скидку с нуля**

- В `PaymentService.create_payment`:
  - после загрузки `booking`:
    - если `booking.base_price` и `booking.final_price` не `NULL`:
      - использовать их для заполнения `original_amount` / `final_amount` в `CreatePaymentResponse` (если нужно);
      - не вызывать повторно `DiscountService.get_applicable_discount` для этих цен.
  - вызов `DiscountService` оставить только как fallback, если исторически создавались записи без этих полей.

4.2. **Поле `prepayment_amount`**

- Логику `prepayment_amount` **не менять** в этом инкременте:
  - она по‑прежнему управляется политиками предоплаты;
  - скидки работают на полную цену услуги, а не на фиксированную предоплату (конкретное бизнес‑решение описано в BIZ/ARCH и может быть доработано позже).

---

#### 5. Backend: DTO и API

5.1. **Расширить DTO бронирования**

- В `booking_dto.py` (или аналогичном файле DTO):
  - добавить к `BookingRead` поля:
    - `base_price: str | None`;
    - `discount_amount: str | None`;
    - `final_price: str | None`;
    - `applied_discount_id: UUID | None`.
  - при сериализации `Decimal` → `str` (по текущему стандарту проекта).

5.2. **Админские DTO**

- В админских ответах, где возвращаются бронирования, включить новые поля, чтобы админ видел ценовую информацию.

---

#### 6. Frontend: PWA (мастер записи)

6.1. **Отображение цены со скидкой**

- На шаге **подтверждения**:
  - использовать поля `final_price` и `discount_amount` из ответа создания записи (если доступны);
  - при наличии скидки показывать:
    - `base_price` зачёркнуто;
    - `final_price` как основную цену;
    - подпись «Скидка −X ₽» или «скидка Y%» (по возможности).

6.2. **Минимальные изменения**

- На шаге выбора услуги в этом инкременте можно оставить отображение базовой цены из `PublicService.price`.
- Более продвинутый вариант (превью цены со скидкой до создания записи) оставить на следующий этап (после отдельного ARCH/UI‑решения).

---

#### 7. Frontend: админка

7.1. **Карточка/список записей**

- Добавить отображение:
  - `base_price`;
  - `discount_amount`;
  - `final_price`;
  - названия применённой скидки (по `applied_discount_id` и справочнику скидок).

7.2. **Отчёты (минимум)**

- При наличии существующих отчётов по выручке:
  - использовать `final_price` для расчёта фактической выручки;
  - при возможности — отдельное поле «Сумма скидок» на период (агрегат по `discount_amount`).

---

#### 8. Тесты

8.1. **Unit‑тесты DiscountService**

- Кейсы:
  - скидка `service` на конкретную услугу;
  - скидка `first_visit` при отсутствии `completed`‑записей;
  - скидка `service` c `only_first_visit = True`:
    - применяется только при первом визите;
    - не применяется при повторных визитах;
  - сортировка по `priority` (выбирается скидка с большим приоритетом).

8.2. **Интеграционный тест бронирования**

- Сценарий:
  - создать скидку 20% на услугу X;
  - создать запись с этой услугой для первичного пациента;
  - убедиться, что:
    - `base_price = services.price`,
    - `discount_amount = 20% от base_price`,
    - `final_price = base_price − discount_amount`,
    - `applied_discount_id` заполнен.

8.3. **E2E‑тест мастер записи**

- Через HTTP‑клиент:
  - пройти шаги мастера;
  - проверить, что в ответе создания записи и на шаге подтверждения PWA используются те же значения цен/скидок.

---

### Завершение

По окончании выполнения этого DEV_PROMPT должно быть выполнено:

- Каждая запись (`Booking`) хранит базовую цену, сумму скидки, итоговую цену и ссылку на применённую скидку.
- `DiscountService` применяет одну релевантную скидку по правилам бизнеса, с учётом комбинированных условий (`service` + `only_first_visit`).
- `PaymentService` не пересчитывает скидки с нуля, а опирается на зафиксированную цену записи.
- Пациент в мастере записи видит итоговую цену со скидкой (минимум на шаге подтверждения), админ — видит, какая скидка применена и на сколько изменена цена.

