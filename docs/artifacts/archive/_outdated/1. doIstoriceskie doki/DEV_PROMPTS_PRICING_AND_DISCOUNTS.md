# DEV_PROMPTS — Ценообразование и скидки (PricingService)

> Основание: `ARCH_PRICING_AND_DISCOUNTS.md`  
> Режим: поэтапная реализация с сохранением текущего поведения предоплаты и скидок.

---

## 0. Общие правила для этой фичи

- **Никаких изменений `services.price` через скидки.** Это `base_price`, не трогаем его кодом скидок.
- **Вся логика скидок — через `DiscountService` / `PricingService`, не дублировать формулы.**
- **Сначала backend (PricingService + PaymentService), потом расширение DTO, потом frontend.**
- **После каждого этапа — минимум один интеграционный тест на основной happy-path.**

---

## ФАЗА 1 — Внедрить PricingService и использовать его в PaymentService (backend)

### Задача 1.1 — Создать `PricingService`

- **Файлы:**
  - `src/application/services/pricing_service.py` — новый файл.
  - Использовать реализацию и сигнатуры из `ARCH_PRICING_AND_DISCOUNTS.md`, раздел 2.2.

- **Что сделать:**
  1. Создать dataclass `PricingResult` с полями:
     - `base_price: Decimal`
     - `effective_price: Decimal`
     - `discount_amount: Decimal`
     - `discount_id: UUID | None`
     - `discount_type: str | None`
     - `discount_name: str | None`
  2. Создать класс `PricingService` с конструктором `__init__(self, session: AsyncSession)`.
  3. Реализовать метод `compute_effective_price(...)`, который:
     - принимает `clinic_id`, `service_id`, `doctor_id`, `patient_id`, `on_date`, `base_price`;
     - вызывает `DiscountService.get_applicable_discount(...)` с теми же параметрами (price = base_price);
     - заполняет `PricingResult` по результату.

### Задача 1.2 — Переподключить PaymentService на PricingService

- **Файл:** `src/application/services/payment_service.py`

- **Текущее место:** поиск по `discount_svc = DiscountService(self.session)` и `get_applicable_discount(...)`.

- **Что сделать:**
  1. Заменить локальное создание `DiscountService` на использование `PricingService`:
     - `pricing_svc = PricingService(self.session)`
     - вызвать `compute_effective_price` с:
       - `clinic_id = booking.clinic_id`
       - `service_id = booking.service_id`
       - `doctor_id = booking.doctor_id`
       - `patient_id = booking.patient_id`
       - `on_date = booking.appointment_date`
       - `base_price = amount` (текущая сумма предоплаты).
  2. Из результата `PricingResult`:
     - взять `effective_price` как новый `amount` к оплате;
     - посчитать:
       - `original_amount` — строка от `base_price`, если `discount_amount > 0`, иначе `None`;
       - `discount_amount` — строка от `discount_amount`, если > 0, иначе `None`;
       - `final_amount` — строка от `effective_price`, если `discount_amount > 0`, иначе `None`.
  3. Убедиться, что остальной код `PaymentService.create_payment` не меняется (логика статусов/препеймента прежняя).

### Задача 1.3 — Минимальные тесты на поведение предоплаты со скидками

- **Цель:** Зафиксировать, что переход к `PricingService` не сломал бизнес-логику.

- **Что протестировать (pytest):**
  - Сценарий без скидок: `PricingResult.effective_price == base_price`, платеж создаётся как раньше.
  - Сценарий со скидкой `discount_type = "period"` и `percent_off`:
    - итоговая сумма в платеже равна `base_price - discount`;
    - поля `original_amount` / `discount_amount` / `final_amount` заполнены корректно.

> **Критерий завершения Фазы 1:**  
> - `PricingService` существует и используется в `PaymentService`.  
> - Все существующие тесты проходят, новые тесты по скидкам зелёные.  
> - Поведение предоплаты и создания платежей не изменилось функционально (ручная проверка по минимуму кейсов).

---

## ФАЗА 2 — Расширить DTO услуг полями effective_price и скидок (backend)

### Задача 2.1 — Обновить DTO для услуг

- **Файл:** `src/application/dto/service_dto.py` (уточнить точное имя по коду).

