# SEED_PROTOCOL.md
# Универсальный протокол seed-данных
# Применимо к: любой реляционной БД с зависимостями между сущностями
# Стек-пример: Python + SQLAlchemy 2 async + PostgreSQL
# Адаптируется под: Node/Prisma, Java/Hibernate, любой ORM

---

## ГЛАВНЫЙ ПРИНЦИП

Seed — это не "заполнить таблицы". Это **развернуть граф зависимостей в правильном порядке**.

Любая ошибка в seed-данных (UUID вместо имён, пустые дни, сломанные страницы) имеет одну из трёх причин:
1. **Порядок**: сущность создана до того как создана её зависимость
2. **Связь**: FK проставлен неверно или не проставлен вообще
3. **Режим**: dev-данные перемешаны с prod-структурой

---

## ТРИ РЕЖИМА SEED (никогда не смешивать)

| Режим | Файл | Цель | Данные |
|-------|------|------|--------|
| `smoke` | `seeds/smoke.py` | каждая страница открывается без ошибок | минимум: 1 запись каждого типа |
| `demo` | `seeds/demo.py` | показать продукт клиенту | реалистичные имена, даты на месяц вперёд, красивые цифры |
| `prod` | `seeds/prod.py` | чистый старт на проде | только справочники: роли, категории, настройки по умолчанию |

**Правило:** Alembic-миграции содержат только схему (`upgrade`/`downgrade`). Никаких INSERT в миграциях кроме системных констант (enum-значения, дефолтные роли).

**Запуск:**
```bash
python scripts/seeds/smoke.py    # проверка что всё работает
python scripts/seeds/demo.py     # демо для клиента
python scripts/seeds/prod.py     # инициализация продакшна
```

---

## ШАГ 1: ПОСТРОИТЬ ГРАФ ЗАВИСИМОСТЕЙ (обязательно до написания seed)

Перед любым seed — нарисовать граф. Стрелка означает "должен существовать раньше".

**Алгоритм:**
1. Выписать все сущности проекта
2. Для каждой найти FK-поля
3. Построить направленный граф: A → B означает "B зависит от A"
4. Топологически отсортировать — это и есть порядок создания

**Пример для медицинского SaaS:**
```
Tenant (клиника)
  └── Doctor (врач)          FK: tenant_id
  └── Service (услуга)       FK: tenant_id
  └── Patient (пациент)      FK: tenant_id
        └── Schedule (расписание)   FK: doctor_id, tenant_id
              └── Booking (запись)  FK: doctor_id, patient_id, service_id, tenant_id
                    └── Transaction FK: booking_id, tenant_id
                    └── Notification FK: booking_id, patient_id
```

**Порядок создания из графа:**
```
1. Tenant
2. Doctor, Service, Patient (параллельно — нет зависимостей между собой)
3. Schedule (зависит от Doctor)
4. Booking (зависит от Doctor + Patient + Service + Schedule)
5. Transaction, Notification (зависят от Booking)
```

**Правило нарушения порядка:**
Если создаёшь Booking до Schedule — слот не существует → FK violation или пустые поля.
Если создаёшь Schedule без Doctor — нет владельца → ошибка или NULL.

---

## ШАГ 2: ФАБРИЧНЫЙ ПАТТЕРН (Factory)

Каждая сущность — отдельная фабрика. Фабрика принимает явные зависимости, генерирует реалистичные данные.

