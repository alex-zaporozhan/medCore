## ARCH_RATE_LIMITING — rate limiting для auth/SMS/AI/отчётов

Основание: `ARCH_HARDENING_ROADMAP.md` (п. 3), текущая архитектура (`src/application/services/auth_service.py`, `src/api/v1/routers/auth.py`, `src/application/services/chat_ai_service.py`, `src/api/v1/routers/admin_ai_reports.py`, Redis‑инфраструктура).

**Цель:** формализовать стратегию rate limiting на уровне приложения и инфраструктуры, определить "дорогие" эндпоинты и контракт для сервиса `RateLimiter`, чтобы:

- защититься от брутфорса SMS‑кодов и злоупотребления auth‑эндпоинтами;
- ограничить нагрузку на внешние AI‑провайдеры и тяжёлые отчётные запросы;
- иметь единый слой, который легко включить/отключить и настроить через конфиг.

---

## 1. Классы "дорогих" эндпоинтов

### 1.1. Auth/SMS

Эндпоинты:

- `/api/v1/auth/send-code` — генерация и отправка SMS‑кода пациенту;
- (возможные будущие) `/api/v1/auth/forgot-password`, `/api/v1/auth/reset-password` и т.п.

Почему дорогие:

- стоимость SMS/пуш‑уведомлений;
- риск злоупотребления (массовые запросы на чужие номера, спам);
- возможный вектор для DoS на SMS‑провайдера.

### 1.2. Auth‑login админов

Эндпоинт:

- `/api/v1/admin/auth/login` — попытки входа администратора по email/паролю.

Почему дорогой:

- брутфорс паролей;
- возможность перегрузить базу и логирование множеством неуспешных попыток.

### 1.3. AI‑эндпоинты

Эндпоинты:

- `ChatAiService`:
  - admin chat summary;
  - suggest reply;
  - patient AI insight;
- AI‑отчёты (`/api/v1/admin/ai-reports/conflicts`, `reanalyze` и т.п.).

Почему дорогие:

- каждый запрос может вызывать внешний AI‑провайдер (стоимость + ограниченные квоты);
- тяжёлые бизнес‑операции (агрегации, анализ текстов).

### 1.4. Отчёты и тяжёлые агрегации

Эндпоинты:

- отчёты по бронированиям, выручке, работе врачей/админов (`/api/v1/admin/reports/*`);
- возможные будущие выгрузки CSV/Excel с большой выборкой.

Почему дорогие:

- тяжёлые запросы к БД;
- потенциально большие объёмы данных на выдаче.

---

## 2. Стратегия rate limiting на уровне приложения

### 2.1. Общий подход

- Используем Redis как счётчик запросов:
  - ключи вида `rate:{route_key}:{dimension}` (например, `rate:auth_send_code:ip`, `rate:auth_send_code:phone`);
  - значение — количество запросов за окно `T` секунд.
- Вводим **минимальный слой rate limiting в приложении**, который работает независимо от NGINX/Cloudflare:
  - быстрый ответ с 429 без загрузки тяжёлой бизнес‑логики;
  - простая настройка лимитов через конфиг.

### 2.2. Ключи и измерения

Для разных классов эндпоинтов используем разные ключи:

- Auth/SMS:
  - по IP: `rate:auth_send_code:ip:{ip}`;
  - по телефону: `rate:auth_send_code:phone:{normalized_phone}`;
- Admin login:
  - по IP: `rate:admin_login:ip:{ip}`;
  - по email: `rate:admin_login:email:{normalized_email}`;
- AI‑эндпоинты:
  - по клинике: `rate:ai:{route_key}:clinic:{clinic_id}`;
  - опционально по администратору: `rate:ai:{route_key}:admin:{admin_id}`;
- Отчёты:
  - по клинике: `rate:reports:{route_key}:clinic:{clinic_id}`;
  - опционально по администратору.

**Нормализация:**

- IP:
  - использовать строку `X-Forwarded-For`/`remote_addr` после корректной обработки на уровне FastAPI/uvicorn/прокси;
- Телефон:
  - использовать уже существующую нормализацию из `AuthService._normalize_phone`;
- Email:
  - `strip().lower()`.

