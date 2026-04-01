# Архитектура: Ценообразование и скидки (PricingService)
> Режим: SAAS · Backend: Python 3.11 + FastAPI · Frontend: React + TypeScript · БД: PostgreSQL 15  
> Почему: единый слой ценообразования и отсутствие расхождений между прайсом и кассой.

---

## 1. ADR — ключевые решения

- **ADR-1: Скидка — это overlay над базовой ценой, а не изменение самой цены услуги.**
  - В таблице `services` поле `price NUMERIC(10,2)` трактуем как **`base_price`**.
  - Любая скидка (first_visit / service / doctor / period) применяется поверх `base_price` и даёт **`effective_price`**.
  - При выключении/истечении скидки `effective_price` автоматически становится равным `base_price`, т.к. мы не мутируем `services.price`.

- **ADR-2: Единый слой ценообразования `PricingService`.**
  - Создаётся новый прикладной сервис `src/application/services/pricing_service.py`.
  - Задача сервиса — по входным параметрам (`clinic_id`, `service_id`, `doctor_id`, `patient_id`, `date`, `base_price`) вернуть:
    - `base_price: Decimal`
    - `effective_price: Decimal`
    - `discount_amount: Decimal`
    - `discount: Discount | None` (для внутреннего использования)
  - `PricingService` переиспользует текущую логику `DiscountService.get_applicable_discount` и **не дублирует** правила first_visit/service/doctor/period.

- **ADR-3: Backend — единственный источник истины для цены, которая уходит в кассу.**
  - Все суммы, которые уходят в YooKassa или любую кассу, считаются на backend через `PricingService`.
  - Frontend не применяет скидки самостоятельно, а только отображает данные, пришедшие из API (`effective_price`, `discount_amount`, метаданные скидки).

- **ADR-4: Обогащение DTO услуг полями “эффективной цены”.**
  - В DTO для услуг (public/admin) добавляются поля:
    - `base_price: Decimal` (дублирует историческое `price`);
    - `effective_price: Decimal`;
    - `has_active_discount: bool`;
    - `discount_id: UUID | None`;
    - `discount_type: Literal["first_visit","service","doctor","period"] | None`;
    - `discount_label: str | None` (человекочитаемое имя акции).
  - Существующее поле `price` остаётся для обратной совместимости и трактуется как `base_price`.

- **ADR-5: Миграция безопасна для текущей логики предоплаты.**
  - Первый этап — внедрение `PricingService` как thin-wrapper вокруг `DiscountService` в `PaymentService`, без изменения контрактов API.
  - Второй этап — расширение DTO услуг новыми полями (вниз совместимо).
  - Третий этап — фронтенд переходит на использование `effective_price` для отображения прайса.

---

## 2. Модель данных и связи

### 2.1 Существующие сущности

- `services` (domain: `src/domain/entities/service.py`):
  - поле `price NUMERIC(10,2) NOT NULL` — трактуем как `base_price`;
  - поле не меняется при акциях/скидках.
- `discounts` (domain: `src/domain/entities/discount.py`):
  - `clinic_id UUID`
  - `discount_type: "first_visit" | "service" | "doctor" | "period"`
  - `service_id UUID | NULL`
  - `doctor_id UUID | NULL`
  - `valid_from DATE | NULL`
  - `valid_until DATE | NULL`
  - `percent_off NUMERIC(5,2) | NULL`
  - `amount_off NUMERIC(10,2) | NULL`
  - `is_active BOOLEAN`

### 2.2 Новый прикладной слой

Файл: `src/application/services/pricing_service.py`

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.discount_service import DiscountService


@dataclass
class PricingResult:
    base_price: Decimal
    effective_price: Decimal
    discount_amount: Decimal
    discount_id: UUID | None
    discount_type: str | None
    discount_name: str | None


class PricingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discount_svc = DiscountService(session)

    async def compute_effective_price(
        self,
        *,
        clinic_id: UUID,
        service_id: UUID | None,
        doctor_id: UUID | None,
        patient_id: UUID | None,
        on_date: date,
        base_price: Decimal,
    ) -> PricingResult:
        discount, discount_amount, final_amount = await self._discount_svc.get_applicable_discount(
            clinic_id=clinic_id,
            service_id=service_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            on_date=on_date,
            price=base_price,
        )
        return PricingResult(
            base_price=base_price,
            effective_price=final_amount,
            discount_amount=discount_amount,
            discount_id=getattr(discount, "id", None),
            discount_type=getattr(discount, "discount_type", None),
            discount_name=getattr(discount, "name", None),
        )