- **Что добавить в DTO чтения (read-модели):**
  - `base_price: Decimal`
  - `effective_price: Decimal`
  - `has_active_discount: bool`
  - `discount_id: UUID | None`
  - `discount_type: str | None`
  - `discount_label: str | None`

- **Требования:**
  - Поле `price` не удалять и не менять тип.
  - `base_price` заполнять значением `price`.

### Задача 2.2 — Внедрить PricingService в сервисы, отдающие услуги

- **Файлы (ориентировочно):**
  - `src/application/services/service_service.py`
  - `src/api/v1/routers/services.py`
  - Публичный роутер для списка услуг (по HANDOFF).

- **Что сделать:**
  1. При формировании списка услуг для public/admin добавить вычисление `PricingResult`:
     - для public:
       - `clinic_id` — из контекста клиники;
       - `service_id` — текущая услуга;
       - `doctor_id = None`;
       - `patient_id = None`;
       - `on_date = today()`.
  2. DTO заполнять:
     - `base_price = service.price`
     - `effective_price = pricing_result.effective_price`
     - `has_active_discount = pricing_result.discount_amount > 0`
     - `discount_id`, `discount_type` — из `PricingResult`
     - `discount_label = pricing_result.discount_name`

> **Критерий завершения Фазы 2:**  
> - Public/admin эндпоинты услуг возвращают новые поля, не ломая старые.  
> - Для активной `period`-скидки видно расхождение `base_price` / `effective_price`.  
> - Для отключённой скидки `effective_price == base_price`, `has_active_discount == false`.

---

## ФАЗА 3 — Обновить frontend для использования effective_price

### Задача 3.1 — Пациентский wizard записи

- **Файл:** `frontend/src/app/pages/BookingWizardPage.tsx`

- **Что сделать:**
  1. Расширить TS-тип услуги (в `frontend/src/api/types.ts`), чтобы включал:
     - `base_price`, `effective_price`, `has_active_discount`, `discount_*`.
  2. В списке услуг:

     ```tsx
     const serviceOptions =
       publicServices?.map((s) => ({
         value: s.id,
         label: s.has_active_discount
           ? `${s.name} — ${s.base_price} ₽ → ${s.effective_price} ₽`
           : `${s.name} — ${s.effective_price} ₽`,
       })) ?? [];
     ```

  3. При отображении выбранной услуги на шаге оплаты использовать `effective_price` как “цену сейчас”.

### Задача 3.2 — Админка: услуги и расписание

- **Файлы:**
  - `frontend/src/admin/pages/AdminServicesPage.tsx`
  - `frontend/src/admin/pages/SchedulePage.tsx`

- **Что сделать:**
  - В таблице услуг:
    - отображать `effective_price` как основную цену;
    - если `has_active_discount`, показывать `base_price` зачёркнутой и бейдж “Скидка”.
  - В расписании (создание записи из сетки):
    - в выпадающем списке услуг выводить `effective_price` по аналогии с patient wizard.

> **Критерий завершения Фазы 3:**  
> - Пользователь в UI всегда видит цену, совпадающую с ценой, которая идёт в платёж.  
> - При отключении скидки отображение автоматически возвращается к `base_price` без ручного вмешательства.

---

## ФАЗА 4 — Тесты и защита от регрессий

### Задача 4.1 — Интеграционные тесты “прайс + оплата”

- Написать тесты (pytest) для следующего сценария:
  1. Создать услугу с ценой 3000 ₽.
  2. Создать `period`-скидку 10% для клиники.
  3. Проверить:
     - `GET /public/clinics/{id}/services` → `effective_price == 2700`, `has_active_discount == true`.
  4. Создать запись и попытаться создать предоплату:
     - сумма в платеже (и поля `original_amount`/`discount_amount`/`final_amount`) соответствуют 3000 → 2700.

### Задача 4.2 — Сценарий отмены скидки

- Продолжение предыдущего теста:
  1. Деактивировать скидку (`is_active = false` или `valid_until` в прошлом).
  2. Повторно запросить список услуг:
     - `effective_price == base_price == 3000`, `has_active_discount == false`.
  3. Создать ещё одну запись и предоплату:
     - сумма в платеже равна 3000, без скидки.

> **Критерий завершения Фазы 4:**  
> - Интеграционные тесты фиксируют как применение, так и отмену скидки.  
> - Нет расхождений между прайсом и чеком в базовых сценариях.