### 2.3. Рекомендуемые лимиты (базовый уровень)

#### Auth/SMS (`/auth/send-code`)

- По IP: не более **20 запросов за 10 минут** (`limit=20`, `window=600`).
- По телефону: не более **5 запросов за 10 минут** (`limit=5`, `window=600`).

При превышении:

- 429 Too Many Requests;
- сообщение в detail: "Слишком много попыток. Попробуйте позже." (без уточнения лимитов).

#### Admin login

- По IP: не более **30 попыток за 10 минут**.
- По email: не более **10 попыток за 10 минут**.

Поведение при превышении — аналогично.

#### AI‑эндпоинты

- Для кратких AI‑операций (summary/suggest reply):
  - по клинике: **60 запросов в минуту** на каждый тип операции;
- Для тяжёлых отчётов/аналитики (reanalyze, долгие range‑аналисы):
  - по клинике: **5 запусков в час**.

#### Отчёты

- Стандартные отчёты:
  - по клинике: **20 запросов за 10 минут** на каждый тип;
- Тяжёлые агрегаты (выгрузки, большие диапазоны):
  - индивидуально, по SLA, но в base‑уровне можно использовать те же лимиты, что и для тяжёлых AI‑операций.

Все значения **должны быть вынесены в конфиг** (`core/config.py`), чтобы их можно было адаптировать без правки кода.

---

## 3. Контракт сервиса `RateLimiter`

### 3.1. Расположение и зависимость

- Backend‑слой: `src/infrastructure/rate_limiter.py` или пакет `src/infrastructure/rate_limiting/`.
- Использует общий Redis‑клиент (`src.infrastructure.database.redis_client.get_redis`).

### 3.2. Интерфейс

Базовый интерфейс (Python‑псевдокод):

```python
class RateLimitExceeded(Exception):
    def __init__(self, key: str, limit: int, window: int) -> None: ...


class RateLimiter:
    def __init__(self, redis: Redis): ...

    async def check_or_raise(self, key: str, limit: int, window: int) -> None:
        """
        Увеличивает счётчик по ключу и проверяет, не превышен ли лимит.
        :param key: строковый ключ в стиле rate:...
        :param limit: максимальное количество запросов за окно.
        :param window: размер окна в секундах.
        :raises RateLimitExceeded: если лимит превышен.
        """
        ...
```

Дополнительно (по необходимости):

- `async def get_remaining(self, key: str, limit: int, window: int) -> int: ...` — вернуть, сколько запросов ещё можно сделать до лимита (опционально для UI/логов).

### 3.3. Алгоритм на Redis

- Используем простую схему "fixed window":
  - `INCR key` + `EXPIRE key window`, если ключ новый;
  - если после `INCR` значение > `limit` → выбрасываем `RateLimitExceeded`.
- Упрощение:
  - не используем sliding window/Leaky Bucket в MVP;
  - этого достаточно для защиты от грубых злоупотреблений.

**Требования:**

- Все операции должны быть **атомарными** (использовать стандартный Redis‑семантику INCR+EXPIRE).
- Ошибка Redis:
  - при недоступности Redis rate limiting не должен ломать основной функционал:
    - логировать ошибку;
    - **по умолчанию пропускать запрос** (fail‑open), если иное не указано в требовании @SEC.

---

## 4. Встраивание `RateLimiter` в эндпоинты

### 4.1. Auth/SMS (`/auth/send-code`)

**Уровень:** FastAPI‑роутер `src/api/v1/routers/auth.py`.

**Паттерн:**

- В начале хендлера `send_code`:
  - извлечь IP (из `request.client.host` и/или `X-Forwarded-For`);
  - нормализовать телефон с помощью `AuthService._normalize_phone`;
  - вызвать:

```python
await rate_limiter.check_or_raise(
    key=f"rate:auth_send_code:ip:{ip}",
    limit=settings.rate_auth_send_code_ip_limit,
    window=settings.rate_auth_send_code_ip_window_seconds,
)
await rate_limiter.check_or_raise(
    key=f"rate:auth_send_code:phone:{normalized_phone}",
    limit=settings.rate_auth_send_code_phone_limit,
    window=settings.rate_auth_send_code_phone_window_seconds,
)
```