```python
# scripts/seeds/factories.py

from faker import Faker
from datetime import datetime, timedelta, date
import random

fake = Faker('ru_RU')  # русские имена и данные

# ─────────────────────────────────────────
# УРОВЕНЬ 1: Независимые сущности
# ─────────────────────────────────────────

def make_tenant(session) -> Tenant:
    """Клиника — корень всего графа"""
    tenant = Tenant(
        name="Демо Стоматология",
        phone=fake.phone_number(),
        address=fake.address(),
    )
    session.add(tenant)
    session.flush()   # ← обязательно: получить id до использования в FK
    session.refresh(tenant)
    return tenant


def make_doctor(session, tenant: Tenant) -> Doctor:
    """Врач — зависит только от Tenant"""
    doctor = Doctor(
        tenant_id=tenant.id,
        full_name=fake.name(),          # ← НИКОГДА не UUID, всегда full_name
        specialty=random.choice([
            "Терапевт", "Хирург", "Ортодонт", "Пародонтолог"
        ]),
        phone=fake.phone_number(),
        is_active=True,
    )
    session.add(doctor)
    session.flush()
    session.refresh(doctor)
    return doctor


def make_service(session, tenant: Tenant) -> Service:
    """Услуга — зависит только от Tenant"""
    services_catalog = [
        ("Чистка зубов", 3500, 60),
        ("Пломба", 5000, 45),
        ("Рентген", 800, 15),
        ("Имплант", 45000, 120),
        ("Отбеливание", 12000, 90),
        ("Детский приём", 2500, 30),
    ]
    name, price, duration = random.choice(services_catalog)
    service = Service(
        tenant_id=tenant.id,
        name=name,
        price=price,
        duration_minutes=duration,
    )
    session.add(service)
    session.flush()
    session.refresh(service)
    return service


def make_patient(session, tenant: Tenant) -> Patient:
    """Пациент — зависит только от Tenant"""
    patient = Patient(
        tenant_id=tenant.id,
        full_name=fake.name(),
        phone=fake.phone_number(),
        email=fake.email(),
        birth_date=fake.date_of_birth(minimum_age=18, maximum_age=75),
    )
    session.add(patient)
    session.flush()
    session.refresh(patient)
    return patient


# ─────────────────────────────────────────
# УРОВЕНЬ 2: Расписание (зависит от Doctor)
# ─────────────────────────────────────────

def make_schedule_for_month(
    session,
    doctor: Doctor,
    month_start: date,
    slots_per_day: int = 8
) -> list[Schedule]:
    """
    Создаёт расписание на весь месяц.
    ВАЖНО: итерируем по дням, не создаём одну запись на месяц.
    Каждый рабочий день = свои слоты.
    """
    schedules = []
    current = month_start

    while current.month == month_start.month:
        # Пропускаем выходные
        if current.weekday() < 5:
            for slot_num in range(slots_per_day):
                slot_time = datetime.combine(
                    current,
                    datetime.min.time()
                ).replace(hour=9) + timedelta(minutes=30 * slot_num)

                schedule = Schedule(
                    doctor_id=doctor.id,
                    tenant_id=doctor.tenant_id,
                    slot_datetime=slot_time,
                    is_available=True,
                )
                session.add(schedule)
                schedules.append(schedule)

        current += timedelta(days=1)

    session.flush()
    return schedules


# ─────────────────────────────────────────
# УРОВЕНЬ 3: Записи (зависят от всего выше)
# ─────────────────────────────────────────

BOOKING_STATUSES = ["pending", "confirmed", "completed", "cancelled"]
BOOKING_WEIGHTS  = [0.15, 0.35, 0.40, 0.10]  # реалистичное распределение

def make_booking(
    session,
    schedule: Schedule,
    patient: Patient,
    service: Service,
) -> Booking:
    """
    Запись — зависит от Schedule + Patient + Service.
    Schedule передаётся явно — никогда не выбирать случайный из БД.
    """
    status = random.choices(BOOKING_STATUSES, weights=BOOKING_WEIGHTS)[0]

    booking = Booking(
        tenant_id=patient.tenant_id,
        doctor_id=schedule.doctor_id,
        patient_id=patient.id,
        service_id=service.id,
        schedule_id=schedule.id,
        scheduled_at=schedule.slot_datetime,
        status=status,
        notes=fake.sentence() if random.random() > 0.7 else None,
    )
    session.add(booking)
    session.flush()
    session.refresh(booking)

    # Помечаем слот как занятый
    schedule.is_available = False

    return booking


# ─────────────────────────────────────────
# УРОВЕНЬ 4: Дочерние сущности
# ─────────────────────────────────────────

def make_transaction(session, booking: Booking) -> Transaction | None:
    """Транзакция только для завершённых записей"""
    if booking.status != "completed":
        return None

    tx = Transaction(
        tenant_id=booking.tenant_id,
        booking_id=booking.id,
        amount=booking.service.price,
        type="income",
        description=f"Оплата: {booking.service.name}",
        created_at=booking.scheduled_at + timedelta(minutes=30),
    )
    session.add(tx)
    session.flush()
    return tx
```

---

## ШАГ 3: ЗАГЛУШКИ ДЛЯ ВНЕШНИХ СЕРВИСОВ

