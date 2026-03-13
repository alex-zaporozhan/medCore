# ARCH_PRICING_AND_DISCOUNTS_APPLY — Применение скидок и ценообразование

> Роль: @ARCH  
> Вход: `BIZ_DISCOUNTS_PRICING_RULES.md`, текущая реализация `discounts` и `PaymentService`.  
> Цель: сделать так, чтобы:
> - скидки применялись **к реальной цене записи** (а не только к сумме предоплаты);
> - пациент видел цену со скидкой в мастере записи и на подтверждении;
> - скидка была **зафиксирована** в БД и не менялась задним числом.

---

## 1. Режим и стек (контекст)

- Режим: SAAS  
- Backend: Python 3.11 + FastAPI + SQLAlchemy (async)  
- Frontend: TypeScript + React + Vite (Mantine UI)  
- БД: PostgreSQL (asyncpg)

---

## 2. Текущее состояние (high‑level)

1. Таблица `discounts` и сервис `DiscountService` уже существуют:
   - типы: `first_visit` | `service` | `doctor` | `period`;
   - логика применения — в методе `get_applicable_discount`.
2. Скидки учитываются **только в `PaymentService.create_payment`**:
   - корректируется сумма предоплаты;
   - в бронировании нет отдельного поля «цена со скидкой».
3. PWA в мастере записи отображает `PublicService.price` (базовая цена), не зная о скидках.

**Вывод:** применение скидок привязано к оплате, а не к записи/цене услуги. Нужен слой «фиксации цены» на стороне записи/чека.

---

## 3. Проектируемая модель данных

### 3.1. Расширение `Booking`

Добавить в сущность `Booking` (и таблицу в БД) поля:

- `base_price NUMERIC(10,2) NULL` — базовая цена услуги на момент записи (до скидки);
- `discount_amount NUMERIC(10,2) NULL` — сумма применённой скидки;
- `final_price NUMERIC(10,2) NULL` — итоговая цена после скидки;
- `applied_discount_id UUID NULL FK -> discounts(id)` — какая скидка была применена (если была).

**Правила:**

- `base_price` и `final_price` заполняются **один раз** при создании/подтверждении записи и не пересчитываются задним числом.
- Если скидок нет — `base_price = services.price`, `final_price = base_price`, `discount_amount = 0`, `applied_discount_id = NULL`.

### 3.2. Альтернатива (на будущее)

Если появится необходимость учитывать несколько услуг в одной записи:

- отдельная таблица `booking_items`:
  - `booking_id`, `service_id`, `base_price`, `discount_amount`, `final_price`, `applied_discount_id`, `quantity`;
- в этом ARCH фиксируем **MVP‑вариант без `booking_items`**, одна услуга на запись (как сейчас).

---

## 4. Точка расчёта цены и скидки

### 4.1. При создании записи

- Endpoint (пациент): `POST /api/v1/bookings` (см. текущую реализацию `BookingService` / `booking_service.py`).
- При успешном создании записи:
  1. Определяем `base_price`:
     - читаем `Service.price` по `service_id`;
     - при необходимости учитываем будущие надбавки (вне этого ARCH).
  2. Вызываем `DiscountService.get_applicable_discount(...)` с:
     - `clinic_id`, `service_id`, `doctor_id`, `patient_id`, `appointment_date`, `price = base_price`.
  3. Получаем `(discount, discount_amount, final_price)`:
     - записываем в поля `base_price`, `discount_amount`, `final_price`, `applied_discount_id`.

### 4.2. При оплате (предоплата / полная)

- В `PaymentService.create_payment`:
  - больше **не считать скидку с нуля**, а опираться на уже сохранённые `final_price` / `discount_amount`.
  - Для предоплаты:
    - если логика предоплаты остаётся фиксированной (500 ₽ или `clinic.prepayment_amount`) — скидка может применяться только к полной цене (в отчётах); это отдельное бизнес‑решение, см. BIZ‑документ.

**MVP‑решение, которое зафиксируем:**

- `PaymentService`:
  - если `booking.final_price` задан и > 0 — использовать её как «цена услуги» для отчётности;
  - сумму предоплаты по‑прежнему считаем по политике предоплаты (не смешиваем пока два контекста).

---

## 5. Алгоритм применения скидок (архитектура)

### 5.1. Расширение `Discount` (миграция)

Добавить:

- `priority INTEGER NOT NULL DEFAULT 0` — приоритет применения (чем больше, тем важнее).
- `only_first_visit BOOLEAN NOT NULL DEFAULT false` — для скидок типа `service`/`doctor`/`period`, которые должны работать **только при первом визите**.