- При `RateLimitExceeded`:
  - возвращать 429 с коротким detail (одно и то же сообщение для любых превышений).

### 4.2. Admin login

**Уровень:** `src/api/v1/routers/admin_auth.py` (`admin_login`).

**Паттерн:**

- В начале хендлера:
  - извлечь IP;
  - нормализовать email (`strip().lower()`);
  - вызвать `check_or_raise` по ключам `rate:admin_login:ip:...` и `rate:admin_login:email:...`.

### 4.3. AI‑эндпоинты

**Уровень:** роутеры и/или сервисы, которые обращаются к AI:

- `src/application/services/chat_ai_service.py`;
- `src/api/v1/routers/admin_ai_reports.py`;
- `src/api/v1/routers/admin_patient_ai.py` и др.

**Паттерн:**

- Перед вызовом внешнего AI:
  - взять `clinic_id` (из `current_admin.clinic_id` или настроек клиники);
  - собрать `route_key` (`"chat_summary"`, `"suggest_reply"`, `"patient_insight"`, `"ai_reports_reanalyze"` и т.п.);
  - вызвать:

```python
await rate_limiter.check_or_raise(
    key=f"rate:ai:{route_key}:clinic:{clinic_id}",
    limit=settings.rate_ai_clinic_limit,
    window=settings.rate_ai_clinic_window_seconds,
)
```

- При необходимости — отдельные лимиты для тяжёлых операций (`rate_ai_heavy_*`).

### 4.4. Отчётные эндпоинты

**Уровень:** `src/api/v1/routers/admin_reports.py`, `AdminReportsService` и др.

**Паттерн:**

- В начале хендлера или перед запуском тяжёлого отчёта:

```python
await rate_limiter.check_or_raise(
    key=f"rate:reports:{route_key}:clinic:{clinic_id}",
    limit=settings.rate_reports_clinic_limit,
    window=settings.rate_reports_clinic_window_seconds,
)
```

---

## 5. Рекомендации по NGINX/Cloudflare

Приложен минимальный набор рекомендаций для инфраструктурного слоя. Конкретная реализация — зона ответственности @OPS, но **должна быть согласована** с приложенческими лимитами.

### 5.1. NGINX

Базовые идеи:

- Ввести `limit_req_zone` по IP:

```nginx
limit_req_zone $binary_remote_addr zone=auth_zone:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=global_zone:10m rate=300r/m;
```

- Применить к локациям:

```nginx
location /api/v1/auth/send-code {
    limit_req zone=auth_zone burst=10 nodelay;
    proxy_pass http://backend;
}

location /api/v1/admin/auth/login {
    limit_req zone=auth_zone burst=10 nodelay;
    proxy_pass http://backend;
}

location /api/ {
    limit_req zone=global_zone burst=50 nodelay;
    proxy_pass http://backend;
}
```

Параметры (`rate`, `burst`) должны подбираться под фактическую нагрузку и SLA.

### 5.2. Cloudflare / внешний WAF

Если используется Cloudflare или аналог:

- задать **rule‑based rate limiting**:
  - по IP для путей `/api/v1/auth/*`, `/api/v1/admin/auth/login`;
  - по клинике/домену для AI‑и отчётных эндпоинтов, если возможно.
- использовать 429 и/или капчу после определённого порога.

Важно:

- rate limiting на уровне прокси **не должен конфликтовать** с приложенческими лимитами:
  - внешние лимиты обычно чуть более "широкие", чем прикладные, чтобы не удваивать отказы.

---

## 6. Выход для @DEV и @OPS

**Для @DEV (см. `DEV_PROMPTS_HARDENING_SECURITY_AND_AI.md`, A.3):**

- реализовать `RateLimiter` и исключение `RateLimitExceeded` по этому контракту;
- добавить нужные конфиги в `Settings`;
- обернуть указанные эндпоинты вызовами `check_or_raise`;
- настроить корректные ответы 429.

**Для @OPS:**

- на основе этого документа настроить базовый rate limiting в NGINX/Cloudflare;
- следить за метриками превышения лимитов и корректировать значения при необходимости.