Поля требующие реальных API (SMS, платёжки, OAuth) — не пропускать и не оставлять NULL. Использовать детерминированные заглушки.

```python
# scripts/seeds/stubs.py
# Заглушки для внешних сервисов в dev/demo режиме

STUB_PHONE    = "+7 (999) 000-00-{:02d}"   # .format(index) → уникальные номера
STUB_EMAIL    = "demo+{index}@example.com"
STUB_YOOKASSA = "stub_payment_{uuid}"        # видно что заглушка
STUB_TELEGRAM = 100000000                    # невалидный но непустой chat_id

def stub_phone(index: int) -> str:
    """Уникальный телефон без реальной регистрации"""
    return f"+7 (999) 000-{index:02d}-{index:02d}"

def stub_payment_id(prefix: str = "demo") -> str:
    """Видимая заглушка платежа — не перепутать с реальным"""
    return f"STUB_{prefix.upper()}_{fake.uuid4()[:8]}"

def stub_sms_sent() -> bool:
    """В dev SMS не отправляется — возвращаем True чтобы flow продолжился"""
    return True
```

**Правило заглушек:**
- Заглушка должна быть **видимой** — `STUB_` префикс, `demo+` в email
- Заглушка должна быть **уникальной** — не один телефон на всех пациентов
- Заглушка должна **не ломать flow** — поле заполнено, валидация проходит
- В prod-seed заглушек нет — только реальные данные или NULL где допустимо

---

## ШАГ 4: ТРИ СКРИПТА

### `seeds/smoke.py` — минимум для проверки страниц

```python
"""
SMOKE SEED: минимальный набор для проверки что каждая страница
открывается без ошибок. Не для демо — для CI и быстрой проверки.
Создаёт: 1 tenant, 2 врача, 3 услуги, 5 пациентов,
         расписание на 3 дня, 4 записи разных статусов.
"""
async def run_smoke(session: AsyncSession):
    tenant   = make_tenant(session)
    doctors  = [make_doctor(session, tenant) for _ in range(2)]
    services = [make_service(session, tenant) for _ in range(3)]
    patients = [make_patient(session, tenant) for _ in range(5)]

    # 3 дня расписания — достаточно чтобы календарь не был пустым
    today = date.today()
    for doctor in doctors:
        for day_offset in range(3):
            day = today + timedelta(days=day_offset)
            slots = make_schedule_for_day(session, doctor, day, slots=4)

            # Минимум 1 запись каждого статуса
            for status in ["pending", "confirmed", "completed", "cancelled"]:
                slot = next((s for s in slots if s.is_available), None)
                if slot and patients:
                    booking = make_booking(
                        session, slot,
                        random.choice(patients),
                        random.choice(services)
                    )
                    booking.status = status
                    if status == "completed":
                        make_transaction(session, booking)

    await session.commit()
    print("✅ Smoke seed завершён")
```

### `seeds/demo.py` — реалистичные данные на месяц

```python
"""
DEMO SEED: полные данные для демонстрации клиенту.
Создаёт: 1 tenant, 4 врача, 8 услуг, 30 пациентов,
         расписание на текущий месяц, ~120 записей
         с реалистичным распределением статусов.
Правила:
- Все имена через Faker('ru_RU') — никаких UUID
- Даты равномерно распределены по месяцу
- Финансы: завершённые записи → транзакции в кассе
- Сегодня и завтра — обязательно есть записи (для дашборда)
"""
async def run_demo(session: AsyncSession):
    tenant   = make_tenant(session)
    doctors  = [make_doctor(session, tenant) for _ in range(4)]
    services = [make_service(session, tenant) for _ in range(8)]
    patients = [make_patient(session, tenant) for _ in range(30)]

    # Расписание на весь месяц
    month_start = date.today().replace(day=1)
    all_slots = []
    for doctor in doctors:
        slots = make_schedule_for_month(session, doctor, month_start)
        all_slots.extend(slots)

    # ВАЖНО: сегодня и завтра — гарантированно не пустые
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    priority_dates = {today, tomorrow}

    priority_slots = [s for s in all_slots if s.slot_datetime.date() in priority_dates]
    other_slots    = [s for s in all_slots if s.slot_datetime.date() not in priority_dates]

    # Сначала заполняем приоритетные дни
    for slot in random.sample(priority_slots, min(len(priority_slots), 12)):
        if slot.is_available:
            booking = make_booking(session, slot, random.choice(patients), random.choice(services))
            make_transaction(session, booking)

    # Затем остальные дни — ~40% заполненность
    bookings_count = int(len(other_slots) * 0.4)
    for slot in random.sample(other_slots, min(len(other_slots), bookings_count)):
        if slot.is_available:
            booking = make_booking(session, slot, random.choice(patients), random.choice(services))
            make_transaction(session, booking)

    await session.commit()
    print(f"✅ Demo seed завершён: {len(doctors)} врача, {len(patients)} пациентов")
```