(Флаг `only_first_visit` позволяет описать комбинации `service ∧ first_visit` без отдельного типа.)

### 5.2. Новый контракт `DiscountService.get_applicable_discount`

Текущий метод уже имеет сигнатуру:

```python
async def get_applicable_discount(
    self,
    clinic_id: UUID,
    service_id: UUID | None,
    doctor_id: UUID | None,
    patient_id: UUID | None,
    on_date: date,
    price: Decimal,
) -> tuple[Discount | None, Decimal, Decimal]:
    ...
```

Нужно:

- отфильтровать скидки по:
  - `clinic_id`, `is_active`, `valid_from` / `valid_until`;
  - типу (`discount_type`) и комбинациям условий (см. ниже).
- сортировать по:
  - `priority DESC`,
  - при равном приоритете — по дате создания (последняя выигрывает).
- учесть комбинации:
  - `discount_type == "first_visit"` → работает только если `is_patient_first_visit` и не рассматривает `service_id`/`doctor_id`;
  - `discount_type == "service"`:
    - если `d.service_id == service_id`,
    - и, если `d.only_first_visit == True`, дополнительно `is_patient_first_visit`;
  - аналогично для `doctor` и `period`.

**Важно:** метод по‑прежнему возвращает **одну** скидку (MVP). Комбинирование нескольких скидок в будущем — отдельный ARCH.

---

## 6. API‑контракты

### 6.1. DTO бронирования (пациент/админ)

Расширить DTO `BookingRead` (и связанные):

- `base_price: str | null`
- `discount_amount: str | null`
- `final_price: str | null`
- `applied_discount_id: UUID | null`

При этом:

- публичные эндпоинты пациента могут использовать только `final_price` для отображения цены;
- админские эндпоинты могут видеть все поля.

### 6.2. Публичный список услуг

Варианты:

- **Вариант A (MVP):** оставить `PublicService.price` как есть (базовая цена), а цену со скидкой получать **из бронирования** и/или через новый endpoint.
- **Вариант B:** добавить к `PublicService` поле `price_with_discount` (рассчитанное на лету с учётом пациента) — требует знать `patient_id` на этапе получения списка услуг.

Для MVP целесообразно:

- использовать Вариант A, но:
  - на шаге подтверждения показывать цену из бронирования (`final_price`);
  - опционально добавить endpoint `GET /api/v1/pricing/quote` (по `clinic_id`, `service_id`, `patient_id`), если понадобятся превью‑цены.

---

## 7. Изменения во фронтенде (контекст для DEV_PROMPT)

Кратко, что потребуется от фронта (детали в DEV_PROMPT):

- PWA:
  - на шаге подтверждения использовать `final_price` и информацию о скидке из бронирования;
  - при желании — отображать старую цену и размер скидки.
- Админка:
  - в списке/карточке записей и/или платежей отображать поля `base_price`, `final_price`, `discount_amount`, `applied_discount_id` (с названием скидки).

---

## 8. Этапность и риски

### 8.1. Этап 1 (MVP)

- Миграции:
  - добавить ценовые поля в `bookings`;
  - добавить `priority`, `only_first_visit` в `discounts`.
- Обновить `DiscountService` и `BookingService`:
  - при создании записи вычислять и сохранять `base_price`/`discount`/`final_price`.
- Обновить `PaymentService`:
  - использовать зафиксированные цены для отчётности;
  - не пересчитывать скидку с нуля.
- Расширить DTO бронирования.
- Минимальные изменения PWA/админки (отображение цены и скидки на подтверждении и в админ‑интерфейсе).

### 8.2. Этап 2 (после валидации)

- Возможность комбинировать несколько скидок.
- Отдельный endpoint для превью‑цены (`pricing/quote`).
- Более продвинутые отчёты по скидкам.

---

## 9. Указания для @DEV (резюме)

На основе этого ARCH подготовить `DEV_PROMPT_PRICING_AND_DISCOUNTS_APPLY.md` со следующим порядком:

1. Миграции БД (`bookings`, `discounts`).
2. Обновление `DiscountService.get_applicable_discount` и вспомогательных методов.
3. Обновление `BookingService` (заполнение `base_price`/`final_price` при создании).
4. Обновление `PaymentService` (использование зафиксированных цен).
5. Расширение DTO и API (бронирования).
6. Изменения PWA и админки (отображение цен и скидок).
7. Юнит‑ и e2e‑тесты на сценарий:
   - услуга со скидкой 20%,
   - первый визит,
   - проверка, что `final_price` и скидка записаны в БД и отображаются пользователю.