```

> **Важно:** `PricingService` — единая точка применения скидок. Любые новые сценарии (полная онлайн-оплата, особые акции) должны использовать его, а не напрямую `DiscountService`.

---

## 3. API-контракты

### 3.1 Публичные услуги клиники

Эндпоинт (уточнить по коду, условно):  
`GET /api/v1/public/clinics/{clinic_id}/services`

#### Текущее поведение (по коду)

- Возвращает массив DTO услуг, где у каждой услуги есть, как минимум:
  - `id: UUID`
  - `name: str`
  - `price: Decimal (строка)` — базовая цена.

#### Целевое поведение

- Расширенный DTO услуги (новые поля помечены `(*)`):

```jsonc
{
  "id": "UUID",
  "name": "string",
  "price": "3000.00",          // историческое поле = base_price
  "base_price": "3000.00",     // (*)
  "effective_price": "2700.00",// (*) с учётом всех активных скидок
  "has_active_discount": true, // (*)
  "discount_id": "UUID",       // (*) или null
  "discount_type": "period",   // (*) или null
  "discount_label": "Весенняя скидка 10%" // (*) или null
}
```

- Логика применения скидок:
  - Берём `base_price = service.price`.
  - Вызываем `PricingService.compute_effective_price` с:
    - `clinic_id = clinic.id`
    - `service_id = service.id`
    - `doctor_id = null` (на стадии общего прайса врача может не быть)
    - `patient_id = null` (пациент не аутентифицирован)
    - `on_date = today()`
  - Для типов скидок:
    - `service` / `period` — применяются;
    - `doctor` — **не применяется** на этапе “общего прайса” (может быть учтена позже в карточке врача или при бронировании слота);
    - `first_visit` — опционально: может отображаться как промо (через `discount_label`), но цена по умолчанию остаётся `base_price` (решение можно уточнить в отдельном ADR).

### 3.2 Админские услуги клиники

Эндпоинт:  
`GET /api/v1/admin/clinics/{clinic_id}/services`

- Аналогично public-DTO, но:
  - добавляем те же поля `base_price`, `effective_price`, `has_active_discount`, `discount_*`;
  - админ видит фактический активный прайс с учётом скидок;
  - при изменении услуги админ редактирует только `base_price` (`service.price`).

### 3.3 Платежи (предоплата / полная оплата)

Эндпоинт:  
`POST /api/v1/payments` (через `PaymentService.create_payment`)

- Текущее поведение:
  - считает сумму предоплаты на основе:
    - `booking.prepayment_amount` или `clinic.prepayment_amount`;
    - скидки из `DiscountService.get_applicable_discount`.
  - Возвращает:

```jsonc
{
  "payment_url": "https://...",
  "provider_payment_id": "string",
  "prepayment_required": true,
  "original_amount": "500.00" | null,
  "discount_amount": "100.00" | null,
  "final_amount": "400.00" | null
}
```

- Целевое поведение:
  - Логика скидки переносится в `PricingService`:
    - `base_price = amount` (предоплата);
    - `effective_price`, `discount_amount` — из `PricingService`.
  - Контракт ответа **не меняется** (для совместимости), просто источник данных меняется на `PricingService`.

---

## 4. Принцип “цена для кассы считается на бэке”

- Любая сумма, которая:
  - отображается как “к оплате”;
  - уходит в YooKassa;
  - попадает в фискальный чек;
  — **должна быть возвращена бэком**.

- Frontend:
  - не реализует бизнес-логику скидок;
  - использует поля `effective_price`, `discount_amount`, `discount_label` для UI;
  - не отправляет свои “пересчитанные” суммы в YooKassa.

---

## 5. Миграционный план

### Этап 1. Внедрение PricingService + рефакторинг PaymentService

1. Создать `PricingService` и `PricingResult` в `src/application/services/pricing_service.py`.
2. В `PaymentService.create_payment` заменить прямой вызов `DiscountService.get_applicable_discount` на вызов `PricingService.compute_effective_price`:
   - `base_price = amount` (текущая сумма предоплаты);
   - итоговый `amount` брать из `effective_price`;
   - `original_amount`, `discount_amount`, `final_amount` вычислять по `PricingResult`.
3. Добавить unit/integration тесты, подтверждающие, что:
   - для наборов скидок (first_visit, service, doctor, period) итоговые суммы совпадают с прежней логикой.

### Этап 2. Обогащение DTO услуг (backend)

1. Расширить Pydantic DTO для услуг (public/admin) полями:
   - `base_price: Decimal`
   - `effective_price: Decimal`
   - `has_active_discount: bool`
   - `discount_id: UUID | None`
   - `discount_type: str | None`
   - `discount_label: str | None`
2. В сервисах, отдающих услуги (public/admin), внедрить вызовы `PricingService.compute_effective_price`:
   - для public-DTO: считать по `clinic_id`, `service_id`, `on_date=today`, без doctor/patient контекста;
   - для admin-DTO: аналогично, при необходимости учитывать контекст (можно начать без doctor/patient).
3. Убедиться, что:
   - старое поле `price` остаётся и равно `base_price`;
   - новые поля присутствуют и корректны в ответах API.

### Этап 3. Обновление frontend

1. В пациентской части (`BookingWizardPage`, список услуг) перейти с `${s.price} ₽` на:
   - если `effective_price != base_price` → показывать `base_price` зачёркнутым и `effective_price` крупно;
   - иначе отображать `base_price`.
2. В админке (страницы услуг, расписания) аналогично отображать активные скидки:
   - показывать “текущую цену с учётом скидки” + бейдж “Скидка”.
3. Везде, где фронт использует цену услуги, переключиться на `effective_price` как источник “актуального прайса”.

---

## 6. Обратный путь: отмена скидки и возврат старой цены

- При деактивации скидки:
  - админ меняет `is_active` или истекает `valid_until` в сущности `Discount`;
  - записи в `services` не меняются.

- При следующем вызове `PricingService.compute_effective_price`:
  - в выборке активных скидок для данной услуги/доктора/периода скидка уже не попадает;
  - `discount` возвращается как `None`;
  - `effective_price = base_price`;
  - `discount_amount = 0`.

Таким образом:

- “Старая цена” всегда хранится в `services.price` (`base_price`).
- Отменить скидку = выключить overlay, не трогая базовую цену.

---

## 7. Указания для @DEV (резюме)

1. **Не изменять `services.price` при операциях со скидками.** Все изменения цен — только через создание/обновление записей в `discounts`.
2. **Для любых новых сценариев оплаты использовать `PricingService`.** Не дублировать логику скидок вручную.
3. **Соблюдать обратную совместимость API.** Поле `price` в DTO оставляем, новые поля добавляем дополнительно.
4. **Тесты:** для ключевых сценариев (first_visit/service/doctor/period) обеспечить, что:
   - отображаемая `effective_price` совпадает с ценой, которая идёт в платежи;
   - при отключении скидки `effective_price` возвращается к `base_price` без ручных правок.