### `seeds/prod.py` — чистый старт на продакшне

```python
"""
PROD SEED: только то что необходимо для работы системы.
НЕ создаёт: пациентов, записей, транзакций, демо-врачей.
Создаёт: роли, дефолтные настройки, категории услуг.
Идемпотентен: можно запускать повторно без дублирования.
"""
async def run_prod(session: AsyncSession):
    # Роли — только если не существуют
    for role_name in ["owner", "admin", "doctor", "receptionist"]:
        exists = await session.scalar(
            select(Role).where(Role.name == role_name)
        )
        if not exists:
            session.add(Role(name=role_name))

    # Категории услуг по умолчанию
    default_categories = [
        "Терапия", "Хирургия", "Ортодонтия",
        "Профилактика", "Протезирование", "Имплантология"
    ]
    for cat_name in default_categories:
        exists = await session.scalar(
            select(ServiceCategory).where(ServiceCategory.name == cat_name)
        )
        if not exists:
            session.add(ServiceCategory(name=cat_name))

    # Настройки по умолчанию
    defaults = {
        "booking_reminder_hours": "24",
        "slot_duration_minutes": "30",
        "working_hours_start": "09:00",
        "working_hours_end": "20:00",
    }
    for key, value in defaults.items():
        exists = await session.scalar(
            select(Setting).where(Setting.key == key)
        )
        if not exists:
            session.add(Setting(key=key, value=value))

    await session.commit()
    print("✅ Prod seed завершён: роли, категории, настройки")
```

---

## ДИАГНОСТИКА: ПОЧЕМУ ПУСТЫЕ ДНИ

Если после seed конкретные дни пустые — причина всегда одна из четырёх:

| Симптом | Причина | Лечение |
|---------|---------|---------|
| Сегодня/завтра пустые | Нет приоритизации дат | Явно заполнять `priority_dates` первыми |
| Весь месяц пустой | Schedule создан, Booking не создан | Проверить порядок в графе |
| Записи есть но врач пустой | FK doctor_id = None | `session.flush()` после make_doctor |
| Имена = UUID | Поле берётся из id вместо full_name | Проверить что передаётся в отображение |

---

## ПРАВИЛА ДЛЯ @DEV

```
□ Никаких INSERT в Alembic-миграциях кроме системных констант
□ Каждая фабрика вызывает session.flush() + session.refresh() после add()
□ Порядок создания строго по графу зависимостей
□ Заглушки внешних API — с префиксом STUB_ или demo+
□ Сегодня и завтра всегда заполнены в demo-seed
□ prod-seed идемпотентен: повторный запуск не создаёт дубли
□ Faker('ru_RU') для русскоязычных проектов — никаких John Doe
```

---

## СТРУКТУРА ФАЙЛОВ

```
scripts/
  seeds/
    __init__.py
    factories.py      # фабрики сущностей (импортируются в smoke/demo)
    stubs.py          # заглушки внешних сервисов
    smoke.py          # минимальный набор
    demo.py           # полный демо-набор
    prod.py           # production init
    run.py            # единая точка входа: python run.py [smoke|demo|prod]
```

`run.py`:
```python
import sys, asyncio
from seeds.smoke import run_smoke
from seeds.demo  import run_demo
from seeds.prod  import run_prod
from db import get_session  # твой session factory

MODE_MAP = {"smoke": run_smoke, "demo": run_demo, "prod": run_prod}

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if mode not in MODE_MAP:
        print(f"Режим '{mode}' неизвестен. Используй: smoke | demo | prod")
        sys.exit(1)
    async with get_session() as session:
        await MODE_MAP[mode](session)

asyncio.run(main())
```

---

Reference: docs/ROLE_DEV.md · docs/ROLE_ARCH.md · docs/STACK_SELECTION.md
Version: 1.0 | 2026-03
